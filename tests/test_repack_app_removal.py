#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('repack',ROOT/'scripts/repack.py')
repack=importlib.util.module_from_spec(spec);spec.loader.exec_module(repack)

class OfflineAppRemoval(unittest.TestCase):
    def test_removal_keeps_keyboard_and_rejects_system_root(self):
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory);content=work/'content'
            for name in ['Lightning','Traceur','BoxLatinIME']:
                app=content/'system/app'/name;app.mkdir(parents=True)
                (app/(name+'.apk')).write_bytes(name.encode())
                oat=app/'oat/arm64';oat.mkdir(parents=True)
                (oat/'base.odex').write_bytes(b'compiled fixture')
            image=work/'system.img'
            with image.open('wb') as f:f.truncate(16*1024*1024)
            subprocess.run(['/usr/sbin/mke2fs','-q','-t','ext4','-F','-d',str(content),str(image)],check=True)
            for path in ['/system','/system/app','/vendor/lib64','/system/app/../BoxLatinIME']:
                with self.assertRaises(ValueError):repack.remove_ext4_app(image,path)
            for name in ['Lightning','Traceur']:
                repack.remove_ext4_app(image,'/system/app/'+name)
                self.assertFalse(repack.run(['/usr/sbin/debugfs','-R','stat /system/app/'+name,image]).strip())
            self.assertEqual(repack.run(['/usr/sbin/debugfs','-R','cat /system/app/BoxLatinIME/BoxLatinIME.apk',image]),'BoxLatinIME')
            subprocess.run(['/usr/sbin/e2fsck','-fn',str(image)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__':unittest.main()

