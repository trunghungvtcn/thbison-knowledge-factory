"""Build only allowlisted source assets; never bundle credentials or old outputs."""
import json
import shutil
import zipfile
from pathlib import Path

from percent_to_ipynb import convert

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.kaggle-deploy' / 'release-20260904'
OUT.mkdir(parents=True, exist_ok=True)
package = OUT / 'package'
package.mkdir(exist_ok=True)
shutil.copy2(ROOT / '.kaggle-deploy/package/dataset-metadata.json', package / 'dataset-metadata.json')
with zipfile.ZipFile(package / 'kf-pilot-package.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for folder in ('src', 'config', 'tests'):
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in {'.py', '.yaml', '.json', '.csv'}:
                archive.write(path, path.relative_to(ROOT).as_posix())
    archive.write(ROOT / 'requirements.txt', 'requirements.txt')
for kind, filename in [('extract', '10_extract_and_ocr'), ('claims', '20_claims_score_notion')]:
    target = OUT / kind
    target.mkdir(exist_ok=True)
    convert(ROOT / 'notebooks' / (filename + '.py'), target / (filename + '.ipynb'))
    metadata = json.loads((ROOT / '.kaggle-deploy' / (kind + '-kernel') / 'kernel-metadata.json').read_text())
    metadata['is_private'] = True
    (target / 'kernel-metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    if kind == 'claims':
        path = target / (filename + '.ipynb')
        notebook = json.loads(path.read_text(encoding='utf-8'))
        notebook['cells'].insert(1, {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': ['import os\nos.environ["KF_NOTION_ENABLED"] = "1"\n']})
        path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding='utf-8')
print(str(OUT))
