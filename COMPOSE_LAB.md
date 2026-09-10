# Local integration lab

All services bind only to `127.0.0.1`, use generated local SQLite/PGLite state, force `APP_MODE=MOCK`, and set both production/public-effect switches to false.

Commands:

```text
python scripts/labctl.py up
python scripts/labctl.py down
python scripts/verify_candidate.py
python content-os/modules/vendor6/scripts/run_actual_integration.py
```

Ports are V1 planning `18081`, V2 writer `18082`, V3 runtime `18083`, Knowledge→V4 gateway `18084`, and V5 CMS DRY_RUN `18085`. The E2E command owns process startup/shutdown and deletes only its generated `.lab-data`/`evidence-current` directories.

No live Notion target is configured. `config/notion-sandbox.example.json` remains intentionally empty. No VPS target is selected or contacted.
