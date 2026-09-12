"""Validated, GUI-independent control operations shared by the CLI and studio."""
from gi.repository import Gio
from ..profiles import loads_profile, dumps_profile, validate_profile, ProfileError

APP_ID='io.projectscope.GamescopeOverlay'

def cycle_profile(profiles, current_id, step):
    if not profiles:
        raise ValueError('No valid presets available. Open the studio to load your library.')
    ids=[p['id'] for p in profiles]
    if current_id not in ids:
        return validate_profile(profiles[0 if step>0 else -1])
    return validate_profile(profiles[(ids.index(current_id)+step)%len(profiles)])

def command(cfg, action, argument=None):
    if action in ('show','hide','toggle'):
        value=not cfg.get_boolean('visible') if action=='toggle' else action=='show'
        cfg.set_boolean('visible',value)
    elif action=='profile':
        cfg.set_string('profile',dumps_profile(loads_profile(argument)))
    elif action in ('next','previous'):
        profiles=[]
        for content in cfg.get_strv('preset-library'):
            try: profiles.append(loads_profile(content))
            except ProfileError: continue
        current=loads_profile(cfg.get_string('profile'))
        cfg.set_string('profile',dumps_profile(cycle_profile(
            profiles,current['id'],1 if action=='next' else -1)))
    elif action in ('random', 'color'):
        from .controls import random_profile, next_color
        current=loads_profile(cfg.get_string('profile'))
        updated=random_profile(current) if action=='random' else next_color(current)
        cfg.set_string('profile',dumps_profile(updated))
        if action=='color': cfg.set_boolean('invert-crosshair',False)
    elif action=='save':
        from .controls import save_current
        save_current(cfg)
    elif action in ('size-up','size-down','thicker','thinner'):
        from ..resize import resize, thicken
        operation=resize if action.startswith('size-') else thicken
        operation(cfg,1 if action in ('size-up','thicker') else -1)
    else:
        raise ValueError(f'Unknown command: {action}')
    Gio.Settings.sync()

def running():
    bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
    from gi.repository import GLib
    result=bus.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus',
        'org.freedesktop.DBus','NameHasOwner',GLib.Variant('(s)',(APP_ID,)),
        None,Gio.DBusCallFlags.NONE,1000,None)
    return result.unpack()[0]

def remote_action(action):
    if not running(): return
    connection=Gio.bus_get_sync(Gio.BusType.SESSION,None)
    actions=Gio.DBusActionGroup.get(connection,APP_ID,'/io/projectscope/GamescopeOverlay')
    actions.activate_action(action,None)
    connection.flush_sync(None)


def stop(): remote_action("stop")


def quit_all():
    """Ask the existing studio to quit, then stop the backend; never launch either."""
    from gi.repository import GLib
    application=Gio.Application.get_default()
    if application is not None and application.get_application_id()=='io.projectscope.SteamOS':
        try:
            stop()
        finally:
            application.quit()
        return
    try:
        connection=Gio.bus_get_sync(Gio.BusType.SESSION,None)
        # NO_AUTO_START makes quitting safe even when the studio is closed.
        connection.call_sync('io.projectscope.SteamOS','/io/projectscope/SteamOS',
            'org.gtk.Actions','Activate',
            GLib.Variant('(sava{sv})',('quit',[],{})),None,
            Gio.DBusCallFlags.NO_AUTO_START,1000,None)
    except GLib.Error:
        pass  # A closed studio must not prevent stopping the overlay.
    finally:
        stop()
