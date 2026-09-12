"""ProjectScope SteamOS commands; the normal GNOME entry point is unchanged."""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description='ProjectScope SteamOS preview')
    parser.add_argument('command',nargs='?',default='launch',choices=[
        'launch','studio','overlay','menu','status','stop','toggle','show','hide','next','previous','profile'])
    parser.add_argument('file',nargs='?',type=Path,help='JSON preset for the profile command')
    parser.add_argument('--desktop-preview',action='store_true',help='Allow the X11 desktop overlay outside Gamescope')
    args=parser.parse_args()
    try:
        if args.command=='overlay':
            from .overlay import run
            return run(args.desktop_preview)
        if args.command in ('studio','launch'):
            from .studio import run
            return run(args.command=='launch')
        from .control import running,stop,command,remote_action
        from ..settings import settings
        from ..profiles import load_profile,dumps_profile,loads_profile
        if args.command=='stop': stop();return 0
        if args.command=='menu':
            if not running(): raise RuntimeError('Start the overlay before opening its quick menu.')
            remote_action('menu');return 0
        cfg=settings()
        if args.command=='status':
            print(json.dumps({'running':running(),'visible':cfg.get_boolean('visible'),
                              'preset':loads_profile(cfg.get_string('profile'))['name']}));return 0
        if args.command=='profile':
            if not args.file: parser.error('profile requires a JSON file')
            command(cfg,'profile',dumps_profile(load_profile(args.file)))
        else: command(cfg,args.command)
        return 0
    except (RuntimeError,ValueError,OSError,ImportError) as exc:
        print('ProjectScope: '+str(exc),file=sys.stderr);return 1

if __name__=='__main__': sys.exit(main())
