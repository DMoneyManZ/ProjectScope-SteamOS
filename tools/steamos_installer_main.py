"""Entrypoint for the SteamOS source installer; uses standard-library extraction."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from installer_main import extract_payload

def main():
    parser=argparse.ArgumentParser(description='ProjectScope SteamOS 0.1.0 preview — per-user installer')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true',help='Check installed runtime dependencies')
    group.add_argument('--install',action='store_true',help='Install below your home, without sudo')
    group.add_argument('--extract',type=Path,metavar='NEW_DIRECTORY',help='Extract the included GPL source')
    args=parser.parse_args()
    with zipfile.ZipFile(Path(sys.argv[0]).resolve()) as bundle: payload=bundle.read('payload.zip')
    if args.extract:
        extract_payload(payload,args.extract.expanduser().absolute());return 0
    with tempfile.TemporaryDirectory(prefix='projectscope-steamos-') as temporary:
        target=Path(temporary)/'source';extract_payload(payload,target)
        command=[sys.executable,str(target/'tools/install_steamos.py')]
        if args.check: command.append('--check')
        return subprocess.run(command,cwd=target).returncode
if __name__=='__main__':
    try: sys.exit(main())
    except (OSError,ValueError,zipfile.BadZipFile,KeyError) as exc:
        print('Installer failed: '+str(exc),file=sys.stderr);sys.exit(1)
