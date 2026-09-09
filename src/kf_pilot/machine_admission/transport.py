"""HTTPS connections pinned to validated IPs; never resolve twice or use proxy env."""
import http.client
import ipaddress
import math
import queue
import socket
import ssl
import threading
import time
from datetime import datetime, timezone
from email.message import Message
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

from kf_pilot.v166_evidence_completion.canonical import require
from .storage import Budget

MAX_SOURCE_BYTES = 20 * 1024**2
MAX_REDIRECTS = 5
MAX_ATTEMPTS = 2
DNS_SLOTS = threading.BoundedSemaphore(2)


def remaining(deadline):
    seconds = deadline - time.monotonic()
    require(seconds > 0, 'ATTEMPT_DEADLINE')
    return seconds


def address_public(address):
    ip = ipaddress.ip_address(address)
    return ip.is_global and not ip.is_multicast and not ip.is_reserved and not ip.is_unspecified


def resolve(url, deadline, resolver=None):
    p = urlsplit(url)
    require(p.scheme == 'https' and p.hostname and p.username is None and p.password is None
            and p.port in (None, 443) and not any(ord(c) < 33 for c in url), 'PUBLIC_HTTPS_REQUIRED')
    require(DNS_SLOTS.acquire(timeout=remaining(deadline)), 'DNS_BUSY')
    answers = queue.Queue(1)
    def worker():
        try:
            answers.put((resolver or socket.getaddrinfo)(p.hostname, 443, type=socket.SOCK_STREAM))
        except Exception as exc:
            answers.put(exc)
        finally:
            DNS_SLOTS.release()
    threading.Thread(target=worker, daemon=True).start()
    try:
        rows = answers.get(timeout=remaining(deadline))
    except queue.Empty as exc:
        raise RuntimeError('DNS_DEADLINE') from exc
    if isinstance(rows, Exception):
        raise RuntimeError('DNS_RESOLUTION_FAILED') from rows
    require(rows, 'DNS_RESOLUTION_EMPTY')
    for row in rows:
        require(address_public(row[4][0]), 'NON_PUBLIC_FETCH_TARGET')
    remaining(deadline)
    return p, rows


class PinnedHTTPS(http.client.HTTPConnection):
    def __init__(self, hostname, address, deadline, context=None):
        super().__init__(hostname, 443, timeout=remaining(deadline))
        self.address = address
        self.deadline = deadline
        self.context = context or ssl.create_default_context()
        require(self.context.check_hostname and self.context.verify_mode == ssl.CERT_REQUIRED, 'TLS_VERIFICATION_REQUIRED')
        self.timer = None

    def connect(self):
        family, socktype, proto, _, sockaddr = self.address
        require(address_public(sockaddr[0]), 'NON_PUBLIC_FETCH_TARGET')
        raw = socket.socket(family, socktype, proto)
        self.sock = raw
        def abort():
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except (OSError, AttributeError):
                pass
        self.timer = threading.Timer(remaining(self.deadline), abort)
        self.timer.daemon = True
        self.timer.start()
        try:
            raw.settimeout(remaining(self.deadline))
            raw.connect(sockaddr)
            require(raw.getpeername()[0] == sockaddr[0], 'PEER_MISMATCH')
            self.sock = self.context.wrap_socket(raw, server_hostname=self.host)
            self.sock.settimeout(remaining(self.deadline))
        except BaseException:
            raw.close(); self.close()
            raise

    def close(self):
        if self.timer:
            self.timer.cancel()
        super().close()


class ResponseInfo:
    def __init__(self, url, status, headers):
        self.url, self.status = url, status
        self.headers = Message()
        for k, v in headers:
            self.headers[k] = v
        self.fetched_at = datetime.now(timezone.utc).isoformat()

    def geturl(self):
        return self.url


def fetch(url, timeout=30, budget=None, resolver=None, connection_factory=None):
    budget = budget or Budget()
    require(type(timeout) in (int, float) and 0 < timeout <= 30, 'TIMEOUT_CAP')
    budget.attempt(url)
    deadline = time.monotonic() + timeout
    current = url
    for hop in range(MAX_REDIRECTS + 1):
        p, addresses = resolve(current, deadline, resolver)
        budget.reserve('hops')
        connection = (connection_factory or PinnedHTTPS)(p.hostname, addresses[0], deadline)
        try:
            connection.request('GET', (p.path or '/') + ('?' + p.query if p.query else ''),
                               headers={'User-Agent': 'KnowledgeFactory-PublicResearch/1.0', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            info = ResponseInfo(current, response.status, response.getheaders())
            remaining(deadline)
            if response.status in {301, 302, 303, 307, 308}:
                require(hop < MAX_REDIRECTS, 'REDIRECT_LIMIT')
                target = response.getheader('Location')
                require(target, 'REDIRECT_LOCATION_MISSING')
                current = urljoin(current, target)
                continue
            if response.status != 200:
                delay = response.getheader('Retry-After', '1')
                try:
                    delay = float(delay)
                except ValueError:
                    try:
                        delay = parsedate_to_datetime(delay).timestamp() - time.time()
                    except (ValueError, TypeError):
                        delay = 60
                if not math.isfinite(delay):
                    delay = 60
                budget.status(url, response.status, delay)
                raise RuntimeError(f'HTTP_{response.status}' + ('_DEFERRED' if response.status in {429, 503} else '_TERMINAL'))
            require(response.getheader('Content-Encoding', 'identity').lower() == 'identity', 'ENCODING_NOT_ALLOWED')
            declared = response.getheader('Content-Length')
            require(declared is None or 0 <= int(declared) <= MAX_SOURCE_BYTES, 'SOURCE_SIZE_LIMIT')
            chunks, total = [], 0
            while True:
                remaining(deadline)
                allowance = budget.read_allowance(min(65536, MAX_SOURCE_BYTES + 1 - total))
                chunk = response.read1(allowance)
                budget.release_unused_bytes(allowance - len(chunk))
                if not chunk:
                    break
                total += len(chunk)
                require(total <= MAX_SOURCE_BYTES, 'SOURCE_SIZE_LIMIT')
                chunks.append(chunk)
            remaining(deadline)
            require(declared is None or total == int(declared), 'TRUNCATED_SOURCE')
            budget.reserve('documents')
            return info, b''.join(chunks)
        finally:
            connection.close()
    raise RuntimeError('REDIRECT_LIMIT')
