"""Full startup/selection/quit against an isolated bus and synthetic compositor."""
from pathlib import Path
import os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from projectscope.gamescope.control import running,quit_all
from projectscope.settings import settings
process=subprocess.Popen([sys.executable,'-m','projectscope.gamescope','launch'],cwd=ROOT)
def wait_for(fn):
    end=time.monotonic()+8
    while time.monotonic()<end:
        if fn(): return
        time.sleep(.1)
    raise AssertionError('Lifecycle condition timed out')
try:
    def welcome():
        result=subprocess.run(['xdotool','search','--name','^ProjectScope · Choose your controls$'],capture_output=True,text=True)
        return result.stdout.strip()
    wait_for(welcome)
    subprocess.run(['xdotool','windowfocus',welcome().splitlines()[0]],check=True)
    # Default Both has focus; select it exactly as a keyboard/controller Enter action.
    subprocess.run(['xdotool','key','Return'],check=True)
    wait_for(running)
    assert settings().get_string('control-mode')=='both'
    # A second launcher invocation must show choices in the existing process.
    subprocess.run([sys.executable,'-m','projectscope.gamescope','launch'],cwd=ROOT,check=True,timeout=5)
    wait_for(welcome)
    subprocess.run([sys.executable,'-m','projectscope.gamescope','studio'],cwd=ROOT,check=True,timeout=5)
    quit_all();process.wait(timeout=5);wait_for(lambda:not running())
    assert process.returncode==0
    # Relaunch, then Quit on the welcome screen; no overlay should start.
    process=subprocess.Popen([sys.executable,'-m','projectscope.gamescope','launch'],cwd=ROOT)
    wait_for(welcome)
    subprocess.run(['xdotool','windowfocus',welcome().splitlines()[0],'key','Tab','Return'],check=True)
    process.wait(timeout=5);assert process.returncode==0 and not running()
    print('Startup, Both selection, complete Quit and welcome Quit: PASS',flush=True)
finally:
    quit_all()
    if process.poll() is None: process.terminate();process.wait(timeout=5)
