#!/usr/bin/env python3
"""Exercise and capture only our editor inside a disposable graphics session."""
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from projectscope.gamescope.studio import App,Studio
from projectscope.profiles import loads_profile
from gi.repository import Gtk,Gdk
app=App();app.register(None)

def pump(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        time.sleep(.01)
from projectscope.gamescope.welcome import Welcome
from projectscope.gamescope.identity import APP_ID
from projectscope.precision import step_for
import subprocess
welcome=Welcome(app);welcome.show_all();welcome.present();pump(1)
subprocess.run(['xdotool','windowfocus',str(welcome.get_window().get_xid())],check=True);pump(.2)
assert welcome.get_allocated_width()<=850 and welcome.get_allocated_height()<=600,welcome.get_size()
image=Gdk.pixbuf_get_from_window(welcome.get_window(),0,0,welcome.get_allocated_width(),welcome.get_allocated_height())
output=ROOT/'build/steamos-welcome.png';output.parent.mkdir(exist_ok=True)
image.savev(str(output),'png',[],[])
welcome.buttons[0].grab_focus();welcome.navigate(16,1)
assert welcome.get_focus()==welcome.buttons[1]
# The selection handler persists the mode and opens the editor; skip starting
# a background overlay in this UI-only smoke, which is tested independently.
original_start=Studio.start_overlay;Studio.start_overlay=lambda *_:None
welcome.navigate(304,1);pump(.3)
Studio.start_overlay=original_start
window=next(w for w in app.get_windows() if isinstance(w,Studio))
assert window.cfg.get_string('control-mode')=='controller'
window.cfg.set_string('control-mode','both')
props=subprocess.check_output(['xprop','-id',str(window.get_window().get_xid()),'WM_CLASS','_NET_WM_ICON'],text=True)
assert APP_ID in props and 'Icon (128 x 128)' in props,props[:300]
pump(1)
assert window.get_allocated_width()<=1050 and window.get_allocated_height()<=700,window.get_size()
dot=window.fields['dot.radius'];before=dot.get_value()
# Pick the actual 0.1 UI bubble, not a mocked settings write.
field=dot.get_parent();choices=field.get_children()[1].get_children()
next(w for w in choices if isinstance(w,Gtk.RadioButton) and w.get_label()=='0.1').set_active(True)
assert dot.get_value()==before
assert step_for(window.cfg,'dot.radius',.5)==.1
dot.spin(Gtk.SpinType.STEP_FORWARD,0);pump(.1)
assert abs(window.profile['style']['dot']['radius']-(before+.1))<1e-6
window.fields['scale'].set_value(2)
pump(.2)
assert loads_profile(window.cfg.get_string('profile'))['style']['scale']==2
window.name.set_text('Synthetic studio preset');window.save()
pump(.2)
assert any(p['name']=='Synthetic studio preset' for _,p in window.catalog)
window.perform('next');pump(.2)
assert window.profile['name']!='Synthetic studio preset'
parent=dot
while not isinstance(parent,Gtk.ScrolledWindow): parent=parent.get_parent()
parent.get_vadjustment().set_value(180);pump(.2)
image=Gdk.pixbuf_get_from_window(window.get_window(),0,0,window.get_allocated_width(),window.get_allocated_height())
output=ROOT/'build/steamos-studio.png';output.parent.mkdir(exist_ok=True)
image.savev(str(output),'png',[],[])
window.destroy()
print('Studio editing, save and cycle: PASS',flush=True)
