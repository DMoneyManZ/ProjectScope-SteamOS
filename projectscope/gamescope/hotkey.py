"""Passive X11 shortcuts only; no keyboard device reading or event logging.

Hotkeys calls callback(action) on one explicit X display. HotkeyManager owns one
registration per Xwayland server belonging to the selected Gamescope PID; call
set_keyboard_enabled when control-mode changes and close during app shutdown.
Ctrl+Alt+Space remains registered in controller-only mode.
"""
import ctypes as C
import ctypes.util
import os
import select
import subprocess
from pathlib import Path

BINDINGS = (
    ('space', 12, 'menu'), ('Home', 0, 'toggle'),
    ('Prior', 0, 'previous'), ('Next', 0, 'next'),
    ('Pause', 0, 'random'), ('Insert', 0, 'save'), ('End', 0, 'color'),
    ('Prior', 1, 'size-up'), ('Next', 1, 'size-down'),
    ('Prior', 4, 'thicker'), ('Next', 4, 'thinner'),
)


class HotkeyLatch:
    def __init__(self): self.down = False
    def event(self, pressed):
        fire = pressed and not self.down
        self.down = pressed
        return fire


class KeyEvent(C.Structure):
    _fields_ = [('type', C.c_int), ('serial', C.c_ulong), ('send_event', C.c_int),
               ('display', C.c_void_p), ('window', C.c_ulong), ('root', C.c_ulong),
               ('subwindow', C.c_ulong), ('time', C.c_ulong), ('x', C.c_int),
               ('y', C.c_int), ('x_root', C.c_int), ('y_root', C.c_int),
               ('state', C.c_uint), ('keycode', C.c_uint), ('same_screen', C.c_int)]


class XEvent(C.Union):
    _fields_ = [('type', C.c_int), ('key', KeyEvent), ('padding', C.c_long * 24)]


class ModifierMap(C.Structure):
    _fields_ = [('max_keypermod', C.c_int), ('modifiermap', C.POINTER(C.c_ubyte))]


class Hotkeys:
    def __init__(self, callback, keyboard_enabled=True, display=None):
        from gi.repository import GLib
        self.glib = GLib
        self.callback = callback
        self.display = None
        self.watch = None
        self.bindings = {}
        self.down = set()
        self.conflicts = []
        self.disconnected = False
        self.lib = C.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6')
        signatures = {
            'XOpenDisplay': ([C.c_char_p], C.c_void_p),
            'XCloseDisplay': ([C.c_void_p], C.c_int),
            'XDefaultRootWindow': ([C.c_void_p], C.c_ulong),
            'XStringToKeysym': ([C.c_char_p], C.c_ulong),
            'XKeysymToKeycode': ([C.c_void_p, C.c_ulong], C.c_ubyte),
            'XGrabKey': ([C.c_void_p, C.c_int, C.c_uint, C.c_ulong, C.c_int, C.c_int, C.c_int], C.c_int),
            'XUngrabKey': ([C.c_void_p, C.c_int, C.c_uint, C.c_ulong], C.c_int),
            'XSync': ([C.c_void_p, C.c_int], C.c_int),
            'XConnectionNumber': ([C.c_void_p], C.c_int),
            'XPending': ([C.c_void_p], C.c_int),
            'XNextEvent': ([C.c_void_p, C.POINTER(XEvent)], C.c_int),
            'XPeekEvent': ([C.c_void_p, C.POINTER(XEvent)], C.c_int),
            'XSetErrorHandler': ([C.c_void_p], C.c_void_p),
            'XkbSetDetectableAutoRepeat': ([C.c_void_p, C.c_int, C.POINTER(C.c_int)], C.c_int),
            'XGetModifierMapping': ([C.c_void_p], C.POINTER(ModifierMap)),
            'XFreeModifiermap': ([C.POINTER(ModifierMap)], C.c_int),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.lib, name)
            function.argtypes = args
            function.restype = result
        self.display = self.lib.XOpenDisplay(display.encode() if display else None)
        if not self.display:
            raise RuntimeError('Cannot open X11 display for shortcuts.')
        try:
            supported = C.c_int()
            self.lib.XkbSetDetectableAutoRepeat(self.display, 1, C.byref(supported))
            self.detectable_repeat = bool(supported.value)
            self.lock_mask = self._lock_mask()
            root = self.lib.XDefaultRootWindow(self.display)
            # Register each logical binding atomically. A conflict disables only
            # that binding; undo its other lock variants before continuing.
            errors = []
            error_type = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_void_p)
            handler = error_type(lambda *_: (errors.append(True), 0)[1])
            old = self.lib.XSetErrorHandler(C.cast(handler, C.c_void_p))
            try:
                for key, modifiers, action in BINDINGS:
                    if not keyboard_enabled and action != 'menu':
                        continue
                    code = self.lib.XKeysymToKeycode(self.display, self.lib.XStringToKeysym(key.encode()))
                    if not code:
                        self.conflicts.append(action)
                        continue
                    errors.clear()
                    variants = {modifiers | locks for locks in lock_variants(self.lock_mask)}
                    for state in variants:
                        self.lib.XGrabKey(self.display, code, state, root, 0, 1, 1)
                    self.lib.XSync(self.display, 0)
                    if errors:
                        for state in variants:
                            self.lib.XUngrabKey(self.display, code, state, root)
                        self.lib.XSync(self.display, 0)
                        self.conflicts.append(action)
                    else:
                        self.bindings[(code, modifiers)] = action
            finally:
                self.lib.XSetErrorHandler(old)
            self.watch = GLib.io_add_watch(
                self.lib.XConnectionNumber(self.display),
                GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self._ready)
        except Exception:
            self.close()
            raise

    def _lock_mask(self):
        mask = 2  # CapsLock's standard LockMask.
        codes = {self.lib.XKeysymToKeycode(self.display, self.lib.XStringToKeysym(name))
                 for name in (b'Num_Lock', b'Scroll_Lock')}
        codes.discard(0)
        mapping = self.lib.XGetModifierMapping(self.display)
        if mapping:
            try:
                count = mapping.contents.max_keypermod
                for modifier in range(8):
                    if any(mapping.contents.modifiermap[modifier * count + offset] in codes
                           for offset in range(count)):
                        mask |= 1 << modifier
            finally:
                self.lib.XFreeModifiermap(mapping)
        return mask

    def _ready(self, _fd, condition):
        if condition & (self.glib.IO_HUP | self.glib.IO_ERR):
            # Do not call XPending on a disconnected server (Xlib exits on I/O
            # errors). The manager will retire this registration on refresh.
            self.watch = None
            self.disconnected = True
            self.close()
            return False
        return self.read()

    def handle_event(self, pressed, keycode, state):
        """Release by physical key even if modifiers were released first."""
        if not pressed:
            self.down.discard(keycode)
            return
        if keycode in self.down:
            return
        self.down.add(keycode)
        action = self.bindings.get((keycode, (state & 255) & ~self.lock_mask))
        if action:
            self.callback(action)

    def read(self):
        while self.display and self.lib.XPending(self.display):
            event = XEvent()
            self.lib.XNextEvent(self.display, C.byref(event))
            if event.type not in (2, 3):
                continue
            if event.type == 3 and not self.detectable_repeat and self.lib.XPending(self.display):
                following = XEvent()
                self.lib.XPeekEvent(self.display, C.byref(following))
                if (following.type == 2 and following.key.keycode == event.key.keycode
                        and following.key.time == event.key.time):
                    self.lib.XNextEvent(self.display, C.byref(following))
                    continue
            self.handle_event(event.type == 2, event.key.keycode, event.key.state)
        return True

    def close(self):
        if self.watch is not None:
            self.glib.source_remove(self.watch)
            self.watch = None
        if self.display:
            if not self.disconnected:
                poller = select.poll()
                poller.register(self.lib.XConnectionNumber(self.display), select.POLLHUP | select.POLLERR)
                self.disconnected = any(condition & (select.POLLHUP | select.POLLERR | select.POLLNVAL)
                                        for _, condition in poller.poll(0))
            if self.disconnected:
                # XCloseDisplay flushes requests and invokes Xlib's fatal I/O
                # handler on a dead server. Close its fd directly instead. The
                # small Xlib allocation is deliberately retained until exit.
                try: os.close(self.lib.XConnectionNumber(self.display))
                except OSError: pass
            else:
                self.lib.XCloseDisplay(self.display)
            self.display = None
        self.down.clear()


def lock_variants(mask):
    variants = [0]
    for bit in range(8):
        if mask & (1 << bit):
            variants += [value | (1 << bit) for value in variants]
    return variants


class MenuHotkey(Hotkeys):
    """Compatibility wrapper for the original no-argument menu callback."""
    def __init__(self, callback, display=None):
        super().__init__(lambda _action: callback(), keyboard_enabled=False, display=display)


def discover_displays(display, root_info=None, socket_directory=Path('/tmp/.X11-unix')):
    """Only inspect X root properties; match the selected compositor PID."""
    if root_info is None:
        from .overlay import root_info
    try:
        pid, _ = root_info(display)
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return [display]
    if pid is None:
        return [display]
    result = {display}
    for socket in socket_directory.glob('X[0-9]*'):
        suffix = socket.name[1:]
        if not suffix.isdigit():
            continue
        candidate = ':' + suffix
        if candidate == display:
            continue
        try:
            other_pid, _ = root_info(candidate)
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            continue
        if other_pid == pid:
            result.add(candidate)
    return sorted(result)


class HotkeyManager:
    """Refresh same-session servers; close removed registrations and retry failures."""
    def __init__(self, callback, display=None, keyboard_enabled=True, discover=None):
        from gi.repository import GLib
        self.glib = GLib
        self.callback = callback
        self.display = display or os.environ.get('DISPLAY', '')
        self.keyboard_enabled = keyboard_enabled
        self.discover = discover or discover_displays
        self.registrations = {}
        self.errors = {}
        self.timer = None
        self.refresh()
        self.timer = GLib.timeout_add_seconds(3, self.refresh)

    def refresh(self):
        try:
            displays = set(self.discover(self.display))
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            displays = set(self.registrations)
        for display, registration in list(self.registrations.items()):
            if not registration.display:
                registration.close()
                del self.registrations[display]
        for display in set(self.registrations) - displays:
            self.registrations.pop(display).close()
        self.errors = {}
        for display in displays - self.registrations.keys():
            try:
                self.registrations[display] = Hotkeys(
                    self.callback, keyboard_enabled=self.keyboard_enabled, display=display)
            except (OSError, RuntimeError) as exc:
                self.errors[display] = str(exc)
        return True

    def set_keyboard_enabled(self, enabled):
        if self.keyboard_enabled == enabled:
            return
        self.keyboard_enabled = enabled
        for hotkeys in self.registrations.values():
            hotkeys.close()
        self.registrations.clear()
        self.refresh()

    def close(self):
        if self.timer is not None:
            self.glib.source_remove(self.timer)
            self.timer = None
        for hotkeys in self.registrations.values():
            hotkeys.close()
        self.registrations.clear()
