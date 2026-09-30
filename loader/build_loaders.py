# SPDX-License-Identifier: Apache-2.0
"""Build recovery containers using pinned Rockchip binaries and LPDDR3 780 MHz.

Run with Python on Linux in this directory. No USB or block-device operations.
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
UPSTREAM = ROOT / 'upstream'
OUTPUT = ROOT / 'delivery'


def main():
    OUTPUT.mkdir(exist_ok=True)
    info = json.loads((ROOT / 'upstream-tree.json').read_text())
    tree = {entry['path']: entry for entry in info['tree']}
    legacy = json.loads((ROOT / 'ddr111-provenance.json').read_text())
    tree[legacy['entry']['path']] = legacy['entry']
    manifest = {'rkbin_commit': info['commit'], 'ddr111_commit': legacy['commit'],
                'hardware_tested': False, 'loaders': []}
    for variant, version in [('primary_ddr111', '1.11'), ('fallback_ddr114', '1.14')]:
        original_ddr = f'bin/rk35/rk3528_ddr_1056MHz_v{version}.bin'
        ddr = f'custom/rk3528_lp3_780_v{version}.bin'
        usb = 'bin/rk35/rk3528_usbplug_v1.04.bin'
        spl = 'bin/rk35/rk3528_spl_v1.07.bin'
        inputs = {}
        for source in [original_ddr, usb, spl, 'tools/boot_merger', 'tools/ddrbin_tool.py']:
            data = (UPSTREAM / source).read_bytes()
            git_blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
            assert git_blob == tree[source]['sha'], f'Upstream mismatch: {source}'
            inputs[source] = {'sha256': hashlib.sha256(data).hexdigest(), 'git_blob': git_blob}
        baseline_config = ROOT / ('ddr111-parameters.txt' if version == '1.11' else 'ddr-default-parameters.txt')
        subprocess.run([sys.executable, str(UPSTREAM / 'tools/ddrbin_tool.py'), 'rk3528',
                        '-g', str(baseline_config), str(UPSTREAM / original_ddr)], check=True)
        (UPSTREAM / 'custom').mkdir(exist_ok=True)
        shutil.copyfile(UPSTREAM / original_ddr, UPSTREAM / ddr)
        params = ROOT / 'lpddr3-780-params.txt'
        params.write_text('lp3_freq=780\n', encoding='ascii')
        result = subprocess.run([sys.executable, str(UPSTREAM / 'tools/ddrbin_tool.py'),
                                 'rk3528', str(params), str(UPSTREAM / ddr)],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        (OUTPUT / f'{variant}-ddr-patch.log').write_text(result.stdout)
        print(result.stdout, end='')
        subprocess.run([sys.executable, str(UPSTREAM / 'tools/ddrbin_tool.py'), 'rk3528',
                        '-g', str(OUTPUT / f'{variant}-parameters.txt'), str(UPSTREAM / ddr)], check=True)
        name = f'rk3518_lpddr3_780MHz_{variant}_usb104_spl107.bin'
        # Keep the upstream chip tag and flags. Both DDR references must match.
        # CREATE_IDB=false avoids producing a flashable ID-block as an extra output.
        ini = f'''[CHIP_NAME]
NAME=RK3528
[VERSION]
MAJOR=1
MINOR=4
[CODE471_OPTION]
NUM=1
Path1={ddr}
Sleep=1
[CODE472_OPTION]
NUM=1
Path1={usb}
[LOADER_OPTION]
NUM=2
LOADER1=FlashData
LOADER2=FlashBoot
FlashData={ddr}
FlashBoot={spl}
[OUTPUT]
PATH=../delivery/{name}
[SYSTEM]
NEWIDB=true
[FLAG]
471_RC4_OFF=true
RC4_OFF=true
CREATE_IDB=false
'''
        config = ROOT / f'{variant}.ini'
        config.write_text(ini, encoding='ascii')
        tool = UPSTREAM / 'tools/boot_merger'
        tool.chmod(tool.stat().st_mode | 0o100)
        result = subprocess.run([str(tool), str(config)], cwd=UPSTREAM, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        (OUTPUT / f'{variant}-build.log').write_text(result.stdout)
        print(result.stdout, end='')
        data = (OUTPUT / name).read_bytes()
        assert data[:4] == b'LDR ', data[:16]
        manifest['loaders'].append({'file': name, 'variant': variant, 'bytes': len(data),
                                   'sha256': hashlib.sha256(data).hexdigest(), 'inputs': inputs,
                                   'ddr_source': original_ddr, 'ddr_payload': ddr,
                                   'ddr_payload_sha256': hashlib.sha256((UPSTREAM / ddr).read_bytes()).hexdigest(),
                                   'parameter_changes': {'lp3_freq': {'old': 1056, 'new': 780}}})
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (OUTPUT / 'SHA256SUMS.txt').write_text(''.join(
        entry['sha256'] + '  ' + entry['file'] + '\n' for entry in manifest['loaders']))


if __name__ == '__main__':
    main()
