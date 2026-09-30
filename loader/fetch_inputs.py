#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Restore pinned official rkbin inputs; no USB or block-device operations."""
import hashlib, json, urllib.request
from pathlib import Path

root=Path(__file__).resolve().parent
info=json.loads((root/'upstream-tree.json').read_text())
legacy=json.loads((root/'ddr111-provenance.json').read_text())
entries={entry['path']:(info['commit'],entry) for entry in info['tree']}
entries[legacy['entry']['path']]=(legacy['commit'],legacy['entry'])
names=['bin/rk35/rk3528_ddr_1056MHz_v1.11.bin',
       'bin/rk35/rk3528_ddr_1056MHz_v1.14.bin',
       'bin/rk35/rk3528_usbplug_v1.04.bin','bin/rk35/rk3528_spl_v1.07.bin',
       'tools/boot_merger','tools/ddrbin_tool.py']
for name in names:
    commit,entry=entries[name]
    path=root/'upstream'/name
    data=path.read_bytes() if path.is_file() else None
    def blob_id(payload):return hashlib.sha1(f'blob {len(payload)}\0'.encode()+payload).hexdigest()
    if data is None or blob_id(data)!=entry['sha']:
        url=f'https://raw.githubusercontent.com/rockchip-linux/rkbin/{commit}/{name}'
        with urllib.request.urlopen(url,timeout=60) as response:data=response.read()
    if blob_id(data)!=entry['sha']:raise ValueError('Input hash mismatch: '+name)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if entry.get('mode')=='100755':path.chmod(0o755)
    print(name,hashlib.sha256(data).hexdigest())
