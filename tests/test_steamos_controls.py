import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from gi.repository import Gio
from projectscope.profiles import load_profile, loads_profile, dumps_profile, validate_profile
from projectscope.settings import SCHEMA
from projectscope.gamescope.controls import COLORS, next_color, random_profile, save_current
from projectscope.gamescope.control import command, quit_all

ROOT = Path(__file__).resolve().parents[1]

class PresetControlsTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_profile(ROOT / 'presets/cs2-precision.json')
        source = Gio.SettingsSchemaSource.new_from_directory(
            str(ROOT / 'extension/schemas'), Gio.SettingsSchemaSource.get_default(), False)
        self.cfg = Gio.Settings.new_full(source.lookup(SCHEMA, False), Gio.memory_settings_backend_new(), None)
        self.cfg.set_string('profile', dumps_profile(self.profile))

    def test_random_compact_valid_and_preserves_opacity(self):
        rng = random.Random(42)
        families = set()
        for _ in range(100):
            profile = random_profile(self.profile, rng)
            self.assertEqual(profile, validate_profile(profile))
            self.assertEqual(profile['style']['opacity'], self.profile['style']['opacity'])
            self.assertLessEqual(profile['style']['lines']['length'], 8)
            self.assertLessEqual(profile['style']['circle']['radius'], 7)
            families.add(tuple(profile['style'][key]['enabled'] for key in ('lines', 'dot', 'circle')))
        self.assertEqual(len(families), 4)

    def test_colors_wrap_and_preserve_geometry(self):
        profile = self.profile
        profile['style']['color'] = COLORS[-1]
        updated = next_color(profile)
        self.assertEqual(updated['style']['color'], COLORS[0])
        self.assertEqual(updated['style']['outline_color'], '#000000')
        self.assertEqual(updated['style']['lines'], profile['style']['lines'])
        self.assertEqual(profile['style']['color'], COLORS[-1])
        self.assertEqual(next_color(updated)['style']['outline_color'], '#FFFFFF')

    def test_save_current_refreshes_library_and_replaces_named_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'personal'
            first = save_current(self.cfg, directory, Path(temp) / 'stock')
            self.assertTrue((directory / (first['id'] + '.json')).exists())
            command(self.cfg, 'color')
            second = save_current(self.cfg, directory, Path(temp) / 'stock')
            self.assertEqual(first['id'], second['id'])
            self.assertEqual(len(list(directory.glob('*.json'))), 1)
            self.assertEqual(loads_profile(self.cfg.get_strv('preset-library')[0]), second)

    def test_commands_resize_and_thickness_use_shared_steps(self):
        self.cfg.set_boolean('og-controls', False)
        command(self.cfg, 'size-up')
        bigger = loads_profile(self.cfg.get_string('profile'))
        self.assertEqual(bigger['style']['scale'], self.profile['style']['scale'] + .25)
        command(self.cfg, 'size-down')
        command(self.cfg, 'thicker')
        thick = loads_profile(self.cfg.get_string('profile'))
        self.assertEqual(thick['style']['lines']['thickness'], self.profile['style']['lines']['thickness'] + .25)
        command(self.cfg, 'thinner')
        self.assertEqual(loads_profile(self.cfg.get_string('profile')), self.profile)

    def test_color_command_disables_inversion(self):
        self.cfg.set_boolean('invert-crosshair', True)
        command(self.cfg, 'color')
        self.assertFalse(self.cfg.get_boolean('invert-crosshair'))

    def test_quit_stops_backend_even_if_studio_absent(self):
        from gi.repository import GLib
        with patch('projectscope.gamescope.control.Gio.bus_get_sync', side_effect=GLib.Error('missing')), \
                patch('projectscope.gamescope.control.stop') as stop:
            quit_all()
            stop.assert_called_once_with()

    def test_quit_from_studio_avoids_synchronous_self_call(self):
        from unittest.mock import Mock
        app = Mock()
        app.get_application_id.return_value = 'io.projectscope.SteamOS'
        with patch('projectscope.gamescope.control.Gio.Application.get_default', return_value=app), \
                patch('projectscope.gamescope.control.Gio.bus_get_sync') as bus, \
                patch('projectscope.gamescope.control.stop') as stop:
            quit_all()
            bus.assert_not_called()
            stop.assert_called_once_with()
            app.quit.assert_called_once_with()
