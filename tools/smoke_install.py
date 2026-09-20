"""Exercise the installed package from outside the repository on each OS."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    def run(*args):
        return subprocess.run([sys.executable, '-m', 'shin', *args], cwd=root,
                              env=env, check=True, capture_output=True, text=True).stdout
    print(run('--version').strip())
    (root/'hello.shin').write_text('print("Hello, installed SHIN!");', encoding='utf-8')
    assert run('run', 'hello.shin').strip() == 'Hello, installed SHIN!'
    run('init', 'site', '--template', 'website')
    run('build', 'site', '--output', 'public', '--path', '/', '--path', '/about')
    assert 'SHIN Studio' in (root/'public/index.html').read_text(encoding='utf-8')
    print('Installed package: version, execution, project creation and static build passed.')
