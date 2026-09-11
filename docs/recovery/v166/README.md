# V16.6 evidence completion

V16.6 separates online public acquisition from frozen, offline evidence analysis.
It never writes Notion, Kaggle, SQL, production schemas, or schedules.

```powershell
python -m kf_pilot.v166_evidence_completion discover --research-plan v166/inputs/research_plan.json --output v166/acquisition/public-001
python -m kf_pilot.v166_evidence_completion freeze --acquisition-dir v166/acquisition/public-001 --as-of 2026-09-05T00:00:00+07:00 --output v166/corpus/frozen-001
python -m kf_pilot.v166_evidence_completion propose --run-config v166/inputs/run_config.json --output v166/artifacts/proposal-001
python -m kf_pilot.v166_evidence_completion project-shadow --run-config v166/inputs/run_config.json --proposal v166/artifacts/proposal-001 --output v166/artifacts/final-001
python -m kf_pilot.v166_evidence_completion verify --inputs v166/inputs/run_config.json --committed-run v166/artifacts/final-001 --report v166/artifacts/independent-verification-001.json
```

Receipts must be supplied through a separate trust config whose pins come from an
external trust root. The current repository run deliberately supplies none.

