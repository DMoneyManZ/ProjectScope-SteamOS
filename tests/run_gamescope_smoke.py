#!/usr/bin/env python3
"""Bounded, isolated headless Deck test runner. Does not switch user sessions."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
studio='--studio' in sys.argv
lifecycle='--lifecycle' in sys.argv
with tempfile.TemporaryDirectory(prefix='projectscope-synthetic-') as temporary:
    env=dict(os.environ,XDG_CONFIG_HOME=temporary+'/config',XDG_DATA_HOME=temporary+'/data',
             GSETTINGS_BACKEND='dconf',GDK_BACKEND='x11',GTK_THEME='Adwaita:dark')
    script=['python3','tests/steamos_studio_smoke.py'] if studio else ['python3','tests/gamescope_smoke.py','--capture']
    if lifecycle: script=['python3','tests/steamos_lifecycle_smoke.py']
    size=('1050','700') if studio or lifecycle else ('800','600')
    result=subprocess.run(['dbus-run-session','--','gamescope','--backend','headless',
        '-W',size[0],'-H',size[1],'-w',size[0],'-h',size[1],'--',*script],
        cwd=ROOT,env=env,capture_output=True,text=True,timeout=35)
    content=result.stdout+result.stderr
    expected='Studio editing, save and cycle: PASS' if studio else '"result": "PASS"'
    if lifecycle: expected='Startup, Both selection, complete Quit and welcome Quit: PASS'
    passed=expected in content and 'Traceback' not in content and result.returncode==0
    if passed:
        print('\n'.join(line for line in content.splitlines() if 'PASS' in line or line=='ProjectScope overlay ready'))
    else: print(content[-9000:])
    sys.exit(0 if passed else 1)
