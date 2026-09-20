"""Build a portable Python zipapp from only the runtime sources."""
import hashlib
from pathlib import Path
import shutil
import tempfile
import zipapp

root=Path(__file__).resolve().parents[1]
out=root/'dist'
out.mkdir(exist_ok=True)
archive=out/'shin-0.2.0a2.pyz'
with tempfile.TemporaryDirectory() as temporary:
    stage=Path(temporary)
    shutil.copytree(root/'shin',stage/'shin',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (stage/'__main__.py').write_text('from shin.__main__ import main\nraise SystemExit(main())\n')
    shutil.copy2(root/'LICENSE',stage/'LICENSE')
    zipapp.create_archive(stage,target=archive,interpreter='/usr/bin/env python3',compressed=True)
(out/'SHA256SUMS').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print(archive.name,archive.stat().st_size,'bytes; Python 3.9+ required')
