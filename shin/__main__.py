import argparse
import json
import sys
from pathlib import Path
from . import __version__, compile_source, VM, ShinError
from .models import load_models, mock_model
from .runtime import unique_object
import os
import secrets


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
    init = sub.add_parser('init', help='create a website, API, app or CMS project')
    init.add_argument('directory')
    init.add_argument('--template', choices=['website','api','app','cms'], default='website')
    token = sub.add_parser('token', help='create a new local CMS admin token file')
    token.add_argument('path')
    for action in ('serve','build'):
        command=sub.add_parser(action)
        command.add_argument('directory')
        command.add_argument('--content-db')
        command.add_argument('--allow-content', action='append', default=[])
        command.add_argument('--allow-model', action='append', default=[])
        command.add_argument('--model-config')
        if action=='serve':
            command.add_argument('--port',type=int,default=8000)
            command.add_argument('--admin-token-file')
        else:
            command.add_argument('--output',required=True)
            command.add_argument('--path',action='append',default=[])
            command.add_argument('--base-path',default='')
    args = parser.parse_args(argv)
    try:
        if args.command=='init':
            from .scaffold import scaffold
            scaffold(args.directory,args.template)
            print('Created '+args.template+' project: '+args.directory)
            return 0
        if args.command=='token':
            with os.fdopen(os.open(args.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as handle:
                handle.write(secrets.token_urlsafe(32)+'\n')
            print('Created admin token file (keep it private): '+args.path)
            return 0
        if args.command in ('serve','build'):
            from .web import Application
            from .content import ContentStore
            store=ContentStore(args.content_db,args.allow_content) if args.content_db else None
            models=load_models(read_json(args.model_config)) if args.model_config else {'demo':mock_model()}
            token=read_file(args.admin_token_file).strip() if getattr(args,'admin_token_file',None) else None
            app=Application(args.directory,content=store,allow_content=args.allow_content,
                            admin_token=token,allow_models=args.allow_model,models=models)
            if args.command=='build':
                from .sitebuild import build
                count=build(app,args.output,args.path,args.base_path)
                print('Built '+str(count)+' pages into '+args.output)
            else:
                from wsgiref.simple_server import make_server, WSGIRequestHandler
                class Handler(WSGIRequestHandler):
                    def handle(self):
                        self.connection.settimeout(10)
                        return super().handle()
                    def log_message(self,*args):
                        pass  # Do not log user queries or content.
                with make_server('127.0.0.1',args.port,app,handler_class=Handler) as server:
                    print('SHIN development server: http://127.0.0.1:'+str(server.server_port),flush=True)
                    if token:
                        print('CMS editor: /_shin/admin (token authentication required)',flush=True)
                    server.serve_forever()
            return 0
        program = compile_source(read_file(args.source))
        if args.command == 'check':
            print(json.dumps({'valid': True, 'effects': sorted(program.effects),
                              'functions': sorted(program.functions),
                              'limits': program.limits, 'content_effects': sorted(program.content_effects)}, ensure_ascii=False))
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
    except KeyboardInterrupt:
        return 0
    except (ShinError, OSError, ValueError, UnicodeError, RecursionError) as exc:
        safe = str(exc) if not isinstance(exc, RecursionError) else 'input nesting limit exceeded'
        print('shin: ' + safe, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
