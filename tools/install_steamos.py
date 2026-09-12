#!/usr/bin/env python3
"""Install the SteamOS preview below the current user's home, without sudo."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from desktop_entry import quoted, install_icons, remove_icons, refresh_desktop_caches

ROOT=Path(__file__).resolve().parents[1]
APP_ID='io.projectscope.SteamOS'


def check_dependencies():
    missing=[name for name in ('xprop','glib-compile-schemas') if not shutil.which(name)]
    try:
        import gi
        gi.require_version('Gtk','3.0');gi.require_version('GdkX11','3.0')
        gi.require_foreign('cairo')
        from gi.repository import Gtk,GdkX11
        import cairo
    except (ImportError,ValueError) as exc: missing.append(str(exc))
    if missing:
        raise RuntimeError('Missing dependencies: '+', '.join(missing)+'. See docs/STEAMOS.md. Do not unlock SteamOS to install this preview.')


def main():
    parser=argparse.ArgumentParser(description='Install ProjectScope SteamOS preview for this user')
    parser.add_argument('--uninstall',action='store_true')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.check: check_dependencies();print('SteamOS preview dependencies available.');return 0
    if os.geteuid()==0: raise RuntimeError('Run as your normal desktop user, without sudo.')
    home=Path.home();data=Path(os.environ.get('XDG_DATA_HOME',home/'.local/share'))
    app=data/'projectscope-steamos/app';cli=home/'.local/bin/projectscope-steamos'
    launcher=data/'applications'/(APP_ID+'.desktop')
    desktop=home/'Desktop/ProjectScope SteamOS.desktop'
    if args.uninstall:
        for path in (cli,launcher,desktop): path.unlink(missing_ok=True)
        remove_icons(data,APP_ID)
        if app.exists(): shutil.rmtree(app)
        refresh_desktop_caches(data)
        print('Removed SteamOS preview. Personal presets and settings retained.');return 0
    check_dependencies()
    app.mkdir(parents=True,exist_ok=True)
    if ROOT.resolve()!=app.resolve():
        for name in ('projectscope','presets','assets','extension/schemas'):
            target=app/name
            if target.exists(): shutil.rmtree(target)
            shutil.copytree(ROOT/name,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (app/'tools').mkdir(exist_ok=True)
        for name in ('install_steamos.py','desktop_entry.py'):
            shutil.copy2(ROOT/'tools'/name,app/'tools'/name)
        shutil.copy2(ROOT/'LICENSE',app/'LICENSE')
        (app/'docs').mkdir(exist_ok=True)
        if (ROOT/'docs/STEAMOS.md').exists(): shutil.copy2(ROOT/'docs/STEAMOS.md',app/'docs/STEAMOS.md')
    subprocess.run(['glib-compile-schemas','--strict',str(app/'extension/schemas')],check=True)
    launch=app/'launch_steamos.py'
    launch.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent))\nfrom projectscope.gamescope.__main__ import main\nsys.exit(main())\n')
    cli.parent.mkdir(parents=True,exist_ok=True)
    cli.write_text('#!/bin/sh\nexec '+shlex.join([sys.executable,str(launch)])+' "$@"\n');cli.chmod(0o755)
    install_icons(app,data,APP_ID)
    body='\n'.join(['[Desktop Entry]','Type=Application','Name=ProjectScope SteamOS',
        'Comment=Customize your crosshair for SteamOS',f'Exec={quoted(cli)} launch',
        'Icon='+APP_ID,'StartupWMClass='+APP_ID,'Terminal=false','Categories=Game;Utility;',
        'Actions=Menu;Toggle;Stop;','',
        '[Desktop Action Menu]','Name=Open quick menu',f'Exec={quoted(cli)} menu','',
        '[Desktop Action Toggle]','Name=Show or hide crosshair',f'Exec={quoted(cli)} toggle','',
        '[Desktop Action Stop]','Name=Stop overlay',f'Exec={quoted(cli)} stop',''])
    launcher.parent.mkdir(parents=True,exist_ok=True);launcher.write_text(body)
    desktop.parent.mkdir(parents=True,exist_ok=True);desktop.write_text(body);desktop.chmod(0o755)
    refresh_desktop_caches(data)
    print(f'Installed ProjectScope SteamOS.\nLaunch: {cli}\nDesktop shortcut: {desktop}')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (OSError,RuntimeError,subprocess.CalledProcessError) as exc:
        print('Install failed: '+str(exc),file=sys.stderr);sys.exit(1)
