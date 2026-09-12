"""Non-interactive RGBA window classified as a Gamescope external overlay."""
import os
import re
import signal
import time
import subprocess
from pathlib import Path


def root_info(display):
    result=subprocess.run(['xprop','-display',display,'-root','GAMESCOPE_PID',
                           'GAMESCOPE_XWAYLAND_SERVER_ID'],capture_output=True,text=True,timeout=2)
    def number(name):
        match=re.search(r'^'+name+r'\(CARDINAL\) = (\d+)',result.stdout,re.M)
        return int(match[1]) if match else None
    return number('GAMESCOPE_PID'),number('GAMESCOPE_XWAYLAND_SERVER_ID')


def select_display(desktop_preview=False):
    current=os.environ.get('DISPLAY','')
    if not current: raise RuntimeError('No X11 display. Launch from Steam or Desktop Mode.')
    pid,server=root_info(current)
    if pid is None:
        if desktop_preview: return current
        raise RuntimeError('Gamescope is not running on this display. Use --desktop-preview in KDE Desktop Mode.')
    if server in (0,None): return current
    # Gamescope uses separate Xwayland servers for games. Render on its primary
    # server, matching the compositor PID so another nested session is not chosen.
    for socket in sorted(Path('/tmp/.X11-unix').glob('X[0-9]*')):
        candidate=':'+socket.name[1:]
        try: other_pid,other_server=root_info(candidate)
        except subprocess.TimeoutExpired: continue
        if other_pid==pid and other_server==0: return candidate
    raise RuntimeError('Cannot reach this Gamescope session’s primary X11 display.')


def run(desktop_preview=False):
    os.environ['DISPLAY']=select_display(desktop_preview)
    os.environ['GDK_BACKEND']='x11'
    import cairo
    import gi
    gi.require_version('Gtk','3.0');gi.require_version('GdkX11','3.0')
    gi.require_foreign('cairo')
    from gi.repository import Gtk,Gdk,GdkX11,Gio,GLib
    from ..settings import settings
    from ..profiles import loads_profile,ProfileError
    from ..render import draw
    from .control import APP_ID

    initialized,_=Gtk.init_check([])
    if not initialized: raise RuntimeError('Cannot open the selected X11 display.')
    app=Gio.Application(application_id=APP_ID,flags=Gio.ApplicationFlags.FLAGS_NONE)
    app.register(None)
    if app.get_is_remote():
        print('ProjectScope overlay is already running.');return 0
    Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',True)
    cfg=settings()
    profile=loads_profile(cfg.get_string('profile'))
    window=Gtk.Window(title='ProjectScope Overlay')
    from .identity import apply_window_identity
    apply_window_identity(window)
    window.set_decorated(False);window.set_resizable(False)
    window.set_accept_focus(False);window.set_focus_on_map(False)
    window.set_skip_taskbar_hint(True);window.set_skip_pager_hint(True)
    window.set_keep_above(True);window.set_app_paintable(True)
    window.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
    screen=window.get_screen()
    visual=screen.get_rgba_visual()
    if visual is None: raise RuntimeError('This X11 display has no transparent RGBA visual.')
    window.set_visual(visual)

    def geometry(*_):
        monitor=cfg.get_int('monitor')
        display=window.get_display()
        target=display.get_monitor(monitor) if 0<=monitor<display.get_n_monitors() else display.get_primary_monitor()
        if target is None: target=display.get_monitor(0)
        rect=target.get_geometry()
        window.move(rect.x,rect.y);window.resize(rect.width,rect.height)
        window.set_default_size(rect.width,rect.height)
        if window.get_realized():
            window.get_window().input_shape_combine_region(cairo.Region(),0,0)
        window.queue_draw()

    def paint(_widget,cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0,0,0,0);cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        if cfg.get_boolean('visible'):
            draw(cr,profile['style'],window.get_allocated_width()/2+cfg.get_int('offset-x'),
                 window.get_allocated_height()/2+cfg.get_int('offset-y'))
        return True

    def changed(_cfg,key):
        nonlocal profile
        if key=='profile':
            try: profile=loads_profile(cfg.get_string('profile'))
            except ProfileError: return  # Preserve last valid rendering.
        if key=='monitor': geometry()
        if key in ('profile','visible','offset-x','offset-y'): window.queue_draw()

    window.connect('draw',paint)
    window.connect('configure-event',lambda *_:window.get_window().input_shape_combine_region(cairo.Region(),0,0))
    geometry();window.realize()
    native=window.get_window()
    native.input_shape_combine_region(cairo.Region(),0,0)
    # Establish classification BEFORE mapping. Gamescope excludes this window
    # from game focus candidates and composites its alpha above the game.
    result=subprocess.run(['xprop','-id',str(native.get_xid()),'-f','GAMESCOPE_EXTERNAL_OVERLAY',
                           '32c','-set','GAMESCOPE_EXTERNAL_OVERLAY','1'],capture_output=True,text=True)
    if result.returncode: raise RuntimeError('Cannot mark the Gamescope overlay: '+result.stderr.strip())
    cfg.connect('changed',changed)
    from .menu import QuickMenu
    from .controller import ControllerMonitor
    menu=QuickMenu(cfg)
    last_shortcut=0.0
    def shortcut():
        nonlocal last_shortcut
        now=time.monotonic()
        if now-last_shortcut>=.85:
            last_shortcut=now;menu.toggle()
    controllers=None
    from .hotkey import HotkeyManager
    from .control import command
    def keyboard_action(action):
        if action=='menu': shortcut()
        else:
            try: command(cfg,action)
            except (ValueError,OSError) as exc: print('Shortcut: '+str(exc),flush=True)
    hotkey=HotkeyManager(keyboard_action,os.environ['DISPLAY'],
                         keyboard_enabled=cfg.get_string('control-mode')!='controller')
    def controls_changed(*_):
        nonlocal controllers
        enabled=cfg.get_string('control-mode')!='keyboard'
        if enabled and controllers is None: controllers=ControllerMonitor(shortcut,menu.navigate)
        elif not enabled and controllers is not None: controllers.close();controllers=None
        hotkey.set_keyboard_enabled(cfg.get_string('control-mode')!='controller')
    controls_changed();cfg.connect('changed::control-mode',controls_changed)
    screen.connect('size-changed',geometry)
    def quit_overlay(*_):
        if Gtk.main_level(): Gtk.main_quit()
    action=Gio.SimpleAction.new('stop',None);action.connect('activate',quit_overlay);app.add_action(action)
    window.connect('destroy',quit_overlay)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGTERM,lambda:(quit_overlay(),False)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGINT,lambda:(quit_overlay(),False)[1])
    menu_action=Gio.SimpleAction.new('menu',None)
    menu_action.connect('activate',lambda *_:menu.toggle());app.add_action(menu_action)
    window.show_all()
    print('ProjectScope overlay ready',flush=True)
    Gtk.main()
    if controllers is not None: controllers.close()
    if hotkey is not None: hotkey.close()
    menu.close()
    window.destroy()
    return 0
