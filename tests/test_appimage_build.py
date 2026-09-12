import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_appimage

ROOT = Path(__file__).resolve().parents[1]


class AppImageBuildTests(unittest.TestCase):
    def test_appdir_is_structurally_ready_and_runs(self):
        with tempfile.TemporaryDirectory(prefix='scope appdir ') as temp:
            appdir = build_appimage.build_appdir(Path(temp))
            self.assertEqual(build_appimage.check_appdir(appdir), [])
            desktop = (appdir / (build_appimage.APP_ID + '.desktop')).read_text()
            self.assertIn('Exec=projectscope-steamos launch', desktop)
            self.assertNotIn(str(Path.home()), desktop)
            self.assertNotIn(str(ROOT), (appdir / 'AppRun').read_text())
            env = dict(os.environ, GSETTINGS_BACKEND='memory')
            result = subprocess.run([str(appdir / 'AppRun'), '--help'], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('overlay', result.stdout)
            status = subprocess.run([str(appdir / 'usr/bin/projectscope-steamos'), 'status'], env=env, capture_output=True, text=True)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn('"running"', status.stdout)

    def test_check_reports_missing_apprun(self):
        with tempfile.TemporaryDirectory() as temp:
            appdir = build_appimage.build_appdir(Path(temp))
            (appdir / 'AppRun').unlink()
            self.assertIn('missing AppRun', build_appimage.check_appdir(appdir))


if __name__ == '__main__':
    unittest.main()
