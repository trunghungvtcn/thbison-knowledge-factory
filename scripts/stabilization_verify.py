"""Collect candidate-bound TEST_ONLY evidence without short-circuiting suites."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'stabilization-evidence'


def main():
    OUT.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ('TOKEN', 'SECRET', 'PASSWORD', 'DATABASE_URL', 'API_KEY'))}
    env.update(PYTHONPATH=str(ROOT / 'src'), CONTRACTOR_ROOT=str(ROOT / 'dependencies/pipeline-lab-contractor-m1-m5'), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', DATABASE_URL='', CMS_MODE='DRY_RUN', CMS_LEDGER_PATH=str(OUT / 'cms.sqlite'))
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    receipt = {'job_id': 'THBISON-STABILIZATION-01', 'candidate_sha': sha, 'python': sys.version, 'platform': sys.platform, 'started_at': datetime.now(timezone.utc).isoformat(), 'runs': [], 'production_ready': False, 'merged': False, 'deployed': False, 'notion_writes': False}

    def run(name, cmd, cwd=ROOT):
        with (OUT / (name + '.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run(cmd, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        receipt['runs'].append({'id': name, 'command': cmd, 'cwd': str(cwd.relative_to(ROOT)), 'exit_code': result.returncode, 'log': name + '.log'})
        print(name, result.returncode, flush=True)
        return result.returncode

    run('payload', [sys.executable, 'scripts/jobs/j2_verify_payload.py'])
    run('source_strict', [sys.executable, 'scripts/verify_candidate.py', '--full'])
    run('knowledge', [sys.executable, 'scripts/jobs/j2_source_only_pytest.py', '--junitxml=stabilization-evidence/knowledge.xml', '--summary-json=stabilization-evidence/knowledge.json', '--', 'tests'])
    for vendor in ('vendor1', 'vendor2'):
        cwd = ROOT / 'content-os/modules' / vendor
        if run(vendor + '_install', ['npm', 'ci', '--ignore-scripts'], cwd):
            receipt.setdefault('not_run', []).append({'module': vendor, 'reason': 'dependency installation failed', 'checks': ['scripts', 'src', 'typecheck', 'build']})
            continue
        run(vendor + '_scripts', ['node', '--test', '--test-reporter=junit', f'--test-reporter-destination={OUT / (vendor + "-scripts.xml")}', 'scripts/**/*.test.mjs'], cwd)
        package = json.loads((cwd / 'package.json').read_text())
        source_command = package['scripts']['test'].split(' && ', 1)[1]
        import shlex
        run(vendor + '_src', shlex.split(source_command), cwd)
        run(vendor + '_typecheck', ['npm', 'run', 'typecheck'], cwd)
        run(vendor + '_build', ['npm', 'run', 'build'], cwd)
    for vendor in ('vendor5', 'vendor6'):
        run(vendor, [sys.executable, '-m', 'pytest', '-q', f'content-os/modules/{vendor}/tests', f'--junitxml=stabilization-evidence/{vendor}.xml'])
    run('actual_e2e', [sys.executable, 'content-os/modules/vendor6/scripts/run_actual_integration.py'])
    receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
    receipt['files'] = {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for p in OUT.iterdir() if p.is_file() and p.suffix in ('.log', '.xml', '.json') and p.name != 'receipt.json'}
    receipt['all_commands_passed'] = all(r['exit_code'] == 0 for r in receipt['runs']) and not receipt.get('not_run')
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return 0 if receipt['all_commands_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
