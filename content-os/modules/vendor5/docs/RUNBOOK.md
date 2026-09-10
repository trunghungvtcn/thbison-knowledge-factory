# Runbook

```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
./scripts/verify_local.sh
uvicorn app.httpapi:app --host 127.0.0.1 --port 8080
```

Default flags deny staging writes, production, and public effects. Do not put tokens in the tree.
