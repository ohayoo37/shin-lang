"""Bundle the unchanged reference VM for the browser. No third-party build tools."""
import argparse
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FILES = ['__init__.py', 'compiler.py', 'runtime.py', 'markup.py']

def bundle():
    return json.dumps({'files': {name: (ROOT/'shin'/name).read_text(encoding='utf-8') for name in FILES},
        'bridge': (ROOT/'docs/playground/bridge.py').read_text(encoding='utf-8'),
        'license': (ROOT/'LICENSE').read_text(encoding='utf-8')}, ensure_ascii=False, sort_keys=True) + '\n'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT/'docs/playground/runtime.json'
    content = bundle()
    if args.check:
        if not path.exists() or path.read_text(encoding='utf-8') != content:
            raise SystemExit('Playground bundle is stale: run python3 tools/build_playground.py')
    else:
        path.write_text(content, encoding='utf-8')
    print('Playground reference runtime verified' if args.check else 'Playground reference runtime bundled')
