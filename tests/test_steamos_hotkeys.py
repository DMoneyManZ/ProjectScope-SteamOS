import ctypes as C
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from projectscope.gamescope.hotkey import BINDINGS, Hotkeys, HotkeyManager, XEvent, discover_displays, lock_variants


class HotkeyEventsTests(unittest.TestCase):
    def make_hotkeys(self):
        keys = Hotkeys.__new__(Hotkeys)
        keys.callback = Mock()
        keys.bindings = {(10, 0): 'previous', (10, 1): 'size-up', (10, 4): 'thicker'}
        keys.down = set()
        keys.lock_mask = 18
        return keys

    def test_locks_repeat_modifier_release(self):
        keys = self.make_hotkeys()
        keys.handle_event(True, 10, 19)
        keys.handle_event(True, 10, 19)
        keys.handle_event(False, 10, 18)
        keys.handle_event(True, 10, 4)
        self.assertEqual([call.args[0] for call in keys.callback.call_args_list], ['size-up', 'thicker'])

    def test_unassigned_modifier_never_fires(self):
        keys = self.make_hotkeys()
        keys.handle_event(True, 10, 5)
        keys.callback.assert_not_called()

    def test_non_detectable_repeat_pair_ignored(self):
        keys = self.make_hotkeys()
        keys.display = 1
        keys.detectable_repeat = False
        events = [(2, 10, 0, 1), (3, 10, 0, 2), (2, 10, 0, 2), (3, 10, 0, 3), (2, 10, 0, 4)]
        def write(ptr, values):
            event = C.cast(ptr, C.POINTER(XEvent)).contents
            event.type, event.key.keycode, event.key.state, event.key.time = values
        keys.lib = Mock()
        keys.lib.XPending.side_effect = lambda _display: len(events)
        keys.lib.XNextEvent.side_effect = lambda _display, ptr: write(ptr, events.pop(0))
        keys.lib.XPeekEvent.side_effect = lambda _display, ptr: write(ptr, events[0])
        keys.read()
        self.assertEqual(keys.callback.call_count, 2)

    def test_disconnected_server_cleanup_avoids_fatal_xlib_flush(self):
        import select
        keys = self.make_hotkeys()
        keys.display = 50
        keys.watch = None
        keys.disconnected = False
        keys.lib = Mock()
        keys.lib.XConnectionNumber.return_value = 7
        with patch('projectscope.gamescope.hotkey.select.poll',
                   return_value=Mock(poll=Mock(return_value=[(7, select.POLLHUP)]))), \
                patch('projectscope.gamescope.hotkey.os.close') as close:
            keys.close()
            close.assert_called_once_with(7)
            keys.lib.XCloseDisplay.assert_not_called()
            self.assertIsNone(keys.display)

    def test_all_requested_bindings_exist(self):
        self.assertEqual(len(BINDINGS), 11)
        self.assertIn(('space', 12, 'menu'), BINDINGS)
        self.assertEqual(lock_variants(18), [0, 2, 16, 18])

    def test_discovery_matches_compositor_and_rejects_other_session(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ('X0', 'X1', 'X2', 'X3', 'X1bad'):
                (Path(temp) / name).touch()
            roots = {':0': (100, 0), ':1': (100, 1), ':2': (200, 0), ':3': (None, None)}
            self.assertEqual(discover_displays(':0', roots.__getitem__, Path(temp)), [':0', ':1'])

    def test_manager_refresh_and_mode_preserve_bridge_registration(self):
        discovered = [':0', ':1']
        with patch('projectscope.gamescope.hotkey.Hotkeys') as constructor, \
                patch('gi.repository.GLib.timeout_add_seconds', return_value=99), \
                patch('gi.repository.GLib.source_remove'):
            constructor.side_effect = lambda *a, **kw: Mock(display=object())
            manager = HotkeyManager(Mock(), ':0', discover=lambda _: discovered)
            removed = manager.registrations[':1']
            discovered[:] = [':0', ':2']
            manager.refresh()
            removed.close.assert_called_once()
            self.assertEqual(set(manager.registrations), {':0', ':2'})
            manager.set_keyboard_enabled(False)
            self.assertTrue(all(call.kwargs['keyboard_enabled'] is False for call in constructor.call_args_list[-2:]))
            remaining = list(manager.registrations.values())
            manager.close()
            for registration in remaining:
                registration.close.assert_called_once()


class HotkeyRegistrationTests(unittest.TestCase):
    def library(self):
        lib = Mock()
        lib.XOpenDisplay.return_value = 50
        lib.XDefaultRootWindow.return_value = 100
        lib.XConnectionNumber.return_value = 5
        symbols = {name: index + 10 for index, (name, _, _) in enumerate(BINDINGS)}
        lib.XStringToKeysym.side_effect = lambda name: symbols[name.decode()]
        lib.XKeysymToKeycode.side_effect = lambda _display, symbol: symbol
        lib.XSetErrorHandler.return_value = None
        return lib, symbols

    def test_conflict_rolls_back_only_its_lock_variants(self):
        lib, symbols = self.library()
        handler = [None]
        conflict = [True]
        def set_handler(value):
            previous = handler[0]
            handler[0] = value
            return previous
        def sync(*_):
            if conflict[0] and lib.XGrabKey.call_args.args[1] == symbols['Home']:
                conflict[0] = False
                C.cast(handler[0], C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_void_p))(None, None)
        lib.XSetErrorHandler.side_effect = set_handler
        lib.XSync.side_effect = sync
        with patch('projectscope.gamescope.hotkey.C.CDLL', return_value=lib), \
                patch('projectscope.gamescope.hotkey.select.poll', return_value=Mock(poll=Mock(return_value=[]))), \
                patch.object(Hotkeys, '_lock_mask', return_value=18), \
                patch('gi.repository.GLib.io_add_watch', return_value=9), \
                patch('gi.repository.GLib.source_remove'):
            hotkeys = Hotkeys(Mock(), display=':8')
            lib.XOpenDisplay.assert_called_once_with(b':8')
            self.assertEqual(hotkeys.conflicts, ['toggle'])
            self.assertIn('menu', hotkeys.bindings.values())
            self.assertIn('color', hotkeys.bindings.values())
            self.assertEqual(lib.XUngrabKey.call_count, 4)
            self.assertTrue(all(call.args[1] == symbols['Home'] for call in lib.XUngrabKey.call_args_list))
            self.assertIsNone(handler[0])
            hotkeys.close()
            hotkeys.close()
            lib.XCloseDisplay.assert_called_once_with(50)

    def test_controller_mode_registers_only_menu_and_failed_setup_closes(self):
        lib, _ = self.library()
        with patch('projectscope.gamescope.hotkey.C.CDLL', return_value=lib), \
                patch('projectscope.gamescope.hotkey.select.poll', return_value=Mock(poll=Mock(return_value=[]))), \
                patch.object(Hotkeys, '_lock_mask', return_value=18), \
                patch('gi.repository.GLib.io_add_watch', side_effect=RuntimeError('watch failed')):
            with self.assertRaises(RuntimeError):
                Hotkeys(Mock(), keyboard_enabled=False, display=':8')
            self.assertEqual(lib.XGrabKey.call_count, 4)
            lib.XCloseDisplay.assert_called_once_with(50)
