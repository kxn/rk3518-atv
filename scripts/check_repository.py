#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import json, re, subprocess, xml.etree.ElementTree as ET
from pathlib import Path

root=Path(__file__).resolve().parent.parent
manifest=ET.parse(root/'default.xml').getroot()
projects=manifest.findall('project')
assert len(projects)>1300
paths=set()
for p in projects:
    path=p.get('path',p.get('name'))
    assert path not in paths and not Path(path).is_absolute() and '..' not in Path(path).parts
    paths.add(path)
    assert re.fullmatch('[0-9a-f]{40}',p.get('revision','')),path
for entry in json.loads((root/'sources.lock.json').read_text()):
    assert re.fullmatch('[0-9a-f]{40}',entry['revision'])
    assert entry['url'].startswith('https://')
    assert not Path(entry['path']).is_absolute() and '..' not in Path(entry['path']).parts
for entry in json.loads((root/'patches/series.json').read_text()):
    assert (root/entry['patch']).is_file()
    assert re.fullmatch('[0-9a-f]{40}',entry['base'])
    assert entry.get('scope','aosp') in ('aosp','workspace')
for entry in json.loads((root/'proprietary-files.json').read_text()):
    assert re.fullmatch('[0-9a-f]{64}',entry['sha256'])
    assert '..' not in Path(entry['workspace_path']).parts
    if entry.get('required'):assert entry.get('origin'),entry['path']
for f in (root/'scripts').glob('*.py'):
    compile(f.read_text(),str(f),'exec')
    if f.name != Path(__file__).name:
        assert '/home/dl/' not in f.read_text() and '/data/dl/' not in f.read_text()
for f in (root/'scripts').glob('*.sh'):
    subprocess.run(['bash','-n',str(f)],check=True)
print(f'PASS: {len(projects)} pinned manifest projects; source/patch/input locks and scripts checked')

locks=json.loads((root/'sources.lock.json').read_text())
assert not any(item.get('history')=='source snapshot' for item in locks)
for item in locks:
    if item['path'].startswith('src/aosp/'):
        path=item['path'][len('src/aosp/'):]
        project=next(p for p in projects if p.get('path',p.get('name'))==path)
        assert project.get('revision')==item['revision'],path
for item in json.loads((root/'source-imports.json').read_text()):
    for key in ('source','destination'):
        assert not Path(item[key]).is_absolute() and '..' not in Path(item[key]).parts
    assert any(item['source'].startswith(p['path']+'/') for p in locks) or item['source'].startswith('src/aosp/device/rockchip/common/')
for name in ('rk3518-atv-bluetooth','rk3518-atv-u-boot','rk3518-atv-hwcomposer'):
    assert name not in (root/'default.xml').read_text()
    assert name not in (root/'sources.lock.json').read_text()
print('PASS: direct upstream layout; no deprecated snapshot build inputs')
