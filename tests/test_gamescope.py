"""These tests catch invalid state writes and incorrect preset wrapping."""
import unittest
from pathlib import Path
import gi
from gi.repository import Gio
from projectscope.profiles import load_profile, dumps_profile
from projectscope.settings import SCHEMA
from projectscope.gamescope.control import command, cycle_profile

ROOT=Path(__file__).resolve().parents[1]

class GamescopeControlTests(unittest.TestCase):
    def setUp(self):
        self.a=load_profile(ROOT/'presets/cs2-precision.json')
        self.b=load_profile(ROOT/'presets/fps-ring.json')
        source=Gio.SettingsSchemaSource.new_from_directory(
            str(ROOT/"extension/schemas"),Gio.SettingsSchemaSource.get_default(),False)
        self.cfg=Gio.Settings.new_full(source.lookup(SCHEMA,False),
                                      Gio.memory_settings_backend_new(),None)
        self.cfg.set_strv('preset-library',[dumps_profile(self.a),dumps_profile(self.b)])

    def test_cycle_wraps_both_directions(self):
        self.assertEqual(cycle_profile([self.a,self.b],self.b['id'],1)['id'],self.a['id'])
        self.assertEqual(cycle_profile([self.a,self.b],self.a['id'],-1)['id'],self.b['id'])

    def test_unknown_current_selects_endpoint(self):
        self.assertEqual(cycle_profile([self.a,self.b],'missing',1)['id'],self.a['id'])
        self.assertEqual(cycle_profile([self.a,self.b],'missing',-1)['id'],self.b['id'])

    def test_empty_library_leaves_profile_unchanged(self):
        self.cfg.set_strv('preset-library',[])
        before=self.cfg.get_string('profile')
        with self.assertRaises(ValueError): command(self.cfg,'next')
        self.assertEqual(self.cfg.get_string('profile'),before)

    def test_invalid_import_does_not_replace_profile(self):
        before=self.cfg.get_string('profile')
        with self.assertRaises(ValueError): command(self.cfg,'profile','{}')
        self.assertEqual(self.cfg.get_string('profile'),before)

    def test_toggle_and_next_publish_valid_state(self):
        command(self.cfg,'hide'); self.assertFalse(self.cfg.get_boolean('visible'))
        command(self.cfg,'toggle'); self.assertTrue(self.cfg.get_boolean('visible'))
        command(self.cfg,'next')
        self.assertIn('FPS Ring',self.cfg.get_string('profile'))

    def test_invalid_library_entry_skipped(self):
        self.cfg.set_strv('preset-library',['{}',dumps_profile(self.b)])
        command(self.cfg,'next')
        self.assertIn('FPS Ring',self.cfg.get_string('profile'))

    def test_unknown_command_cannot_change_visibility(self):
        before=self.cfg.get_boolean('visible')
        with self.assertRaises(ValueError): command(self.cfg,'shell','anything')
        self.assertEqual(self.cfg.get_boolean('visible'),before)
