import argparse
import json
import sys
from pathlib import Path
from . import __version__, compile_source, VM, ShinError
from .models import load_models, mock_model
from .runtime import unique_object


def read_file(path):
    with Path(path).open('rb') as handle:
        data = handle.read(65537)
    if len(data) > 65536:
        raise ShinError('input file exceeds 65536 bytes')
    return data.decode('utf-8')


def read_json(path):
    return json.loads(read_file(path), object_pairs_hook=unique_object)


def safe_print(value):
    # Prevent model text from issuing terminal escape/control sequences.
    value = ''.join(c if c in '\n\t' or (ord(c) >= 32 and not 127 <= ord(c) < 160)
                    else f'\\u{ord(c):04x}' for c in value)
    print(value)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='shin', description='SHIN experimental language')
    parser.add_argument('--version', action='version', version='SHIN ' + __version__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('run', 'check', 'disasm'):
        command = sub.add_parser(name)
        command.add_argument('source')
        if name == 'run':
            command.add_argument('--allow-model', action='append', default=[])
            command.add_argument('--model-config')
            command.add_argument('--input', help='JSON input file, explicitly selected by the host')
            command.add_argument('--stats', action='store_true')
    args = parser.parse_args(argv)
    try:
        program = compile_source(read_file(args.source))
        if args.command == 'check':
            print(json.dumps({'valid': True, 'effects': sorted(program.effects),
                              'functions': sorted(program.functions),
                              'limits': program.limits}, ensure_ascii=False))
        elif args.command == 'disasm':
            for name, code in [('main', program.main)] + [(k, f.code) for k, f in program.functions.items()]:
                print(f'[{name}]')
                for i, (op, arg, line) in enumerate(code):
                    print(f'{i:04d} L{line:<4} {op:<12} {arg!r}')
        else:
            models = load_models(read_json(args.model_config)) if args.model_config else {'demo': mock_model()}
            vm = VM(program, args.allow_model, models,
                    read_json(args.input) if args.input else None, output=safe_print)
            vm.run()
            if args.stats:
                print(json.dumps({'steps': vm.steps, 'logical_allocation_bytes': vm.allocated,
                                  'output_bytes': vm.output_bytes}), file=sys.stderr)
        return 0
    except (ShinError, OSError, ValueError, UnicodeError, RecursionError) as exc:
        safe = str(exc) if not isinstance(exc, RecursionError) else 'input nesting limit exceeded'
        print('shin: ' + safe, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
