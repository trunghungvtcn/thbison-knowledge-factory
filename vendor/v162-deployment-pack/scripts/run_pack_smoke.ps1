$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
python "$Root/v162/gate_phase_f_readiness.py" "$Root/v162/example_readiness_report.json" "$Root/v162/example_empty_canary.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "V162_PACK_SMOKE_PASS"
