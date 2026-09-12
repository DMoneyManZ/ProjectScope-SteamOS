#!/usr/bin/env python3
"""Run only inside a disposable X11/Gamescope session; never on a real game.

Catches focus stealing, opaque overlay visuals, missing Gamescope classification,
and pointer interception. The synthetic scene contains no desktop information.
"""
import ctypes
import ctypes.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import gi
gi.require_version('Gtk','3.0')
gi.require_version('GdkX11','3.0')
from gi.repository import Gtk,Gdk,GdkX11,GLib,GdkPixbuf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
clicked=[]
window=Gtk.Window(title='ProjectScope synthetic game')
window.set_default_size(800,600)
area=Gtk.DrawingArea()
def draw(_widget,cr):
    cr.set_source_rgb(.12,.18,.25);cr.paint()
area.connect('draw',draw)
area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
area.connect('button-press-event',lambda *_:clicked.append(True))
window.add(area);window.show_all();window.present()
def pump(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        time.sleep(.01)
pump(1)
game_id=window.get_window().get_xid()
# Explicit focus is restricted to our disposable synthetic game.
subprocess.run(['xdotool','windowfocus',str(game_id)],check=True)
args=[sys.executable,'-m','projectscope.gamescope','overlay']
if '--desktop-preview' in sys.argv: args.append('--desktop-preview')
process=subprocess.Popen(args,cwd=ROOT)
try:
    pump(2)
    if process.poll() is not None: raise AssertionError('overlay exited before test')
    ids=subprocess.check_output(['xdotool','search','--name','^ProjectScope Overlay$'],text=True).split()
    assert len(ids)==1,ids
    xid=int(ids[0])
    properties=subprocess.check_output(['xprop','-id',str(xid),'GAMESCOPE_EXTERNAL_OVERLAY','WM_HINTS'],text=True)
    assert 'GAMESCOPE_EXTERNAL_OVERLAY(CARDINAL) = 1' in properties,properties
    assert 'Client accepts input or input focus: False' in properties,properties
    geometry=subprocess.check_output(['xwininfo','-id',str(xid)],text=True)
    assert 'Depth: 32' in geometry,geometry
    focus=int(subprocess.check_output(['xdotool','getwindowfocus'],text=True))
    assert focus==game_id,(focus,game_id)
    x11=ctypes.CDLL(ctypes.util.find_library('X11'))
    xext=ctypes.CDLL(ctypes.util.find_library('Xext'))
    x11.XOpenDisplay.argtypes=[ctypes.c_char_p];x11.XOpenDisplay.restype=ctypes.c_void_p
    x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
    x11.XFree.argtypes=[ctypes.c_void_p]
    xext.XShapeGetRectangles.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int)]
    xext.XShapeGetRectangles.restype=ctypes.c_void_p
    display=x11.XOpenDisplay(None)
    count=ctypes.c_int(-1);order=ctypes.c_int()
    rectangles=xext.XShapeGetRectangles(display,xid,2,ctypes.byref(count),ctypes.byref(order))
    try: assert count.value==0,count.value
    finally:
        if rectangles: x11.XFree(rectangles)
        x11.XCloseDisplay(display)
    subprocess.run(['xdotool','mousemove','--window',str(game_id),'400','300','click','1'],check=True)
    pump(.4)
    assert clicked,'synthetic game did not receive click through overlay'
    # This request targets ONLY the isolated synthetic compositor. Never run
    # this harness inside the user's normal Gaming Mode session.
    if '--capture' in sys.argv:
        capture=Path('/tmp/gamescope.png')
        assert not capture.exists(),'Existing Gamescope capture: refusing to overwrite'
        subprocess.run(['xprop','-root','-f','GAMESCOPECTRL_REQUEST_SCREENSHOT','32c',
                        '-set','GAMESCOPECTRL_REQUEST_SCREENSHOT','2'],check=True)
        pump(2)
        assert capture.exists(),'Gamescope did not produce a composited frame'
        pix=GdkPixbuf.Pixbuf.new_from_file(str(capture))
        out=ROOT/'build/synthetic-overlay.png';out.parent.mkdir(exist_ok=True)
        out.write_bytes(capture.read_bytes());capture.unlink()
        data=pix.get_pixels();stride=pix.get_rowstride();channels=pix.get_n_channels()
        def pixel(x,y): return tuple(data[y*stride+x*channels:y*stride+x*channels+3])
        assert all(abs(a-b)<=3 for a,b in zip(pixel(100,100),(31,46,64))),pixel(100,100)
        assert pixel(407,299)[1]>220 and pixel(407,299)[2]>220,pixel(407,299)
        from projectscope.gamescope.control import running,command,stop,remote_action
        from projectscope.settings import settings
        assert running(),'Overlay did not register its control service'
        command(settings(),'hide');pump(.5)
        subprocess.run(['xprop','-root','-f','GAMESCOPECTRL_REQUEST_SCREENSHOT','32c',
                        '-set','GAMESCOPECTRL_REQUEST_SCREENSHOT','2'],check=True)
        pump(2)
        hidden=GdkPixbuf.Pixbuf.new_from_file(str(capture));capture.unlink()
        hidden_data=hidden.get_pixels();i=299*hidden.get_rowstride()+407*hidden.get_n_channels()
        assert all(abs(a-b)<=3 for a,b in zip(hidden_data[i:i+3],(31,46,64))),tuple(hidden_data[i:i+3])
        command(settings(),'show');pump(.3)
        print('Composited pixels and live visibility: PASS',flush=True)
        subprocess.run(['xdotool','key','ctrl+alt+space'],check=True);pump(.8)
        menu_ids=subprocess.check_output(['xdotool','search','--name','^ProjectScope Quick Menu$'],text=True).split()
        assert len(menu_ids)==1,menu_ids
        menu_id=int(menu_ids[0])
        assert int(subprocess.check_output(['xdotool','getwindowfocus'],text=True))==menu_id,'Menu did not receive focus'
        pump(.2)
        subprocess.run(['xdotool','key','ctrl+alt+space'],check=True);pump(.5)
        assert int(subprocess.check_output(['xdotool','getwindowfocus'],text=True))==game_id,'Closing menu did not return game focus'
        print('Ctrl+Alt+Space menu focus and return to game: PASS',flush=True)
        cfg=settings()
        def key(value):
            subprocess.run(['xdotool','key',value],check=True);pump(.15)
        key('Home');assert not cfg.get_boolean('visible')
        key('Home');assert cfg.get_boolean('visible')
        from projectscope.profiles import loads_profile,dumps_profile,load_profile
        cfg.set_strv('preset-library',[dumps_profile(load_profile(ROOT/'presets/cs2-precision.json')),
                                       dumps_profile(load_profile(ROOT/'presets/fps-ring.json'))]);pump(.2)
        key('Next');assert loads_profile(cfg.get_string('profile'))['id']=='fps-ring'
        key('Prior');assert loads_profile(cfg.get_string('profile'))['id']=='cs2-precision'
        before=loads_profile(cfg.get_string('profile'))
        key('shift+Prior');assert loads_profile(cfg.get_string('profile'))['style']['scale']==before['style']['scale']+.25
        key('ctrl+Next');assert loads_profile(cfg.get_string('profile'))['style']['lines']['thickness']==before['style']['lines']['thickness']-.25
        key('End');assert loads_profile(cfg.get_string('profile'))['style']['color']!=before['style']['color']
        key('Pause');assert loads_profile(cfg.get_string('profile'))['id']!=before['id']
        key('Insert');assert list((Path(os.environ['XDG_DATA_HOME'])/'projectscope/presets').glob('*.json'))
        cfg.set_string('control-mode','controller');pump(.3)
        key('Home');assert cfg.get_boolean('visible'),'Controller-only must leave Home to game'
        cfg.set_string('control-mode','both');pump(.3)
        key('Home');assert not cfg.get_boolean('visible')
        print('Keyboard controls, save and live input-mode selection: PASS',flush=True)
        # Full Quit from the actual quick-menu button, with no editor open.
        key('ctrl+alt+space');pump(.5)
        quit_menu=subprocess.check_output(['xdotool','search','--name','^ProjectScope Quick Menu$'],text=True).split()[0]
        for _ in range(5): key('Tab')
        key('Return');pump(.4)
        assert process.poll()==0,'Stop command did not cleanly terminate overlay'
    print(json.dumps({'result':'PASS','rgba_depth':32,'empty_input_region':True,
                      'focus_retained':True,'click_through':True,'external_overlay':True}),flush=True)
    # Allow the outer harness to capture ONLY this synthetic Gamescope window.
    if '--hold' in sys.argv: pump(8)
finally:
    process.terminate()
    try: process.wait(timeout=5)
    except subprocess.TimeoutExpired: process.kill();process.wait()
    window.destroy()
