#!/usr/bin/env python3
"""Per-user installer. Only ProjectScope-owned paths are replaced/removed."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from desktop_entry import APP_ID, install_launchers, remove_icons, refresh_desktop_caches

UUID='projectscope@local'
ROOT=Path(__file__).resolve().parents[1]

def run(args):
    return subprocess.run(args,text=True,capture_output=True,check=False)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--uninstall',action='store_true'); args=parser.parse_args()
    home=Path.home(); data=Path(os.environ.get('XDG_DATA_HOME',home/'.local/share'))
    app=data/'projectscope/app'; ext=data/'gnome-shell/extensions'/UUID
    desktop_result=run(['xdg-user-dir','DESKTOP']) if shutil.which('xdg-user-dir') else None
    desktop=Path(desktop_result.stdout.strip()) if desktop_result and desktop_result.returncode==0 else home/'Desktop'
    launcher=data/'applications'/(APP_ID+'.desktop'); desktop_launcher=desktop/'ProjectScope.desktop'
    if args.uninstall:
        from size_shortcuts import configure
        configure(app, uninstall=True)
        run(['gnome-extensions','disable',UUID])
        for file in [launcher,desktop_launcher,data/'applications/projectscope.desktop']: file.unlink(missing_ok=True)
        remove_icons(data,APP_ID)
        for directory in [ext,app]:
            if directory.exists(): shutil.rmtree(directory)
        refresh_desktop_caches(data)
        print('Removed ProjectScope app and extension; personal presets/settings retained.'); return 0
    for command in ['glib-compile-schemas','gnome-extensions']:
        if not shutil.which(command): raise RuntimeError(f'Missing dependency: {command}')
    import gi
    gi.require_version('Gtk','4.0')
    import cairo
    version=run(['gnome-shell','--version']).stdout.strip()
    if not version.startswith('GNOME Shell 50.') and version!='GNOME Shell 50':
        raise RuntimeError(f'This release targets GNOME 50; found {version}')
    upgrading=ext.exists()
    if ROOT.resolve()!=app.resolve():
        app.mkdir(parents=True,exist_ok=True)
        for directory in ['projectscope','presets','extension','assets','tools','support','docs']:
            target=app/directory
            if target.exists(): shutil.rmtree(target)
            shutil.copytree(ROOT/directory,target,ignore=shutil.ignore_patterns('__pycache__','superpowers'))
        for name in ['README.md','VALIDATION.md','LICENSE','CONTRIBUTING.md']:
            if (ROOT/name).exists(): shutil.copy2(ROOT/name,app/name)
    if ext.exists(): shutil.rmtree(ext)
    shutil.copytree(app/'extension',ext)
    for schemas in [ext/'schemas',app/'extension/schemas']:
        result=run(['glib-compile-schemas','--strict',str(schemas)])
        if result.returncode: raise RuntimeError(result.stderr)
    launch=app/'launch.py'
    launch.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent))\nfrom projectscope.app import App\nsys.exit(App().run(sys.argv))\n')
    launcher,desktop_launcher=install_launchers(app,data,desktop,sys.executable)
    run(['gio','set',str(desktop_launcher),'metadata::trusted','true'])
    from gi.repository import Gio
    sys.path.insert(0,str(app))
    from projectscope.storage import preset_catalog
    from projectscope.profiles import dumps_profile
    from projectscope.settings import settings
    cfg=settings()
    cfg.set_strv('preset-library',[dumps_profile(p) for _,p in preset_catalog(app/'presets',data/'projectscope/presets')])
    shell=Gio.Settings.new('org.gnome.shell')
    enabled=shell.get_strv('enabled-extensions')
    if UUID not in enabled: shell.set_strv('enabled-extensions',enabled+[UUID])
    disabled=shell.get_strv('disabled-extensions')
    if UUID in disabled: shell.set_strv('disabled-extensions',[x for x in disabled if x!=UUID])
    Gio.Settings.sync()
    from size_shortcuts import configure
    configure(app)
    result=run(['gnome-extensions','enable',UUID])
    print(f'Installed app: {app}\nDesktop launcher: {desktop_launcher}')
    if upgrading: print('Updated extension code. Log out and back in once to load this update; normal use needs no logout.')
    elif result.returncode: print('Log out and back in once so GNOME discovers the new extension.')
    else: print('Extension enable requested. Open ProjectScope to check status.')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (OSError,RuntimeError,ImportError,ValueError) as exc:
        print(f'Install failed: {exc}',file=sys.stderr); sys.exit(1)
