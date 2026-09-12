"""ProjectScope native GTK4 editor. No polling or game-process access."""
import json
import io
import cairo
from pathlib import Path
import sys
import gi
gi.require_version('Gtk','4.0')
gi.require_version('Gdk','4.0')
gi.require_version('Graphene','1.0')
from gi.repository import Gtk, Gdk, Gio, GLib, Graphene
from .profiles import ProfileError, load_profile, loads_profile, dumps_profile, save_profile
from .modes import set_og, CONTROL_KEYS
from .shortcuts import ShortcutSettings, DEFAULTS, TITLES
from .storage import save_named_profile, preset_catalog
from .render import draw
from .settings import ROOT, settings, shell_call, status

CSS='''
window { background: #171b20; color: #edf0f2; }
.sidebar { background: #11151a; padding: 18px; }
.title { font-size: 27px; font-weight: 800; }
.subtitle { color: #aab5bf; }
.heading { font-size: 16px; font-weight: 700; margin-top: 10px; }
.preview { background: #0d1117; border-radius: 12px; }
.status { color: #93ddc0; font-size: 13px; }
.error { color: #ffb4a8; }
.preset { padding: 10px; border-radius: 7px; }
button.suggested-action { background: #287862; color: white; }
'''

def box(vertical=True,spacing=8):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,spacing=spacing)

def label(text,css=None):
    obj=Gtk.Label(label=text,xalign=0,wrap=True)
    if css: obj.add_css_class(css)
    return obj

class Preview(Gtk.Widget):
    """Cached Cairo image presented as a GTK texture, without gi-cairo bindings."""
    def __init__(self,style,backdrop=False):
        super().__init__()
        self.style=style; self.backdrop=backdrop; self.cache_key=None; self.texture=None
        self.set_size_request(100 if backdrop else 44,190 if backdrop else 44)
        self.set_hexpand(backdrop)

    def do_snapshot(self,snapshot):
        w,h=self.get_width(),self.get_height()
        if w<=0 or h<=0: return
        style=self.style()
        key=(w,h,json.dumps(style,sort_keys=True))
        if key!=self.cache_key:
            surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h); cr=cairo.Context(surface)
            if self.backdrop:
                cr.set_source_rgb(.055,.071,.09); cr.paint()
                cr.set_source_rgb(.24,.28,.29); cr.rectangle(w/2,0,w/2,h); cr.fill()
                cr.set_source_rgba(.7,.8,.85,.1); cr.set_line_width(1)
                for x in range(0,w,24): cr.move_to(x,0); cr.line_to(x,h)
                for y in range(0,h,24): cr.move_to(0,y); cr.line_to(w,y)
                cr.stroke()
            draw(cr,style,w/2,h/2)
            buffer=io.BytesIO(); surface.write_to_png(buffer)
            self.texture=Gdk.Texture.new_from_bytes(GLib.Bytes.new(buffer.getvalue()))
            self.cache_key=key
        snapshot.append_texture(self.texture,Graphene.Rect().init(0,0,w,h))

class Editor(Gtk.ApplicationWindow):
    def __init__(self,app):
        super().__init__(application=app,title='ProjectScope · Crosshair',default_width=1080,default_height=800)
        self.cfg=settings(); self.loading=False; self.controls={}; self.dialogs=[]
        try:
            info=shell_call('GetExtensionInfo')
            self.max_scale=4 if info and info.get('version',0)<5 else 8
        except GLib.Error:
            self.max_scale=8
        self.user_dir=Path(GLib.get_user_data_dir())/'projectscope/presets'
        self.user_dir.mkdir(parents=True,exist_ok=True)
        self.selected_path=None
        self.profile=load_profile(ROOT/'presets/cs2-precision.json')
        initial_error=None
        try: self.profile=loads_profile(self.cfg.get_string('profile'))
        except ProfileError as exc: initial_error=f'Saved settings invalid; preview uses CS2 preset. {exc}'
        Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',True)
        provider=Gtk.CssProvider(); provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(self.get_display(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        header=Gtk.HeaderBar(); self.set_titlebar(header)
        header.pack_end(self.button('Tutorial',self.tutorial))
        header.pack_end(self.button('Enable extension',self.enable))
        outer=box(False,0); self.set_child(outer)
        sidebar=box(); sidebar.set_size_request(240,-1); sidebar.add_css_class('sidebar'); outer.append(sidebar)
        sidebar.append(label('ProjectScope','title'))
        sidebar.append(label('Your crosshair. Your setup.','subtitle'))
        sidebar.append(label('Presets','heading'))
        self.list=Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.connect('row-activated',self.select_preset)
        scroll=Gtk.ScrolledWindow(vexpand=True); scroll.set_child(self.list); sidebar.append(scroll)
        sidebar.append(self.button('Randomize crosshair',self.randomize))
        sidebar.append(self.button('Import preset…',self.import_preset))
        sidebar.append(self.button('Export preset…',self.export_preset))
        sidebar.append(label('Home: show / hide.\nPage Up / Down: cycle saved presets.\nPause: random. Insert: save. End: color.\nClose this window to leave the overlay running.','subtitle'))
        main=box(spacing=12)
        for margin in ('top','bottom','start','end'): getattr(main,'set_margin_'+margin)(20)
        main.set_hexpand(True); outer.append(main)
        top=box(False); top.append(label('Crosshair studio','heading'))
        spacer=box(); spacer.set_hexpand(True); top.append(spacer)
        self.visible=Gtk.Switch(active=self.cfg.get_boolean('visible'),valign=Gtk.Align.CENTER)
        self.visible.connect('notify::active',self.toggle_visible)
        top.append(label('Show crosshair')); top.append(self.visible); main.append(top)
        self.preview=Preview(lambda:self.profile['style'],backdrop=True)
        self.preview.add_css_class('preview'); main.append(self.preview)
        self.message=label('','status'); main.append(self.message)
        self.backend=label(status(),'subtitle'); main.append(self.backend)
        tabs=Gtk.Notebook(vexpand=True); self.tabs=tabs; main.append(tabs)
        design=box(); design.set_margin_top(10); design.set_margin_end(12)
        ds=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER); ds.set_child(design)
        tabs.append_page(ds,Gtk.Label(label='Appearance'))
        self.entry=Gtk.Entry(text=self.profile['name'],hexpand=True,max_length=80)
        self.entry.connect('changed',self.name_changed)
        self.row(design,'Profile name',self.entry)
        for path,title in [('color','Crosshair color'),('outline_color','Outline color')]:
            color=Gtk.ColorButton(); color.set_use_alpha(False)
            color.connect('color-set',self.color_changed,path); self.controls[path]=color
            self.row(design,title,color)
        for path,title,lo,hi,step in [('opacity','Opacity',0,1,.05),('scale','Overall scale',.25,self.max_scale,.05),
            ('outline_width','Outline width',0,8,.5),('rotation','Rotation',-180,180,1)]:
            self.numeric(design,path,title,lo,hi,step)
        for group,title in [('lines','Cross lines'),('dot','Center dot'),('circle','Circle')]:
            design.append(label(title,'heading'))
            self.boolean(design,group+'.enabled','Enabled')
            if group=='lines':
                self.boolean(design,'lines.top','Show top arm')
                for key,text,lo,hi,step in [('length','Length',1,100,.5),('thickness','Thickness',.5,20,.5),('gap','Center gap',0,100,.5)]:
                    self.numeric(design,'lines.'+key,text,lo,hi,step)
            else:
                self.numeric(design,group+'.radius','Radius',.5 if group=='dot' else 1,20 if group=='dot' else 100,.5)
                if group=='circle': self.numeric(design,'circle.thickness','Thickness',.5,20,.5)
        session=box(); session.set_margin_top(12)
        self.syncing_shortcuts=False
        self.shortcuts=ShortcutSettings(self.cfg)
        self.shortcut_buttons={}
        controls=box(); controls.set_margin_top(12)
        controls_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        controls_scroll.set_child(controls)
        self.og_controls=Gtk.Switch(active=self.cfg.get_boolean('og-controls'),valign=Gtk.Align.CENTER)
        self.og_controls.connect('notify::active',lambda w,_:set_og(self.cfg,w.get_active()) if not self.syncing_shortcuts else None)
        self.row(controls,'OG controls',self.og_controls)
        controls.append(label('On: original Home-only controls, with labels and inversion off. Off: restore your updated controls. Your crosshair stays the same. Changes apply immediately; this is not a software downgrade.','subtitle'))

        session_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        session_scroll.set_child(session)
        tabs.append_page(session_scroll,Gtk.Label(label='Position'))
        tabs.append_page(controls_scroll,Gtk.Label(label='Settings'))
        session.append(label('Position is measured in desktop logical pixels. The primary display is used if a selected monitor is disconnected.','subtitle'))
        monitors=self.get_display().get_monitors()
        names=['Primary display']+[f'Monitor {i+1}' for i in range(monitors.get_n_items())]
        monitor=Gtk.DropDown.new_from_strings(names)
        monitor.set_selected(max(0,min(len(names)-1,self.cfg.get_int('monitor')+1)))
        monitor.connect('notify::selected',lambda w,_: self.cfg.set_int('monitor',w.get_selected()-1))
        self.row(session,'Display',monitor)
        for key,title in [('offset-x','Horizontal offset'),('offset-y','Vertical offset')]:
            spin=Gtk.SpinButton.new_with_range(-2000,2000,1); spin.set_value(self.cfg.get_int(key))
            spin.connect('value-changed',lambda w,k=key:self.cfg.set_int(k,w.get_value_as_int()))
            self.row(session,title,spin)
        controls.append(label('Keyboard shortcuts','heading'))
        controls.append(label('Click a shortcut, then press your new keys. Escape cancels; Backspace disables it. Changes apply immediately.','subtitle'))
        for key,title in TITLES.items():
            button=self.button('',lambda _w,k=key:self.capture_shortcut(k))
            self.shortcut_buttons[key]=button
            self.row(controls,title,button)
        controls.append(label('Size changes by 0.25× per press, from 0.25× to 8.0×. Save the preset to keep its size when cycling presets.','subtitle'))
        if self.max_scale<8:
            controls.append(label('This session supports up to 4×. After your next login, the updated overlay supports 8×.','subtitle'))
        controls.append(label('Thickness changes by 0.25 per press. For a dot, it changes the radius.','subtitle'))
        self.defaults_button=self.button('Restore default shortcuts',self.restore_shortcuts)
        controls.append(self.defaults_button)
        self.size_signals=[(cfg,cfg.connect('changed::binding',lambda *_:self.sync_shortcuts()))
                           for cfg in self.shortcuts.size.values()]
        session.append(label('Insert saves the current name (replaces your saved copy of that name). End alternates light/dark colors, keeps the shape, and switches off crosshair inversion so the color is visible.','subtitle'))

        self.display_options={}; self.option_signals=[]
        for key,title in [('show-label','Fading preset label'),('invert-label','Invert label against background'),('invert-crosshair','Invert crosshair against background')]:
            switch=Gtk.Switch(active=self.cfg.get_boolean(key),valign=Gtk.Align.CENTER)
            switch.connect('notify::active',lambda w,_,k=key:self.cfg.set_boolean(k,w.get_active()))
            self.display_options[key]=switch
            self.option_signals.append(self.cfg.connect('changed::'+key,lambda *_args,k=key,w=switch:
                w.set_active(self.cfg.get_boolean(k))))
            self.row(session,title,switch)
        session.append(label('Inversion uses desktop color blending, with no screen capture or player detection. In crosshair inversion mode your saved color and outline are replaced visually by an inverse silhouette. Disable label inversion for white text with a dark shadow.','subtitle'))

        session.append(label('Randomize makes a compact dot, cross or ring design and preserves your opacity. Save a result you like before generating another. No game content is analyzed.','subtitle'))

        session.append(label('Page Up selects the previous preset; Page Down selects the next, wrapping in sidebar order. Save edits before cycling to keep them. These keys are reserved globally while enabled.','subtitle'))

        session.append(label('Home is reserved while the extension is enabled. Change the shortcut here if another app needs Home. The shortcut is inactive on the lock screen.','subtitle'))
        session.append(label('The extension and visibility choice persist across login. No separate background editor or browser is needed.','subtitle'))
        session.append(self.button('Refresh extension status',lambda *_:self.backend.set_text(status())))
        session.append(self.button('Disable extension',self.disable))
        bottom=box(False)
        bottom.append(self.button('Reset to selected preset',self.reset))
        spacer=box(); spacer.set_hexpand(True); bottom.append(spacer)
        save=self.button('Save as preset',self.save_named); save.add_css_class('suggested-action'); bottom.append(save)
        main.append(bottom)
        self.reload_presets(); self.populate()
        self.shortcut_signal=self.cfg.connect('changed',self.sync_shortcuts)
        self.sync_shortcuts()

        self.library_signal=self.cfg.connect('changed::preset-library',lambda *_:self.reload_presets() if not self.loading else None)
        self.profile_signal=self.cfg.connect('changed::profile',self.sync_profile)
        self.visible_signal=self.cfg.connect('changed::visible',self.sync_visible)
        self.connect('close-request',self.on_close)
        self.message.set_text(initial_error or 'Edits apply immediately. Preview is at desktop logical scale.')

    def restore_shortcuts(self,*_):
        self.shortcuts.reset_defaults()
        Gio.Settings.sync()
        self.sync_shortcuts()
        self.message.set_text('Default shortcuts restored.')

    def apply_shortcut(self,key,binding):
        def normalized(value):
            ok,keyval,mods=Gtk.accelerator_parse(value)
            return Gtk.accelerator_name(keyval,mods) if ok else value
        if binding:
            for other,title in TITLES.items():
                if other!=key and normalized(self.shortcuts.get(other))==normalized(binding):
                    raise ValueError('That shortcut is already used for '+title.lower()+'.')
        self.shortcuts.set(key,binding)
        Gio.Settings.sync()
        self.sync_shortcuts()

    def capture_shortcut(self,key):
        dialog=Gtk.Window(title=TITLES[key],transient_for=self,modal=True,default_width=420)
        content=box(); content.set_margin_top(24);content.set_margin_bottom(24)
        content.set_margin_start(24);content.set_margin_end(24)
        content.append(label('Press the new shortcut','heading'))
        prompt=label('Escape cancels · Backspace disables','subtitle');content.append(prompt)
        dialog.set_child(content)
        controller=Gtk.EventControllerKey()
        def pressed(_controller,keyval,_keycode,state):
            if keyval==Gdk.KEY_Escape:
                dialog.close();return True
            if keyval in [Gdk.KEY_Shift_L,Gdk.KEY_Shift_R,Gdk.KEY_Control_L,Gdk.KEY_Control_R,
                          Gdk.KEY_Alt_L,Gdk.KEY_Alt_R,Gdk.KEY_Super_L,Gdk.KEY_Super_R]:
                return True
            mods=state & Gtk.accelerator_get_default_mod_mask()
            if keyval==Gdk.KEY_BackSpace and not mods:
                binding=''
            else:
                if not Gtk.accelerator_valid(keyval,mods):
                    prompt.set_text('Choose another key or add Ctrl, Alt, or Shift.');return True
                binding=Gtk.accelerator_name(keyval,mods)
            try: self.apply_shortcut(key,binding)
            except ValueError as exc:
                prompt.set_text(str(exc));return True
            dialog.close();return True
        controller.connect('key-pressed',pressed);dialog.add_controller(controller)
        dialog.connect('map',lambda w:w.get_surface().inhibit_system_shortcuts(None))
        dialog.connect('close-request',lambda w:(w.get_surface() and w.get_surface().restore_system_shortcuts(),False)[1])
        dialog.present()

    def sync_shortcuts(self,_cfg=None,key=None):
        if key is not None and key not in CONTROL_KEYS+('og-controls',): return
        self.syncing_shortcuts=True
        try:
            og=self.cfg.get_boolean('og-controls')
            self.og_controls.set_active(og)
            for key,button in self.shortcut_buttons.items():
                binding=self.shortcuts.get(key)
                ok,keyval,mods=Gtk.accelerator_parse(binding)
                button.set_label(Gtk.accelerator_get_label(keyval,mods) if ok and binding else 'Disabled')
                button.set_sensitive(not og or key=='toggle-key')
            self.defaults_button.set_sensitive(not og)
            for widget in self.display_options.values(): widget.set_sensitive(not og)
        finally: self.syncing_shortcuts=False

    def button(self,title,callback):
        widget=Gtk.Button(label=title); widget.connect('clicked',callback); return widget

    def row(self,parent,title,widget):
        row=box(False); text=label(title); text.set_hexpand(True)
        row.append(text); row.append(widget); parent.append(row)

    def value(self,path):
        result=self.profile['style']
        for key in path.split('.'): result=result[key]
        return result

    def set_value(self,path,value):
        result=self.profile['style']; parts=path.split('.')
        for key in parts[:-1]: result=result[key]
        result[parts[-1]]=value

    def numeric(self,parent,path,title,lo,hi,step):
        widget=Gtk.SpinButton.new_with_range(lo,hi,step); widget.set_digits(2 if step<1 else 0)
        widget.set_size_request(120,-1); self.controls[path]=widget
        widget.connect('value-changed',self.number_changed,path)
        from .precision import DIMENSIONS,options,step_for,remember
        if path not in DIMENSIONS:
            self.row(parent,title,widget);return
        field=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3);field.append(widget)
        steps=Gtk.Box(spacing=3,halign=Gtk.Align.END);steps.add_css_class('linked')
        selected=step_for(self.cfg,path,step);widget.set_increments(selected,selected*10)
        first=None
        for amount in options(step):
            choice=Gtk.ToggleButton(label=f'{amount:g}')
            if first is None: first=choice
            else: choice.set_group(first)
            choice.set_tooltip_text(f'Adjustment step: {amount:g}')
            choice.set_active(amount==selected)
            def changed(w,value=amount):
                if w.get_active():
                    widget.set_increments(value,value*10);remember(self.cfg,path,value)
            choice.connect('toggled',changed);steps.append(choice)
        field.append(steps);self.row(parent,title,field)

    def boolean(self,parent,path,title):
        widget=Gtk.Switch(valign=Gtk.Align.CENTER); self.controls[path]=widget
        widget.connect('notify::active',self.bool_changed,path); self.row(parent,title,widget)

    def populate(self):
        self.loading=True
        self.entry.set_text(self.profile['name'])
        for path,widget in self.controls.items():
            value=self.value(path)
            if isinstance(widget,Gtk.ColorButton):
                rgba=Gdk.RGBA(); rgba.parse(value); widget.set_rgba(rgba)
            elif isinstance(widget,Gtk.Switch): widget.set_active(value)
            else: widget.set_value(value)
        self.loading=False; self.preview.queue_draw()

    def number_changed(self,widget,path):
        if not self.loading: self.set_value(path,widget.get_value()); self.apply()

    def bool_changed(self,widget,_pspec,path):
        if not self.loading: self.set_value(path,widget.get_active()); self.apply()

    def color_changed(self,widget,path):
        rgba=widget.get_rgba()
        self.set_value(path,'#'+''.join(f'{round(v*255):02X}' for v in (rgba.red,rgba.green,rgba.blue)))
        self.apply()

    def name_changed(self,widget):
        if not self.loading:
            self.profile['name']=widget.get_text().strip(); self.apply()

    def apply(self):
        try:
            if self.profile['style']['scale']>self.max_scale:
                raise ProfileError('Sizes above 4× need the updated overlay after your next login.')
            content=dumps_profile(self.profile)
            if not self.cfg.set_string('profile',content): raise RuntimeError('Settings are not writable')
            self.preview.queue_draw(); self.message.remove_css_class('error')
            self.message.set_text('Applied · Home toggles the overlay when the extension is ready')
        except (ProfileError,RuntimeError) as exc: self.error(str(exc))

    def error(self,text):
        self.message.add_css_class('error'); self.message.set_text(text)

    def reload_presets(self):
        self.loading=True
        while self.list.get_first_child(): self.list.remove(self.list.get_first_child())
        self.selected_path=None
        catalog=preset_catalog(ROOT/'presets',self.user_dir)
        self.cfg.set_strv('preset-library',[dumps_profile(p) for _,p in catalog])
        for path,p in catalog:
            row=Gtk.ListBoxRow(); row.profile_path=path; row.profile_id=p['id']
            content=box(False); content.add_css_class('preset')
            thumb=Preview(lambda style=p['style']:style)
            content.append(thumb); text=box(spacing=2); text.append(label(p['name'])); text.append(label(p['game'],'subtitle'))
            content.append(text); row.set_child(content); self.list.append(row)
            if p['id']==self.profile['id']:
                self.list.select_row(row); self.selected_path=path
        self.loading=False

    def sync_profile(self,*_):
        try: candidate=loads_profile(self.cfg.get_string('profile'))
        except ProfileError as exc:
            self.error(str(exc)); return
        if candidate==self.profile: return
        self.profile=candidate; self.populate()
        self.selected_path=None; self.list.unselect_all()
        row=self.list.get_first_child()
        while row:
            if row.profile_id==candidate['id']:
                self.list.select_row(row); self.selected_path=row.profile_path; break
            row=row.get_next_sibling()
        self.message.remove_css_class('error')
        self.message.set_text('Selected · '+candidate['name'])

    def select_preset(self,_list,row):
        if self.loading or row is None: return
        try:
            self.profile=load_profile(row.profile_path); self.selected_path=row.profile_path; self.populate(); self.apply()
        except (OSError,ProfileError) as exc: self.error(str(exc))

    def randomize(self,*_):
        try:
            info=shell_call('GetExtensionInfo')
            state=info.get('state')
            if hasattr(state,'unpack'): state=state.unpack()
            version=info.get('version',0)
            if hasattr(version,'unpack'): version=version.unpack()
            if state!=1 or version<3:
                self.error('Enable the updated extension first. After installing this update, log out and back in once.')
                return
            self.cfg.set_uint('random-request',(self.cfg.get_uint('random-request')+1)%2**32)
        except GLib.Error as exc: self.error(exc.message)

    def reset(self,*_):
        if self.selected_path:
            try:
                self.profile=load_profile(self.selected_path); self.populate(); self.apply()
            except (OSError,ProfileError) as exc: self.error(str(exc))
        else:
            self.profile=load_profile(ROOT/'presets/cs2-precision.json'); self.populate(); self.apply()

    def save_named(self,*_):
        try:
            candidate=save_named_profile(self.profile,self.user_dir)
            self.profile=candidate; self.apply(); self.reload_presets()
            self.message.set_text('Preset saved. Saving the same name replaces your saved copy.')
        except (OSError,ProfileError) as exc: self.error(str(exc))

    def chooser(self,title,action,callback):
        chooser=Gtk.FileChooserNative.new(title,self,action,'Save' if action==Gtk.FileChooserAction.SAVE else 'Open','Cancel')
        flt=Gtk.FileFilter(); flt.set_name('ProjectScope JSON presets'); flt.add_pattern('*.json'); chooser.add_filter(flt)
        if action==Gtk.FileChooserAction.SAVE: chooser.set_current_name(self.profile['id']+'.json')
        def response(dialog,result):
            try:
                if result==Gtk.ResponseType.ACCEPT:
                    file=dialog.get_file(); path=file.get_path() if file else None
                    if not path: raise ProfileError('Choose a local file')
                    callback(Path(path))
            except (OSError,ProfileError) as exc: self.error(str(exc))
            finally: dialog.destroy(); self.dialogs.remove(dialog)
        chooser.connect('response',response); self.dialogs.append(chooser); chooser.show()

    def import_preset(self,*_):
        def selected(path):
            candidate=load_profile(path)  # Do not replace active state until validated.
            self.profile=candidate; self.selected_path=None; self.list.unselect_all(); self.populate(); self.apply()
            self.message.set_text('Imported and applied. Select Save as preset to keep it in your library.')
        self.chooser('Import preset',Gtk.FileChooserAction.OPEN,selected)

    def export_preset(self,*_):
        def selected(path):
            save_profile(path,self.profile); self.message.set_text('Preset exported')
        self.chooser('Export preset',Gtk.FileChooserAction.SAVE,selected)

    def toggle_visible(self,widget,_): self.cfg.set_boolean('visible',widget.get_active())
    def sync_visible(self,*_): self.visible.set_active(self.cfg.get_boolean('visible'))

    def enable(self,*_):
        try:
            result=shell_call('EnableExtension')
            self.backend.set_text(status() if result else 'Log out and back in once to activate the new extension')
        except GLib.Error as exc: self.error(exc.message)

    def disable(self,*_):
        try: shell_call('DisableExtension'); self.backend.set_text(status())
        except GLib.Error as exc: self.error(exc.message)

    def tutorial(self,*_):
        win=Gtk.Window(title='ProjectScope · Tutorial',transient_for=self,default_width=700,default_height=620)
        text=Gtk.TextView(editable=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,left_margin=20,right_margin=20,top_margin=20,bottom_margin=20)
        text.get_buffer().set_text((ROOT/'docs/USER-GUIDE.md').read_text())
        scroll=Gtk.ScrolledWindow(); scroll.set_child(text); win.set_child(scroll); win.present()

    def on_close(self,*_):
        self.cfg.disconnect(self.shortcut_signal)
        for cfg,signal in self.size_signals: cfg.disconnect(signal)
        for signal in self.option_signals: self.cfg.disconnect(signal)
        self.cfg.disconnect(self.library_signal); self.cfg.disconnect(self.profile_signal); self.cfg.disconnect(self.visible_signal); Gio.Settings.sync()
        return False

class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.projectscope.Crosshair',flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        Gtk.Window.set_default_icon_name(self.get_application_id())
    def do_activate(self):
        win=self.get_active_window()
        if not win: win=Editor(self)
        win.present()

if __name__=='__main__': sys.exit(App().run(sys.argv))
