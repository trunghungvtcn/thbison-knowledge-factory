"""Exercise the generated notebook against both actual Kaggle dataset layouts."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('layout', ['expanded', 'archive'])
def test_generated_bootstrap_matches_local_plan(tmp_path, layout):
    deploy = ROOT / '.kaggle-deploy/v161-no-write'
    notebook = json.loads((deploy/'kernel/30_migrate_v16.ipynb').read_text(encoding='utf-8'))
    package = deploy/'package/v161-no-write.zip'
    inputs, working = tmp_path/'input', tmp_path/'working'
    inputs.mkdir()
    working.mkdir()
    if layout == 'expanded':
        with zipfile.ZipFile(package) as archive:
            archive.extractall(inputs/'dataset')
    else:
        (inputs/'v161-no-write.zip').write_bytes(package.read_bytes())
    source = ''.join(notebook['cells'][1]['source'])
    source = source.replace('/kaggle/input', inputs.as_posix()).replace('/kaggle/working', working.as_posix())
    result = subprocess.run([sys.executable, '-c', source], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
    checks = json.loads((working/'v16_migration/baseline-v15-live/acceptance_checks.json').read_text(encoding='utf-8'))
    assert checks['local_remote_plan_equal'] is True
    assert checks['gates']['update_count'] == 70
    assert checks['gates']['remote_writes'] == 0
