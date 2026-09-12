"""Installers must be relocatable and preserve personal presets on removal."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from gi.repository import Gio

ROOT=Path(__file__).resolve().parents[1]

class SteamOSInstallTests(unittest.TestCase):
    def test_install_launch_and_uninstall_in_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='scope home ') as temp:
            home=Path(temp);data=home/'data folder'
            env=dict(os.environ,HOME=str(home),XDG_DATA_HOME=str(data),GSETTINGS_BACKEND='memory')
            subprocess.run([sys.executable,str(ROOT/'tools/install_steamos.py')],env=env,check=True,capture_output=True,text=True)
            cli=home/'.local/bin/projectscope-steamos'
            result=subprocess.run([str(cli),'--help'],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('overlay',result.stdout)
            desktop=Gio.DesktopAppInfo.new_from_filename(str(data/'applications/io.projectscope.SteamOS.desktop'))
            self.assertIsNotNone(desktop)
            self.assertEqual(desktop.get_name(),'ProjectScope SteamOS')
            self.assertTrue(desktop.get_commandline().endswith(' launch'))
            icons=[data/'icons/hicolor'/directory/'apps'/('io.projectscope.SteamOS.'+suffix)
                   for directory,suffix in [('128x128','png'),('scalable','svg')]]
            for icon in icons: self.assertTrue(icon.exists())
            self.assertTrue((data/'projectscope-steamos/app/LICENSE').exists())
            personal=data/'projectscope/presets/personal.json';personal.parent.mkdir(parents=True);personal.write_text('keep')
            subprocess.run([sys.executable,str(ROOT/'tools/install_steamos.py'),'--uninstall'],env=env,check=True,capture_output=True,text=True)
            self.assertFalse(cli.exists());self.assertEqual(personal.read_text(),'keep')
            self.assertFalse((data/'projectscope-steamos/app').exists())
            for icon in icons: self.assertFalse(icon.exists())
