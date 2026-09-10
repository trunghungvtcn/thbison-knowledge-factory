from __future__ import annotations

import re
from urllib.parse import urlparse

from app.errors import AdapterError

SCRIPT_RE = re.compile(r"<\s*script\b|javascript:|onerror\s*=|onload\s*=", re.I)
SAFE_HOSTS = {"cdn.test.thbison.local", "assets.test.thbison.local", "127.0.0.1", "localhost"}
PRIVATE_PREFIXES = ("10.", "192.168.", "169.254.", "127.")


def sanitize_html(text: str) -> str:
    if SCRIPT_RE.search(text or ""):
        raise AdapterError("UNSAFE_CONTENT", "Unsafe HTML/script blocked")
    return text


def assert_safe_url(url: str | None) -> None:
    if not url:
        return
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme not in ("https", "http"):
        raise AdapterError("DESTINATION_DENIED", "URL scheme not allowlisted")
    if host.startswith(PRIVATE_PREFIXES) and host not in {"127.0.0.1", "localhost"}:
        raise AdapterError("DESTINATION_DENIED", "Private metadata endpoint blocked")
    if host not in SAFE_HOSTS and not host.endswith(".test.thbison.local"):
        if host not in {"example.test", "staging.test.thbison.local"}:
            raise AdapterError("DESTINATION_DENIED", f"Host not allowlisted: {host}")


def preserve_citations(original: str, sanitized: str) -> None:
    # Citations like [claim:test-claim-1] must survive sanitization.
    for m in re.findall(r"\[claim:[A-Za-z0-9_.:-]+\]", original):
        if m not in sanitized:
            raise AdapterError("UNSAFE_CONTENT", "Sanitization damaged citation")
