#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fetch the standalone BSP trees, apply pinned patches, and restore inputs."""
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

def run(*args, cwd=None):
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)

def output(*args, cwd=None):
    return subprocess.check_output([str(a) for a in args], cwd=cwd).decode().strip()

def load(name): return json.loads((HERE/name).read_text())

def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def patch_state(work, item):
    target=work/'src/aosp'/item['path']
    patch=HERE/item['patch']
    records=subprocess.check_output(['git','apply','--numstat','-z',str(patch)],cwd=target).decode().split('\0')
    names={record.split('\t',2)[2] for record in records if record}
    overlay=work/'src/device-support/overlays'/item['path']
    if overlay.exists():names.update(str(p.relative_to(overlay)) for p in overlay.rglob('*') if p.is_file())
    files={}
    for name in sorted(names):
        file=target/name
        files[name]=dict(sha256=digest(file),executable=bool(file.stat().st_mode&0o111)) if file.is_file() else None
    return dict(base=item['base'],patch_sha256=digest(patch),files=files)

def saved_states(work):
    file=work/'.rk3518-source-state.json'
    return json.loads(file.read_text()) if file.is_file() else {}

def applied(work,item,states):
    # Product overlays may extend a patched file beyond the original patch's
    # end-of-file context. Verify their saved content, not only reverse apply.
    if item['path'] in states:
        if states[item['path']]!=patch_state(work,item):
            raise RuntimeError('Patched/overlaid files changed since preparation: '+item['path'])
        return True
    return subprocess.run(['git','apply','--reverse','--check',str(HERE/item['patch'])],
                          cwd=work/'src/aosp'/item['path'],capture_output=True).returncode==0

def destination(work, relative):
    result=(work/relative).resolve()
    if not result.is_relative_to(work.resolve()): raise ValueError('Path outside workspace: '+relative)
    return result

def fetch_tree(url, revision, path):
    if not (path/'.git').exists():
        if path.exists() and any(path.iterdir()): raise RuntimeError('Refusing nonempty destination '+str(path))
        path.mkdir(parents=True, exist_ok=True)
        run('git','init',path)
        run('git','remote','add','origin',url,cwd=path)
    # Existing changes are never reset or cleaned.
    if output('git','status','--porcelain',cwd=path): raise RuntimeError('Dirty checkout '+str(path))
    if subprocess.run(['git','cat-file','-e',revision+'^{commit}'],cwd=path,capture_output=True).returncode:
        run('git','fetch','--depth=1','origin',revision,cwd=path)
    run('git','checkout','--detach',revision,cwd=path)

def native(work):
    for item in load('sources.lock.json'):
        if item['path'].startswith('src/aosp/'): continue
        fetch_tree(item['url'],item['revision'],destination(work,item['path']))

def apply(work):
    aosp=work/'src/aosp'
    states=saved_states(work)
    for item in load('patches/series.json'):
        target=destination(aosp,item['path'])
        if output('git','rev-parse','HEAD',cwd=target)!=item['base']:
            raise RuntimeError('Wrong base for '+item['path'])
        patch=HERE/item['patch']
        if applied(work,item,states):
            print('Already applied:',item['path']); continue
        run('git','apply','--check',patch,cwd=target)
        run('git','apply',patch,cwd=target)
    dev=work/'src/device-support'
    for source in (dev/'overlays').rglob('*'):
        if not source.is_file():continue
        target=destination(aosp,str(source.relative_to(dev/'overlays')))
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=source.read_bytes():
            # Only overwrite tracked inputs on the pinned project base, or previously
            # installed identical overlays. A checkout backup is preserved per file.
            backup=work/'.overlay-backups'/source.relative_to(dev/'overlays')
            if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
        shutil.copy2(source,target)
    kernel=work/'src/rk-kernel'; alias=aosp/'kernel-5.10'
    if alias.is_symlink():
        if alias.resolve()!=kernel.resolve():raise RuntimeError('Wrong kernel-5.10 symlink')
    elif alias.exists():raise RuntimeError('kernel-5.10 already exists and is not our alias')
    else:alias.symlink_to(os.path.relpath(kernel,aosp),target_is_directory=True)
    # These are public AOSP DEVELOPMENT keys, not an OEM private key.
    security=aosp/'device/rockchip/common/security'
    for ext in ('pk8','x509.pem'):
        shutil.copy2(aosp/('build/target/product/security/platform.'+ext),security/('nfc.'+ext))
    states={item['path']:patch_state(work,item) for item in load('patches/series.json')}
    state_file=work/'.rk3518-source-state.json'
    temporary=state_file.with_suffix('.tmp')
    temporary.write_text(json.dumps(states,indent=2)+'\n');temporary.replace(state_file)
    print('Applied patches and overlays. Development keys only; no OEM signing keys.')

def inputs(work, supplied, fetch):
    failures=[]
    for item in load('proprietary-files.json'):
        if not item.get('required',True):continue
        target=destination(work,item['workspace_path'])
        if target.is_file() and digest(target)==item['sha256']:continue
        candidate=supplied/item['sha256'] if supplied else None
        data=candidate.read_bytes() if candidate and candidate.is_file() else None
        origin=item.get('origin')
        if data is None and fetch and origin:
            cache=work/'.input-cache'/hashlib.sha256(origin['url'].encode()).hexdigest()[:16]
            if not (cache/'.git').exists():
                cache.mkdir(parents=True,exist_ok=True);run('git','init',cache)
                run('git','remote','add','origin',origin['url'],cwd=cache)
            if subprocess.run(['git','cat-file','-e',origin['revision']+'^{commit}'],cwd=cache,capture_output=True).returncode:
                run('git','fetch','--depth=1','origin',origin['revision'],cwd=cache)
            q=subprocess.run(['git','show',origin['revision']+':'+origin['path']],cwd=cache,capture_output=True)
            if q.returncode==0:data=q.stdout
        if data is None or hashlib.sha256(data).hexdigest()!=item['sha256']:
            failures.append(item['path']);continue
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        if item.get('executable'):target.chmod(0o755)
        print('Restored:',item['path'])
    if failures:raise RuntimeError('Missing/mismatched inputs:\n'+'\n'.join(failures))

def check(work):
    aosp=work/'src/aosp'
    checks=['vendor/rockchip/common/gpu/Mali450/lib/arm/libGLES_mali.so',
            'vendor/rockchip/common/gpu/Mali450/lib/arm64/libGLES_mali.so',
            'vendor/rockchip/common/wifi/firmware/fmacfw_8800d80_h_u02.bin']
    for name in checks:
        if not (aosp/name).is_file():raise RuntimeError('Missing '+name)
    states=saved_states(work)
    for item in load('patches/series.json'):
        if output('git','rev-parse','HEAD',cwd=aosp/item['path'])!=item['base'] or not applied(work,item,states):
            raise RuntimeError('Patch/base check failed: '+item['path'])
    if not (aosp/'packages/apps/BoxRemoteSetup/Android.bp').exists():raise RuntimeError('Missing remote setup')
    print('Pinned patches, runtime driver files and setup application are present.')

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('command',choices=['native','apply','inputs','check'])
parser.add_argument('--workspace',required=True,type=Path)
parser.add_argument('--supplied',type=Path,help='Authorized binary files named by SHA256')
parser.add_argument('--fetch-upstream',action='store_true',help='Restore pinned inputs from their public upstreams; respect upstream licenses')
args=parser.parse_args();work=args.workspace.resolve();work.mkdir(parents=True,exist_ok=True)
try:
    if args.command=='native':native(work)
    elif args.command=='apply':apply(work)
    elif args.command=='inputs':inputs(work,args.supplied,args.fetch_upstream)
    else:check(work)
except (RuntimeError,ValueError,subprocess.CalledProcessError) as e:
    print(str(e),file=sys.stderr);sys.exit(1)
