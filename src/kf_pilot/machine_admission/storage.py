"""Single-host file transactions, OS-owned locks and durable workload accounting."""
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

from kf_pilot.v166_evidence_completion.canonical import bytes_for, digest, load, require


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    with temp.open('wb') as f:
        f.write(bytes_for(value))
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


@contextmanager
def lock(path):
    """Locks are released by the OS on process death, including Windows."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as f:
        if f.tell() == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def transact(self, fn):
        with lock(self.root / 'state.lock'):
            path = self.root / 'state.json'
            state = load(path) if path.exists() else {'tasks': {}, 'budget': {}, 'revoked': [], 'gaps': {}}
            result = fn(state)
            atomic(path, state)
            return result

    def commit(self, key, pins, produce, fault=None):
        require(len(key) == 64 and all(c in '0123456789abcdef' for c in key), 'TASK_KEY')
        with lock(self.root / f'{key}.lock'):
            directory = self.root / 'runs' / key
            marker = directory / 'COMMITTED.json'
            if marker.exists():
                manifest = load(marker)
                require(manifest['pins'] == pins, 'REPLAY_PIN_MISMATCH')
                payload = load(directory / 'result.json')
                require(digest(payload) == manifest['result_hash'], 'COMMIT_TAMPER')
                self.transact(lambda s: s['tasks'][key].update(state='DONE', result_hash=digest(payload)))
                return payload, True
            def start(s):
                t = s['tasks'].setdefault(key, {'attempts': 0, 'created_at': time.time()})
                require(t['attempts'] < 2, 'TASK_RETRY_CAP')
                t.update(attempts=t['attempts'] + 1, state='RUNNING', pins=pins)
            self.transact(start)
            payload = produce()
            atomic(directory / 'result.json', payload)
            if fault:
                fault()
            atomic(marker, {'pins': pins, 'result_hash': digest(payload)})
            self.transact(lambda s: s['tasks'][key].update(state='DONE', result_hash=digest(payload)))
            return payload, False

    def visible(self, key, pins):
        marker = self.root / 'runs' / key / 'COMMITTED.json'
        if not marker.exists():
            return None
        state = self.transact(lambda s: s.copy())
        if any(v in state['revoked'] for v in pins.values()):
            return None
        require(load(marker)['pins'] == pins, 'STALE_DEPENDENCY')
        result = load(marker.parent / 'result.json')
        require(digest(result) == load(marker)['result_hash'], 'COMMIT_TAMPER')
        return result

    def revoke(self, dependency):
        def change(s):
            if dependency not in s['revoked']:
                s['revoked'].append(dependency)
        self.transact(change)

    def enrichment(self, gap, evidence_hashes):
        def change(s):
            g = s['gaps'].setdefault(gap, {'rounds': 0, 'seen': []})
            novel = set(evidence_hashes) - set(g['seen'])
            if not novel or g['rounds'] >= 2:
                return False
            g['rounds'] += 1
            g['seen'] = sorted(set(g['seen']) | novel)
            return True
        return self.transact(change)


class Budget:
    DEFAULT = {'bytes': 100 * 1024**2, 'hops': 60, 'documents': 40,
               'model_calls': 100, 'model_tokens': 300000}

    def __init__(self, store=None, caps=None):
        self.store = store
        self.caps = dict(self.DEFAULT)
        for key, value in (caps or {}).items():
            require(key in self.caps and type(value) is int and 0 <= value <= self.caps[key], 'BUDGET_CONFIG')
            self.caps[key] = value
        self.memory = {'budget': {}}

    def change(self, fn):
        return self.store.transact(fn) if self.store else fn(self.memory)

    def reserve(self, kind, amount=1):
        require(kind in self.caps and type(amount) is int and amount >= 0, 'BUDGET_AMOUNT')
        def use(s):
            b = s['budget']; old = b.get(kind, 0)
            require(old + amount <= self.caps[kind], 'BUDGET_EXHAUSTED', kind)
            b[kind] = old + amount
        self.change(use)

    def attempt(self, url, now=None):
        now = time.time() if now is None else now
        def use(s):
            urls = s['budget'].setdefault('urls', {})
            row = urls.setdefault(url, {'attempts': 0, 'terminal': False, 'next_at': 0})
            require(not row['terminal'], 'URL_TERMINAL')
            require(now >= row['next_at'], 'URL_DEFERRED')
            require(row['attempts'] < 2, 'URL_ATTEMPT_CAP')
            row['attempts'] += 1
        self.change(use)

    def read_allowance(self, wanted):
        require(type(wanted) is int and wanted > 0, 'READ_ALLOWANCE')
        def use(s):
            b = s['budget']; n = min(wanted, self.caps['bytes'] - b.get('bytes', 0))
            require(n > 0, 'BUDGET_EXHAUSTED', 'bytes')
            b['bytes'] = b.get('bytes', 0) + n
            return n
        return self.change(use)

    def release_unused_bytes(self, amount):
        def use(s):
            require(type(amount) is int and 0 <= amount <= s['budget'].get('bytes', 0), 'BYTE_RELEASE')
            s['budget']['bytes'] -= amount
        self.change(use)

    def status(self, url, code, delay=0):
        def use(s):
            row = s['budget']['urls'][url]
            row['terminal'] = code not in {429, 503}
            row['next_at'] = time.time() + max(delay, 1)
        self.change(use)

    def model_reserve(self, input_tokens, max_output=4000):
        require(type(input_tokens) is int and input_tokens >= 0, 'TOKEN_INPUT')
        require(type(max_output) is int and 0 < max_output <= 4000, 'TOKEN_OUTPUT')
        def use(s):
            b = s['budget']; total = input_tokens + max_output
            require(b.get('model_calls', 0) + 1 <= self.caps['model_calls'], 'MODEL_CALL_CAP')
            require(b.get('model_tokens', 0) + total <= self.caps['model_tokens'], 'MODEL_TOKEN_CAP')
            b['model_calls'] = b.get('model_calls', 0) + 1
            b['model_tokens'] = b.get('model_tokens', 0) + total
        self.change(use)

    def snapshot(self):
        return self.change(lambda s: json.loads(json.dumps(s['budget'])))
