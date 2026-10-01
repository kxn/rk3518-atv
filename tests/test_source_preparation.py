#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise preparation across native SDK and AOSP project boundaries."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/project.py'

class PreparationTest(unittest.TestCase):
    def test_pinned_sdk_copy_and_local_edit_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); project=root/'entry'; work=root/'work'
            (project/'scripts').mkdir(parents=True); (project/'patches').mkdir()
            shutil.copy2(SCRIPT,project/'scripts/project.py')
            series=[]; locks=[]
            for path,scope in [('src/aic8800','workspace'),('device/rockchip/common','aosp')]:
                tree=work/path if scope=='workspace' else work/'src/aosp'/path
                tree.mkdir(parents=True)
                def git(*args):
                    return subprocess.check_output(['git',*args],cwd=tree,stderr=subprocess.DEVNULL)
                git('init','--quiet'); git('config','user.name','Fixture'); git('config','user.email','fixture@example.invalid')
                (tree/'driver.c').write_text('int feature = 0;\n')
                git('add','.'); git('commit','--quiet','-m','Upstream')
                revision=git('rev-parse','HEAD').decode().strip()
                (tree/'driver.c').write_text('int feature = 1;\n')
                name=path.replace('/','__')+'.patch'
                (project/'patches'/name).write_bytes(git('diff','HEAD'))
                git('checkout','--','driver.c')
                series.append(dict(path=path,scope=scope,base=revision,patch='patches/'+name))
                if scope=='workspace':
                    locks.append(dict(path=path,url='https://example.invalid/unused.git',revision=revision))
            mapping=[dict(source='src/aic8800/driver.c',destination='hardware/aic/driver.c')]
            for name,data in [('patches/series.json',series),('sources.lock.json',locks),('source-imports.json',mapping)]:
                (project/name).write_text(json.dumps(data))
            (work/'src/device-support/overlays').mkdir(parents=True)
            security=work/'src/aosp/device/rockchip/common/security'; security.mkdir()
            keys=work/'src/aosp/build/target/product/security'; keys.mkdir(parents=True)
            for extension in ('pk8','x509.pem'):(keys/('platform.'+extension)).write_text('PUBLIC DEVELOPMENT FIXTURE\n')
            (work/'src/rk-kernel').mkdir()
            def prepare(command='apply'):
                return subprocess.run(['python3',str(project/'scripts/project.py'),command,'--workspace',str(work)],capture_output=True,text=True)
            self.assertEqual(prepare().returncode,0)
            imported=work/'src/aosp/hardware/aic/driver.c'
            self.assertEqual(imported.read_text(),'int feature = 1;\n')
            self.assertEqual(prepare().returncode,0)
            # Native checkout has expected uncommitted patches: don't reset it.
            self.assertEqual(prepare('native').returncode,0)
            imported.write_text('a downstream user edit\n')
            result=prepare()
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Mapped upstream files changed',result.stderr)
            self.assertEqual(imported.read_text(),'a downstream user edit\n')
            imported.write_text('int feature = 1;\n')
            native=work/'src/aic8800/driver.c'; native.write_text('another user edit\n')
            result=prepare('native')
            self.assertNotEqual(result.returncode,0)
            self.assertIn('changed since preparation',result.stderr)
            self.assertEqual(native.read_text(),'another user edit\n')

if __name__=='__main__': unittest.main()

