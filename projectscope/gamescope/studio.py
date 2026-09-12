"""Compact SteamOS preset studio. Closing it leaves the overlay running."""
import copy
import subprocess
import sys
import tempfile
from pathlib import Path
import cairo
import gi
gi.require_version('Gtk','3.0')
gi.require_foreign('cairo')
from gi.repository import Gtk,Gdk,Gio,GLib
from ..settings import ROOT,settings
from ..profiles import load_profile,loads_profile,dumps_profile,save_profile,ProfileError
from ..storage import preset_catalog,save_named_profile
from ..render import draw
from .control import APP_ID,command,running,stop,remote_action,quit_all
from ..precision import DIMENSIONS,options,step_for,remember

CSS=b'''
window { background: #171b20; color: #edf0f2; }
.sidebar { background: #11151a; padding: 18px; }
.title { font-size: 26px; font-weight: bold; }
.subtitle { color: #aab5bf; }
.status { color: #93ddc0; }
button { min-height: 30px; }
button.suggested-action { background: #287862; color: white; }
button.step { min-height: 18px; padding: 1px 9px; border-radius: 12px; font-size: 11px; }
button.step:checked { background: #287862; color: white; }
button:focus { outline: 2px solid #93ddc0; outline-offset: -3px; }
'''

def text(value,style=None):
    widget=Gtk.Label(label=value,xalign=0)
    widget.set_line_wrap(True)
    if style: widget.get_style_context().add_class(style)
    return widget

def column(spacing=10): return Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=spacing)

def button(label,callback):
    widget=Gtk.Button(label=label);widget.connect('clicked',callback);return widget

class Studio(Gtk.ApplicationWindow):
    def __init__(self,app):
        super().__init__(application=app,title='ProjectScope · SteamOS',default_width=1050,default_height=700)
        from .identity import apply_window_identity
        apply_window_identity(self)
        self.cfg=settings();self.loading=False;self.fields={};self.process=None
        self.profile=loads_profile(self.cfg.get_string('profile'))
        self.user_dir=Path(GLib.get_user_data_dir())/'projectscope/presets'
        self.user_dir.mkdir(parents=True,exist_ok=True)
        Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',True)
        provider=Gtk.CssProvider();provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root=Gtk.Box(spacing=0);self.add(root)
        sidebar=column();sidebar.set_size_request(245,-1)
        sidebar.get_style_context().add_class('sidebar');root.pack_start(sidebar,False,False,0)
        sidebar.pack_start(text('ProjectScope','title'),False,False,0)
        sidebar.pack_start(text('Your crosshair. Your setup.','subtitle'),False,False,0)
        sidebar.pack_start(text('SteamOS preview','status'),False,False,0)
        self.presets=Gtk.ListBox();self.presets.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.presets.connect('row-activated',self.select)
        scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.presets);sidebar.pack_start(scroll,True,True,0)
        for title,callback in [('Import preset…',lambda *_:self.choose(False)),('Export preset…',lambda *_:self.choose(True))]:
            sidebar.pack_start(button(title,callback),False,False,0)
        hint=text('Close this window to keep the crosshair running.','subtitle')
        hint.set_max_width_chars(26);sidebar.pack_start(hint,False,False,0)
        main=column(12);main.set_border_width(18);root.pack_start(main,True,True,0)
        top=Gtk.Box(spacing=10);main.pack_start(top,False,False,0)
        top.pack_start(text('Crosshair studio','title'),True,True,0)
        self.visibility=Gtk.Switch(active=self.cfg.get_boolean('visible'))
        self.visibility.set_valign(Gtk.Align.CENTER)
        self.visibility.connect('notify::active',lambda w,_:command(self.cfg,'show' if w.get_active() else 'hide'))
        top.pack_end(self.visibility,False,False,0);top.pack_end(text('Show crosshair'),False,False,0)
        self.preview=Gtk.DrawingArea();self.preview.set_size_request(-1,165)
        self.preview.connect('draw',self.draw_preview);main.pack_start(self.preview,False,False,0)
        actions=Gtk.Box(spacing=8);main.pack_start(actions,False,False,0)
        self.start_button=button('Start overlay',self.start_overlay)
        self.start_button.get_style_context().add_class('suggested-action')
        actions.pack_start(self.start_button,True,True,0)
        actions.pack_start(button('Previous',lambda *_:self.perform('previous')),False,False,0)
        actions.pack_start(button('Next',lambda *_:self.perform('next')),False,False,0)
        actions.pack_start(button('Stop overlay',lambda *_:stop()),False,False,0)
        self.desktop=Gtk.CheckButton(label='Allow Desktop Mode preview')
        self.desktop.set_active(True)
        main.pack_start(self.desktop,False,False,0)
        self.message=text('Select Start overlay to begin.','status');main.pack_start(self.message,False,False,0)
        tabs=Gtk.Notebook();main.pack_start(tabs,True,True,0)
        form=Gtk.Grid(column_spacing=18,row_spacing=10,margin=12)
        scroller=Gtk.ScrolledWindow();scroller.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);scroller.add(form)
        tabs.append_page(scroller,Gtk.Label(label='Appearance'))
        self.row=0
        self.name=Gtk.Entry(text=self.profile['name']);self.name.set_max_length(80)
        self.name.connect('changed',self.rename);self.add_row(form,'Preset name',self.name)
        for key,label in [('color','Crosshair color'),('outline_color','Outline color')]:
            widget=Gtk.ColorButton();widget.connect('color-set',self.color,key);self.fields[key]=widget
            self.add_row(form,label,widget)
        for key,label,low,high,step in [('opacity','Opacity',0,1,.05),('scale','Size',.25,8,.25),
            ('outline_width','Outline',0,8,.5),('rotation','Rotation',-180,180,1),
            ('lines.length','Arm length',1,100,.5),('lines.thickness','Arm thickness',.5,20,.5),
            ('lines.gap','Center gap',0,100,.5),('dot.radius','Dot radius',.5,20,.5),
            ('circle.radius','Ring radius',1,100,.5),('circle.thickness','Ring thickness',.5,20,.5)]:
            widget=Gtk.SpinButton.new_with_range(low,high,step);widget.set_digits(2 if step<1 else 0)
            widget.connect('value-changed',lambda w,k=key:self.change(k,w.get_value()))
            self.fields[key]=widget
            self.add_row(form,label,self.precision(widget,key,step) if key in DIMENSIONS else widget)
        for key,label in [('lines.enabled','Cross lines'),('lines.top','Top arm'),('dot.enabled','Center dot'),('circle.enabled','Ring')]:
            widget=Gtk.Switch();widget.set_valign(Gtk.Align.CENTER)
            widget.connect('notify::active',lambda w,_,k=key:self.change(k,w.get_active()))
            self.fields[key]=widget;self.add_row(form,label,widget)
        position=column();position.set_border_width(14)
        position_scroll=Gtk.ScrolledWindow();position_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        position_scroll.add(position);tabs.append_page(position_scroll,Gtk.Label(label='Position & help'))
        position.pack_start(text('Position on the active display','title'),False,False,0)
        for key,label in [('offset-x','Horizontal offset'),('offset-y','Vertical offset')]:
            row=Gtk.Box(spacing=12);row.pack_start(text(label),True,True,0)
            spin=Gtk.SpinButton.new_with_range(-2000,2000,1);spin.set_value(self.cfg.get_int(key))
            spin.connect('value-changed',lambda w,k=key:self.cfg.set_int(k,w.get_value_as_int()))
            row.pack_end(spin,False,False,0);position.pack_start(row,False,False,0)
        position.pack_start(text('Gaming Mode: keep ProjectScope running, press Steam, then open your game. Return here to change presets or visibility. Touch and mouse controls are supported. Hold L1 + R1 + Y for 0.6 seconds to open the quick menu. On a keyboard use Ctrl + Alt + Space. Use D-pad, A and B there. The controller must expose all three buttons to Linux.','subtitle'),False,False,0)
        position.pack_start(text('This preview uses a transparent overlay. Background inversion and fading labels are not available. The performance HUD and real-game compatibility still need a Gaming Mode check.','subtitle'),False,False,0)
        footer=Gtk.Box(spacing=10);main.pack_start(footer,False,False,0)
        footer.pack_start(button('Reset preset',self.reset),False,False,0)
        footer.pack_start(button('Quick menu',self.open_menu),False,False,0)
        save=button('Save preset',self.save);save.get_style_context().add_class('suggested-action');footer.pack_end(save,False,False,0)
        controls=column(12);controls.set_border_width(18)
        controls_scroll=Gtk.ScrolledWindow();controls_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        controls_scroll.add(controls);tabs.append_page(controls_scroll,Gtk.Label(label='Controls & settings'))
        controls.pack_start(text('Your controls','title'),False,False,0)
        self.control_label=text('','status');controls.pack_start(self.control_label,False,False,0)
        controls.pack_start(button('Choose keyboard, controller or both',lambda *_:app.choose_controls()),False,False,0)
        controls.pack_start(text('Home · show / hide     Ctrl + Alt + Space · quick menu\nPage Up / Down · presets     Pause · random preset\nInsert · save preset     End · color\nShift + Page Up / Down · size     Ctrl + Page Up / Down · thickness\n\nController: L1 + R1 + Y · quick menu\nD-pad or left stick · move     A · select     B · back','subtitle'),False,False,0)
        controls.pack_end(button('Quit ProjectScope',lambda *_:quit_all()),False,False,0)
        self.control_label.set_text('Active: '+self.cfg.get_string('control-mode').title())
        self.reload();self.populate()
        self.signal=self.cfg.connect('changed',self.changed)
        self.watch=Gio.bus_watch_name(Gio.BusType.SESSION,APP_ID,Gio.BusNameWatcherFlags.NONE,
            lambda *_:self.backend(True),lambda *_:self.backend(False))
        self.connect('destroy',self.close)

    def precision(self,widget,key,default):
        group=column(3);group.pack_start(widget,False,False,0)
        row=Gtk.Box(spacing=3);row.set_halign(Gtk.Align.END)
        row.pack_start(text('Step','subtitle'),False,False,3)
        selected=step_for(self.cfg,key,default);widget.set_increments(selected,selected*10)
        first=None
        for amount in options(default):
            choice=Gtk.RadioButton.new_with_label_from_widget(first,f'{amount:g}')
            if first is None: first=choice
            choice.set_mode(False);choice.get_style_context().add_class('step')
            choice.set_active(amount==selected)
            def changed(w,value=amount):
                if w.get_active():
                    widget.set_increments(value,value*10);remember(self.cfg,key,value)
            choice.connect('toggled',changed);row.pack_start(choice,False,False,0)
        group.pack_start(row,False,False,0);return group

    def add_row(self,grid,label,widget):
        title=text(label);title.set_hexpand(True)
        grid.attach(title,0,self.row,1,1);grid.attach(widget,1,self.row,1,1);self.row+=1

    def backend(self,active):
        self.start_button.set_sensitive(not active)
        self.message.set_text('Overlay running. Edits apply immediately.' if active else 'Overlay stopped. Select Start overlay.')

    def draw_preview(self,widget,cr):
        width,height=widget.get_allocated_width(),widget.get_allocated_height()
        cr.set_source_rgb(.055,.071,.09);cr.paint()
        cr.set_source_rgb(.24,.28,.29);cr.rectangle(width/2,0,width/2,height);cr.fill()
        cr.set_source_rgba(.7,.8,.85,.10);cr.set_line_width(1)
        for x in range(0,width,24): cr.move_to(x,0);cr.line_to(x,height)
        for y in range(0,height,24): cr.move_to(0,y);cr.line_to(width,y)
        cr.stroke();draw(cr,self.profile['style'],width/2,height/2)

    def populate(self):
        self.loading=True;self.name.set_text(self.profile['name'])
        for key,widget in self.fields.items():
            value=self.profile['style']
            for part in key.split('.'): value=value[part]
            if isinstance(widget,Gtk.ColorButton):
                rgba=Gdk.RGBA();rgba.parse(value);widget.set_rgba(rgba)
            elif isinstance(widget,Gtk.Switch): widget.set_active(value)
            else: widget.set_value(value)
        self.loading=False;self.preview.queue_draw()

    def change(self,key,value):
        if self.loading: return
        candidate=copy.deepcopy(self.profile);target=candidate['style'];parts=key.split('.')
        for part in parts[:-1]: target=target[part]
        target[parts[-1]]=value
        self.apply(candidate)

    def color(self,widget,key):
        rgba=widget.get_rgba()
        self.change(key,'#'+''.join(f'{round(v*255):02X}' for v in (rgba.red,rgba.green,rgba.blue)))

    def rename(self,widget):
        if self.loading: return
        candidate=copy.deepcopy(self.profile);candidate['name']=widget.get_text().strip()
        self.apply(candidate)

    def apply(self,profile):
        try:
            command(self.cfg,'profile',dumps_profile(profile))
            self.profile=profile;self.preview.queue_draw();self.message.set_text('Applied: '+profile['name'])
        except (ValueError,GLib.Error) as exc: self.message.set_text(str(exc))

    def perform(self,action):
        try: command(self.cfg,action)
        except ValueError as exc: self.message.set_text(str(exc))

    def changed(self,_cfg,key):
        if key=='profile':
            try: candidate=loads_profile(self.cfg.get_string('profile'))
            except ProfileError as exc: self.message.set_text(str(exc));return
            if candidate!=self.profile:
                self.profile=candidate;self.populate()
                self.message.set_text('Selected: '+candidate['name'])
                for row in self.presets.get_children():
                    if row.profile_path.stem==candidate['id']: self.presets.select_row(row);break
        elif key=='control-mode': self.control_label.set_text('Active: '+self.cfg.get_string(key).title())
        elif key=='visible': self.visibility.set_active(self.cfg.get_boolean('visible'))

    def reload(self):
        for row in self.presets.get_children(): self.presets.remove(row)
        self.catalog=preset_catalog(ROOT/'presets',self.user_dir)
        self.cfg.set_strv('preset-library',[dumps_profile(p) for _,p in self.catalog])
        for path,profile in self.catalog:
            row=Gtk.ListBoxRow();row.profile_path=path
            label=text(profile['name']);label.set_margin_top(8);label.set_margin_bottom(8);row.add(label)
            self.presets.add(row)
            if profile['id']==self.profile['id']: self.presets.select_row(row)
        self.presets.show_all()

    def select(self,_list,row):
        try: self.apply(load_profile(row.profile_path));self.populate()
        except (OSError,ValueError) as exc: self.message.set_text(str(exc))

    def reset(self,*_):
        row=self.presets.get_selected_row()
        if row: self.select(self.presets,row)

    def save(self,*_):
        try:
            candidate=copy.deepcopy(self.profile);candidate['name']=self.name.get_text().strip()
            self.apply(save_named_profile(candidate,self.user_dir));self.reload();self.message.set_text('Preset saved.')
        except (OSError,ValueError) as exc: self.message.set_text(str(exc))

    def choose(self,export):
        dialog=Gtk.FileChooserDialog(title='Export preset' if export else 'Import preset',transient_for=self,
            action=Gtk.FileChooserAction.SAVE if export else Gtk.FileChooserAction.OPEN)
        dialog.add_buttons('Cancel',Gtk.ResponseType.CANCEL,'Save' if export else 'Open',Gtk.ResponseType.ACCEPT)
        flt=Gtk.FileFilter();flt.set_name('ProjectScope JSON presets');flt.add_pattern('*.json');dialog.add_filter(flt)
        if export: dialog.set_current_name(self.profile['id']+'.json');dialog.set_do_overwrite_confirmation(True)
        try:
            if dialog.run()==Gtk.ResponseType.ACCEPT:
                path=Path(dialog.get_filename())
                if export: save_profile(path,self.profile);self.message.set_text('Preset exported.')
                else: self.apply(load_profile(path));self.populate()
        except (OSError,ValueError) as exc: self.message.set_text(str(exc))
        finally: dialog.destroy()

    def open_menu(self,*_):
        if running(): remote_action('menu')
        else: self.message.set_text('Start the overlay first, then open the quick menu.')

    def start_overlay(self,*_):
        if running(): return
        args=[sys.executable,'-m','projectscope.gamescope','overlay']
        if self.desktop.get_active(): args.append('--desktop-preview')
        error=tempfile.TemporaryFile(mode='w+t')
        self.process=subprocess.Popen(args,cwd=ROOT,stdout=subprocess.DEVNULL,stderr=error,start_new_session=True)
        self.start_button.set_sensitive(False)
        def exited(_pid,status):
            if status:
                error.seek(0);self.message.set_text(error.read()[-1200:].strip() or 'Overlay stopped unexpectedly.')
            error.close();self.start_button.set_sensitive(True)
        GLib.child_watch_add(self.process.pid,exited)

    def close(self,*_):
        Gio.bus_unwatch_name(self.watch);self.cfg.disconnect(self.signal);Gio.Settings.sync()

class App(Gtk.Application):
    def __init__(self,welcome=False):
        super().__init__(application_id='io.projectscope.SteamOS',flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.welcome=welcome
    def do_startup(self):
        Gtk.Application.do_startup(self)
        action=Gio.SimpleAction.new('quit',None)
        action.connect('activate',lambda *_:(stop(),self.quit()))
        self.add_action(action)
    def choose_controls(self):
        from .welcome import Welcome
        window=next((w for w in self.get_windows() if isinstance(w,Welcome)),None)
        if window is None: window=Welcome(self)
        window.show_all();window.present()
    def selected(self,mode,window):
        cfg=settings();cfg.set_string('control-mode',mode);Gio.Settings.sync()
        studio=next((w for w in self.get_windows() if isinstance(w,Studio)),None)
        if studio is None: studio=Studio(self)
        studio.show_all();studio.present();window.destroy();studio.start_overlay()

    def do_command_line(self,line):
        self.welcome='launch' in line.get_arguments()[1:]
        if self.welcome: self.choose_controls()
        else:
            window=next((w for w in self.get_windows() if isinstance(w,Studio)),None)
            if window is None: window=Studio(self)
            window.show_all();window.present()
        return 0

    def do_activate(self):
        window=self.get_active_window()
        if window is None and self.welcome:
            self.choose_controls();return
        if window is None: window=Studio(self)
        window.show_all();window.present()

def run(welcome=False): return App(welcome).run([sys.argv[0],'launch' if welcome else 'studio'])
