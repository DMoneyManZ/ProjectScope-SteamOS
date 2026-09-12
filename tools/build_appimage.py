#!/usr/bin/env python3
"""Assemble a spec-shaped AppDir for the SteamOS preview and build an AppImage when appimagetool exists.

The AppDir reuses the installed layout (source under usr/lib, compiled schema beside it).
⚠ GTK 3, PyGObject, Pycairo and Python itself are host libraries: this AppDir does NOT bundle
them. A self-contained AppImage still needs linuxdeploy + linuxdeploy-plugin-gtk on a build host.
"""
import argparse
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
APP_ID = 'io.projectscope.SteamOS'
VERSION = '0.1.0-preview'
APPDIR_NAME = 'ProjectScope-SteamOS.AppDir'
LIB = 'usr/lib/projectscope-steamos'

PICK_PYTHON = '''# Prefer an interpreter that has PyGObject; a Homebrew/pyenv python3 first on PATH usually lacks it.
PY=""
for candidate in /usr/bin/python3 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import gi" >/dev/null 2>&1; then PY="$candidate"; break; fi
done
[ -n "$PY" ] || PY=python3
'''

APPRUN = '''#!/bin/sh
# AppImage entry point: run the bundled source with the host Python and GTK 3.
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:$PATH"
%s
exec "$PY" "$HERE/%s/launch_steamos.py" "$@"
''' % (PICK_PYTHON, LIB)

WRAPPER = '''#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
%s
exec "$PY" "$HERE/../lib/projectscope-steamos/launch_steamos.py" "$@"
''' % PICK_PYTHON

LAUNCH = ('import sys\nfrom pathlib import Path\n'
          'sys.path.insert(0,str(Path(__file__).resolve().parent))\n'
          'from projectscope.gamescope.__main__ import main\nsys.exit(main())\n')

DESKTOP = '\n'.join([
    '[Desktop Entry]', 'Type=Application', 'Version=1.0', 'Name=ProjectScope SteamOS',
    'Comment=Customize your crosshair for SteamOS', 'Exec=projectscope-steamos launch',
    'Icon=' + APP_ID, 'StartupWMClass=' + APP_ID, 'Terminal=false',
    'Categories=Game;Utility;', 'X-AppImage-Version=' + VERSION, 'Actions=Menu;Toggle;Stop;', '',
    '[Desktop Action Menu]', 'Name=Open quick menu', 'Exec=projectscope-steamos menu', '',
    '[Desktop Action Toggle]', 'Name=Show or hide crosshair', 'Exec=projectscope-steamos toggle', '',
    '[Desktop Action Stop]', 'Name=Stop overlay', 'Exec=projectscope-steamos stop', ''])


def _executable(path, text):
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_appdir(output):
    """Create output/<APPDIR_NAME> from the repository; returns the AppDir path."""
    appdir = output / APPDIR_NAME
    if appdir.exists(): shutil.rmtree(appdir)
    lib = appdir / LIB
    for name in ('projectscope', 'presets', 'assets', 'extension/schemas'):
        shutil.copytree(ROOT / name, lib / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.compiled'))
    shutil.copy2(ROOT / 'LICENSE', lib / 'LICENSE')
    subprocess.run(['glib-compile-schemas', '--strict', str(lib / 'extension/schemas')], check=True)
    lib.joinpath('launch_steamos.py').write_text(LAUNCH)
    _executable(appdir / 'AppRun', APPRUN)
    binary = appdir / 'usr/bin/projectscope-steamos'
    binary.parent.mkdir(parents=True)
    _executable(binary, WRAPPER)
    for target in (appdir / (APP_ID + '.desktop'), appdir / 'usr/share/applications' / (APP_ID + '.desktop')):
        target.parent.mkdir(parents=True, exist_ok=True); target.write_text(DESKTOP)
    png = ROOT / 'assets/projectscope.png'; svg = ROOT / 'assets/projectscope.svg'
    shutil.copy2(png, appdir / (APP_ID + '.png')); shutil.copy2(png, appdir / '.DirIcon')
    for directory, source in (('128x128', png), ('scalable', svg)):
        target = appdir / 'usr/share/icons/hicolor' / directory / 'apps' / (APP_ID + source.suffix)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    return appdir


def check_appdir(appdir):
    """Return a list of problems; empty means the AppDir is structurally ready for appimagetool."""
    problems = []
    required = ['AppRun', APP_ID + '.desktop', APP_ID + '.png', '.DirIcon', 'usr/bin/projectscope-steamos',
                'usr/share/applications/' + APP_ID + '.desktop',
                'usr/share/icons/hicolor/128x128/apps/' + APP_ID + '.png',
                LIB + '/launch_steamos.py', LIB + '/projectscope/gamescope/__main__.py',
                LIB + '/extension/schemas/gschemas.compiled', LIB + '/presets', LIB + '/LICENSE']
    for name in required:
        if not (appdir / name).exists(): problems.append('missing ' + name)
    for name in ('AppRun', 'usr/bin/projectscope-steamos'):
        path = appdir / name
        if path.exists() and not path.stat().st_mode & stat.S_IXUSR: problems.append(name + ' is not executable')
    desktop = appdir / (APP_ID + '.desktop')
    if desktop.exists():
        for line in desktop.read_text().splitlines():
            if line.startswith('Exec=') and line.split('=', 1)[1].startswith('/'):
                problems.append('absolute Exec path in desktop entry: ' + line)
        validator = shutil.which('desktop-file-validate')
        if validator:
            result = subprocess.run([validator, str(desktop)], capture_output=True, text=True)
            if result.returncode: problems.append('desktop-file-validate: ' + (result.stdout + result.stderr).strip())
    return problems


def main():
    parser = argparse.ArgumentParser(description='Build the ProjectScope SteamOS AppDir and, if possible, an AppImage')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/appimage')
    parser.add_argument('--check', action='store_true', help='Only validate an existing AppDir under --output')
    parser.add_argument('--require-tool', action='store_true', help='Fail when appimagetool is not installed')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    appdir = args.output / APPDIR_NAME if args.check else build_appdir(args.output)
    problems = check_appdir(appdir)
    for problem in problems: print('AppDir problem: ' + problem, file=sys.stderr)
    if problems: return 1
    print('AppDir ready: ' + str(appdir))
    tool = shutil.which('appimagetool')
    if not tool:
        print('⚠ appimagetool not found; AppDir built but no AppImage produced. '
              'Install appimagetool (or linuxdeploy + gtk plugin to bundle GTK) and rerun.', file=sys.stderr)
        return 1 if args.require_tool else 0
    if args.check: return 0
    image = args.output / ('ProjectScope-SteamOS-' + VERSION + '-x86_64.AppImage')
    subprocess.run([tool, str(appdir), str(image)], check=True, env={**os.environ, 'ARCH': 'x86_64'})
    print('Built ' + str(image))
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError, subprocess.CalledProcessError) as exc:
        print('AppImage build failed: ' + str(exc), file=sys.stderr); sys.exit(1)
