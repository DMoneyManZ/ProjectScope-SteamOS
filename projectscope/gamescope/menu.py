"""User-invoked controller menu; only this menu temporarily accepts focus."""
import subprocess
import sys
import gi
gi.require_version('Gtk','3.0');gi.require_version('GdkX11','3.0')
from gi.repository import Gtk,Gdk,GdkX11
from .control import command,quit_all
from .overlay import root_info
from ..settings import ROOT
from ..profiles import loads_profile

class QuickMenu:
    def __init__(self,cfg): self.cfg=cfg;self.window=None;self.buttons=[];self.index=0
    def close(self,*_):
        if self.window:
            window=self.window;self.window=None;window.destroy()
    def toggle(self):
        if self.window: self.close();return
        window=Gtk.Window(title='ProjectScope Quick Menu');self.window=window
        window.set_default_size(440,420);window.set_position(Gtk.WindowPosition.CENTER)
        from .identity import apply_window_identity
        apply_window_identity(window)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10,margin=20);window.add(box)
        label=Gtk.Label(label='ProjectScope');label.set_markup('<span size="xx-large" weight="bold">ProjectScope</span>')
        box.pack_start(label,False,False,0)
        self.caption=Gtk.Label(label=loads_profile(self.cfg.get_string('profile'))['name']);box.pack_start(self.caption,False,False,0)
        self.buttons=[]
        for title,callback in [('Show / hide crosshair',lambda:self.perform('toggle')),
            ('Previous preset',lambda:self.perform('previous')),('Next preset',lambda:self.perform('next')),
            ('Open full editor',self.editor),('Back to game',self.close),('Quit ProjectScope',quit_all)]:
            button=Gtk.Button(label=title);button.set_size_request(-1,42)
            button.connect('clicked',lambda _w,fn=callback:fn());box.pack_start(button,False,False,0)
            self.buttons.append(button)
        box.pack_start(Gtk.Label(label='D-pad: move   A: select   B: back\nHold L1 + R1 + Y to close'),False,False,0)
        window.connect('delete-event',lambda *_:(self.close(),True)[1])
        window.connect('key-press-event',lambda _w,e:(self.close(),True)[1] if e.keyval==Gdk.KEY_Escape else False)
        window.realize()
        display=window.get_display().get_name()
        if root_info(display)[0] is not None:
            # Interactive Gamescope overlay only while the user opens this menu.
            # Destroying the window releases focus back to the game.
            xid=str(window.get_window().get_xid())
            for prop in ('STEAM_OVERLAY','STEAM_INPUT_FOCUS'):
                subprocess.run(['xprop','-id',xid,'-f',prop,'32c','-set',prop,'1'],check=True,capture_output=True)
        window.show_all();window.present();self.index=0;self.buttons[0].grab_focus()
    def perform(self,action):
        try:
            command(self.cfg,action)
            visible='shown' if self.cfg.get_boolean('visible') else 'hidden'
            self.caption.set_text(loads_profile(self.cfg.get_string('profile'))['name']+' — '+visible)
        except ValueError as exc: self.caption.set_text(str(exc))
    def editor(self):
        subprocess.Popen([sys.executable,'-m','projectscope.gamescope','studio'],cwd=ROOT,start_new_session=True)
        self.close()
    def navigate(self,code,value):
        if self.window is None or not self.window.is_active(): return
        if code==305: self.close()
        elif code==304:
            focused=self.window.get_focus()
            if focused in self.buttons: focused.clicked()
        elif code in (16,17,544,545,546,547):
            focused=self.window.get_focus()
            if focused in self.buttons: self.index=self.buttons.index(focused)
            step=value if code in (16,17) else (-1 if code in (544,546) else 1)
            self.index=(self.index+step)%len(self.buttons);self.buttons[self.index].grab_focus()
