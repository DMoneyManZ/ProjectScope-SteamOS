#!/usr/bin/env python3
"""Build an auditable source bundle; excludes local notes, logs and datasets."""
import hashlib
import io
from pathlib import Path
import tempfile
import zipapp
import zipfile
from build_release import ROOT,public_files


def main():
    files=list(public_files())+[ROOT/'docs/STEAMOS.md']
    output=ROOT/'dist/steamos';output.mkdir(parents=True,exist_ok=True)
    source=output/'ProjectScope-SteamOS-0.1.0-preview-source.zip'
    with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in files: archive.write(path,path.relative_to(ROOT).as_posix())
    installer=output/'ProjectScope-SteamOS-0.1.0-preview-linux.run'
    with tempfile.TemporaryDirectory() as temporary:
        staging=Path(temporary)
        (staging/'__main__.py').write_bytes((ROOT/'tools/steamos_installer_main.py').read_bytes())
        (staging/'installer_main.py').write_bytes((ROOT/'tools/installer_main.py').read_bytes())
        (staging/'payload.zip').write_bytes(source.read_bytes())
        zipapp.create_archive(staging,installer,interpreter='/usr/bin/env python3',compressed=True)
    installer.chmod(0o755)
    (output/'SHA256SUMS').write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n' for path in (source,installer)))
    print(installer)

if __name__=='__main__': main()
