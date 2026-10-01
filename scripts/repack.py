# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
"""Repack from the retained final image, never from deleted experimental partitions."""
import argparse,hashlib,json,pathlib,subprocess,tempfile,re,stat

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(args):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True)
    if r.returncode:raise RuntimeError(r.stderr or r.stdout)
    return r.stdout

def safe_debugfs_path(value):
    if not value or any(c.isspace() or c in '"\\' for c in value):
        raise ValueError('debugfs paths must not contain whitespace, quotes or backslashes')
    return value

def read_ext4_metadata(image, inside, work):
    output=run(['/usr/sbin/debugfs','-R','stat '+inside,image])
    if not output.strip():return None
    info=re.search(r'Type:\s+regular\s+Mode:\s+([0-7]+)',output)
    owners=re.search(r'User:\s+(\d+)\s+Group:\s+(\d+)',output)
    if not info or not owners:raise ValueError('Replacement must be a regular file: '+inside)
    attrs={}
    for name in re.findall(r'^\s+(\S+) \(\d+\) =',output,re.M):
        safe_debugfs_path(name)
        dst=work/('xattr-'+str(len(attrs)))
        if dst.exists():dst.unlink()
        run(['/usr/sbin/debugfs','-R','ea_get -f '+str(dst)+' '+inside+' '+name,image])
        if not dst.exists():raise ValueError('Cannot read xattr '+name)
        attrs[name]=dst.read_bytes()
    return {'mode':stat.S_IFREG|int(info.group(1),8),'uid':int(owners.group(1)),
            'gid':int(owners.group(2)),'attrs':attrs}

def replace_ext4_file(image, entry, work):
    inside=safe_debugfs_path(entry['path']);source=pathlib.Path(entry['source']).resolve()
    safe_debugfs_path(str(source))
    if not inside.startswith('/') or '..' in pathlib.PurePosixPath(inside).parts:
        raise ValueError('Invalid absolute ext4 path')
    if not source.is_file():raise ValueError('Source must be a regular file')
    old=read_ext4_metadata(image,inside,work)
    if old is None and ('mode' not in entry or not entry.get('selinux')):
        raise ValueError('New files require explicit mode and SELinux label')
    expected=old or {'mode':stat.S_IFREG|0o644,'uid':0,'gid':0,'attrs':{}}
    mode=entry.get('mode')
    if mode is not None:
        if not re.fullmatch(r'0?[0-7]{5,6}',mode) or int(mode,8)&stat.S_IFMT(0o170000)!=stat.S_IFREG:
            raise ValueError('mode must be an octal regular-file mode')
        expected['mode']=int(mode,8)
    for name in ['uid','gid']:
        if name in entry:
            value=entry[name]
            if not isinstance(value,int) or isinstance(value,bool) or not 0<=value<=0xffffffff:
                raise ValueError('Invalid '+name)
            expected[name]=value
    if entry.get('selinux'):
        label=entry['selinux']
        if any(c.isspace() or c=='\0' for c in label):raise ValueError('Invalid SELinux label')
        expected['attrs']['security.selinux']=label.encode()+b'\0'
    if 'security.selinux' not in expected['attrs']:
        raise ValueError('Replacement needs a SELinux label')
    commands=('rm '+inside+'\n' if old else '')+'write '+str(source)+' '+inside+'\n'
    for name in ['mode','uid','gid']:
        value='0'+format(expected[name],'o') if name=='mode' else str(expected[name])
        commands+='set_inode_field '+inside+' '+name+' '+value+'\n'
    for i,(name,value) in enumerate(expected['attrs'].items()):
        data=work/('write-xattr-'+str(i));data.write_bytes(value)
        commands+='ea_set -f '+str(data)+' '+inside+' '+name+'\n'
    script=work/'debugfs.commands';script.write_text(commands)
    run(['/usr/sbin/debugfs','-w','-f',script,image])
    readback=work/'readback.bin'
    if readback.exists():readback.unlink()
    run(['/usr/sbin/debugfs','-R','dump '+inside+' '+str(readback),image])
    if not readback.exists() or digest(source)!=digest(readback):raise ValueError('Write verification failed: '+inside)
    readback.unlink()
    actual=read_ext4_metadata(image,inside,work)
    if actual!=expected:raise ValueError('Ownership/mode/xattr verification failed: '+inside)

def remove_ext4_app(image, inside):
    """Delete one explicitly named application directory in an offline image."""
    safe_debugfs_path(inside)
    parts=pathlib.PurePosixPath(inside).parts
    allowed=(len(parts)==4 and parts[1:3] in [('system','app'),('system','priv-app')]) or (len(parts)==3 and parts[1] in ('app','priv-app'))
    if not inside.startswith('/') or '..' in parts or not allowed:
        raise ValueError('remove-app requires one app directory below app/priv-app')
    initial=run(['/usr/sbin/debugfs','-R','stat '+inside,image])
    if not initial.strip():raise ValueError('Application directory missing: '+inside)
    if 'Type: directory' not in initial:raise ValueError('Application root must be a directory')
    def delete(path):
        listing=run(['/usr/sbin/debugfs','-R','ls -p '+path,image])
        for line in listing.splitlines():
            fields=line.split('/')
            if len(fields)<7 or not fields[1].isdigit():continue
            name=fields[5]
            if name in ('.','..'):continue
            safe_debugfs_path(name)
            child=path+'/'+name
            mode=int(fields[2],8)
            if stat.S_ISDIR(mode):delete(child)
            else:run(['/usr/sbin/debugfs','-w','-R','rm '+child,image])
        run(['/usr/sbin/debugfs','-w','-R','rmdir '+path,image])
    delete(inside)
    if run(['/usr/sbin/debugfs','-R','stat '+inside,image]).strip():
        raise ValueError('Application removal failed: '+inside)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',type=pathlib.Path,required=True)
    ap.add_argument('--verification',type=pathlib.Path)
    ap.add_argument('--output',type=pathlib.Path,required=True)
    ap.add_argument('--changes',type=pathlib.Path,help='JSON array: partition/path and op=remove-app, or source with optional mode/selinux for replacement')
    ap.add_argument('--tools',type=pathlib.Path,required=True)
    args=ap.parse_args();base=args.base.resolve();output=args.output.resolve()
    if output.exists() or output==base:raise ValueError('Output must be a new path')
    vf=args.verification or base.parent/'verification.json';metadata=json.loads(vf.read_text())
    if digest(base)!=metadata['sha256']:raise ValueError('Base image hash does not match verification.json')
    changes=json.loads(args.changes.read_text()) if args.changes else []
    with tempfile.TemporaryDirectory(prefix='rk3518-final-repack-') as td:
        work=pathlib.Path(td);expected={}
        run([args.tools/'lpunpack',base,work])
        for name,info in metadata['partitions'].items():
            p=work/(name+'.img')
            if digest(p)!=info['sha256']:raise ValueError('Partition hash mismatch: '+name)
        for entry in changes:
            name=entry['partition']
            if name not in metadata['partitions']:raise ValueError('Invalid partition')
            operation=entry.get('op','replace')
            if operation=='remove-app':remove_ext4_app(work/(name+'.img'),entry['path'])
            elif operation=='replace':replace_ext4_file(work/(name+'.img'),entry,work)
            else:raise ValueError('Unknown image operation: '+operation)
        lpmake=[args.tools/'lpmake','--metadata-size','65536','--metadata-slots','2','--device','super:2516582400','--group','rockchip_dynamic_partitions:2512388096','--force-full-image','--output',output]
        for name in metadata['partitions']:
            p=work/(name+'.img');run(['/usr/sbin/e2fsck','-fn',p])
            expected[name]={'size':p.stat().st_size,'sha256':digest(p)}
            lpmake+=['--partition',f'{name}:readonly:{p.stat().st_size}:rockchip_dynamic_partitions','--image',f'{name}={p}']
        output.parent.mkdir(parents=True,exist_ok=True);run(lpmake)
        verify=work/'verify';verify.mkdir()
        for name,info in expected.items():
            run([args.tools/'lpunpack','-p',name,output,verify]);p=verify/(name+'.img')
            if digest(p)!=info['sha256']:raise ValueError('Packed partition verification failed: '+name)
            p.unlink()
        result={'sha256':digest(output),'size':output.stat().st_size,'super_start_lba':'0x001FD000','partitions':expected,'base_sha256':metadata['sha256'],'changes':changes}
        output.with_suffix('.verification.json').write_text(json.dumps(result,indent=2))
        print(json.dumps({'output':str(output),'sha256':result['sha256'],'verified_partitions':len(expected)}))
if __name__=='__main__':main()
