import json
from urllib.request import urlopen

from thbison_v6.http_probe import serve_background


def test_healthz_loopback():
    httpd, _ = serve_background()
    try:
        port = httpd.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as r:
            data = json.loads(r.read().decode())
        assert data["status"] == "ok"
    finally:
        httpd.shutdown()
