"""Controller-friendly startup choice; control mode is independent of session mode."""
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk
from .studio import CSS,column,text,button
from .controller import ControllerMonitor
from .control import quit_all
from ..settings import settings

class Welcome(Gtk.ApplicationWindow):
    def __init__(self,app):
        super().__init__(application=app,title='ProjectScope · Choose your controls',default_width=850,default_height=540)
        from .identity import apply_window_identity
        apply_window_identity(self)
        self.app=app;self.index=0;self.buttons=[]
        Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',True)
        provider=Gtk.CssProvider();provider.load_from_data(CSS+b'''
        .control-tile { padding: 22px; border-radius: 16px; background: #20282e; }
        .control-tile:hover { background: #283b38; }
        .control-tile:focus { background: #254039; }
        .choice-caption { font-size: 19px; font-weight: bold; }
        ''')
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root=column(16);root.set_border_width(28);self.add(root)
        root.pack_start(text('PROJECTSCOPE  /  PLAY YOUR WAY','status'),False,False,0)
        root.pack_start(text('Choose your controls','title'),False,False,0)
        root.pack_start(text('Use either option in Desktop Mode or Gaming Mode.','subtitle'),False,False,0)
        tiles=Gtk.Box(spacing=16,homogeneous=True);root.pack_start(tiles,True,True,0)
        for mode,title,shortcut,hint in [
            ('keyboard','Keyboard','Home · show / hide','Ctrl + Alt + Space · quick menu'),
            ('controller','Controller','L1 + R1 + Y · quick menu','D-pad / left stick + A · select')]:
            tile=Gtk.Button();tile.get_style_context().add_class('control-tile')
            content=column(10);tile.add(content)
            art=Gtk.DrawingArea();art.set_size_request(160,80)
            art.connect('draw',lambda w,cr,m=mode:self.draw_icon(w,cr,m));content.pack_start(art,True,True,0)
            content.pack_start(text(title,'choice-caption'),False,False,0)
            content.pack_start(text(shortcut,'status'),False,False,0)
            content.pack_start(text(hint,'subtitle'),False,False,0)
            tile.connect('clicked',lambda _w,m=mode:app.selected(m,self));tiles.pack_start(tile,True,True,0)
            self.buttons.append(tile)
        both=button('Start using both control options',lambda *_:app.selected('both',self))
        both.get_style_context().add_class('suggested-action');root.pack_start(both,False,False,0);self.buttons.append(both)
        bottom=Gtk.Box(spacing=12);root.pack_start(bottom,False,False,0)
        bottom.pack_start(text('You can change this later in Controls & settings.','subtitle'),True,True,0)
        quit_button=button('Quit',lambda *_:quit_all());bottom.pack_end(quit_button,False,False,0);self.buttons.append(quit_button)
        self.index={'keyboard':0,'controller':1,'both':2}[settings().get_string('control-mode')]
        self.connect('show',lambda *_:self.buttons[self.index].grab_focus())
        self.connect('key-press-event',self.key)
        self.controller=ControllerMonitor(lambda:None,self.navigate)
        self.connect('destroy',lambda *_:self.controller.close())

    def key(self,_w,event):
        if event.keyval in (Gdk.KEY_Left,Gdk.KEY_Right,Gdk.KEY_Up,Gdk.KEY_Down):
            self.move(-1 if event.keyval in (Gdk.KEY_Left,Gdk.KEY_Up) else 1);return True
        return False

    def move(self,step):
        focused=self.get_focus()
        if focused in self.buttons: self.index=self.buttons.index(focused)
        self.index=(self.index+step)%len(self.buttons);self.buttons[self.index].grab_focus()

    def navigate(self,code,value):
        if not self.is_active(): return
        if code==304:
            focused=self.get_focus()
            if focused in self.buttons: focused.clicked()
        elif code in (16,17): self.move(value)
        elif code in (544,546): self.move(-1)
        elif code in (545,547): self.move(1)

    @staticmethod
    def draw_icon(widget,cr,mode):
        cr.translate(widget.get_allocated_width()/2-80,0)
        cr.set_source_rgb(.57,.86,.75);cr.set_line_width(3)
        if mode=='keyboard':
            cr.rectangle(8,8,144,65);cr.stroke()
            for row in range(3):
                for col in range(9):
                    cr.rectangle(18+col*14,18+row*12,7,5);cr.fill()
            cr.rectangle(44,58,72,5);cr.fill()
        else:
            cr.move_to(35,12);cr.curve_to(8,12,3,67,20,72)
            cr.curve_to(32,76,43,55,52,54);cr.line_to(108,54)
            cr.curve_to(118,56,130,76,142,72);cr.curve_to(158,65,149,12,125,12)
            cr.close_path();cr.stroke()
            cr.move_to(35,25);cr.line_to(35,47);cr.move_to(24,36);cr.line_to(46,36);cr.stroke()
            for x,y in ((122,25),(133,36),(122,47),(111,36)):
                cr.arc(x,y,3,0,6.283);cr.fill()
            for x in (65,95): cr.arc(x,44,7,0,6.283);cr.stroke()
        return False
