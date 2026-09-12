import importlib.util
from pathlib import Path
import tempfile
import unittest
from gi.repository import Gio

ROOT = Path(__file__).resolve().parents[1]


class DesktopIdentity(unittest.TestCase):
    def test_launcher_matches_application_and_installs_resolvable_icon(self):
        path = ROOT / 'tools/desktop_entry.py'
        self.assertTrue(path.exists(), 'desktop integration helper is missing')
        spec = importlib.util.spec_from_file_location('desktop_entry', path)
        helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data'; desktop = Path(tmp) / 'Desktop'
            app = data / 'projectscope/app'
            (app / 'assets').mkdir(parents=True)
            (app / 'assets/projectscope.svg').write_bytes((ROOT / 'assets/projectscope.svg').read_bytes())
            (app / 'assets/projectscope.png').write_bytes((ROOT / 'assets/projectscope.png').read_bytes())
            (app / 'launch.py').write_text('')
            (data / 'applications').mkdir()
            legacy = data / 'applications/projectscope.desktop'
            legacy.write_text('[Desktop Entry]\nType=Application\nName=ProjectScope\nExec=python3\n')
            helper.install_launchers(app, data, desktop, '/usr/bin/python3')
            entry = Gio.DesktopAppInfo.new_from_filename(str(data / 'applications/io.projectscope.Crosshair.desktop'))
            self.assertEqual(entry.get_name(), 'ProjectScope')
            self.assertEqual(entry.get_icon().to_string(), 'io.projectscope.Crosshair')
            icon = data / 'icons/hicolor/scalable/apps/io.projectscope.Crosshair.svg'
            self.assertEqual(icon.read_bytes(), (ROOT / 'assets/projectscope.svg').read_bytes())
            raster = data / 'icons/hicolor/128x128/apps/io.projectscope.Crosshair.png'
            self.assertEqual(raster.read_bytes(), (ROOT / 'assets/projectscope.png').read_bytes())
            self.assertTrue((desktop / 'ProjectScope.desktop').exists())
            self.assertTrue(Gio.DesktopAppInfo.new_from_filename(str(legacy)).get_nodisplay())
            helper.remove_icons(data, helper.APP_ID)
            self.assertFalse(icon.exists())
            self.assertFalse(raster.exists())
