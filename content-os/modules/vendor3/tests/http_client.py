"""HTTP client factory. No harness fallback (V3-R3-04)."""
from fastapi.testclient import TestClient
from app.api import create_app

def make_http(rt):
    return TestClient(create_app(rt)), "fastapi"
