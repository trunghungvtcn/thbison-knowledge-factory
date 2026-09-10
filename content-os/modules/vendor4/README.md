# THBISON Vendor 4 — Knowledge API + Asset Gateway (MOCK)

Implementation hoàn chỉnh cho lab. `APP_MODE=MOCK`. Không production, không paid call.

## Chạy

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8080
pytest -q
docker compose up --build
```

Header bắt buộc: `Authorization: Bearer <token>`, POST thêm `Idempotency-Key`, `X-Contract-Version: 1.0.0`.

## Status

`SIMULATED_INTEGRATION_PASS`. Staging round-trip: `NOT_RUN` (credential out-of-band, không có token trong gói).
