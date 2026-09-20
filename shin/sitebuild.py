"""Export explicit GET paths to a new static directory; never overwrite a project."""
import io
from pathlib import Path
import re
import shutil
import tempfile
from importlib import resources
from .compiler import ShinError
from .markup import HTML


def build(application,output,paths,base_path=""):
    if base_path and not re.fullmatch(r"/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*",base_path):
        raise ShinError("invalid static base path")
    target=Path(output)
    if target.exists():
        raise ShinError('build output already exists; choose a new directory')
    if not paths:
        raise ShinError('specify at least one --path, for example --path /')
    if len(set(paths))!=len(paths) or len(paths)>100:
        raise ShinError('static build supports 1..100 unique paths')
    for path in paths:
        if not re.fullmatch(r'/(?:[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*)?',path):
            raise ShinError('static path must be / or safe path segments without a trailing slash')
        if path.startswith(('/_shin','/assets')):
            raise ShinError('reserved static path')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        stage=Path(temporary)/'site';stage.mkdir()
        host=sorted(application.allowed_hosts)[0]
        if ':' in host:host='['+host+']'
        for path in paths:
            status,mime,data=application.dispatch({'HTTP_HOST':host,
                'wsgi.url_scheme':'http','PATH_INFO':path,'REQUEST_METHOD':'GET','QUERY_STRING':'','wsgi.input':io.BytesIO()})
            if status!=200 or not mime.startswith('text/html'):
                raise ShinError('static path must return HTML status 200: '+path)
            if base_path:
                data=re.sub(r'((?:href|src|action)=")/(?!/)', lambda m:m.group(1)+base_path+'/', data.decode('utf-8')).encode('utf-8')
            dest=stage/path.strip('/')/'index.html'
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        assets=stage/'assets';assets.mkdir()
        (assets/'site.css').write_bytes(resources.files('shin').joinpath('assets/site.css').read_bytes())
        public=application.root/'public'
        if public.is_symlink():
            raise ShinError('symlink public directories are forbidden')
        if public.exists():
            for file in public.rglob('*'):
                if file.is_symlink():
                    raise ShinError('symlinks are not allowed in static assets')
                if file.is_file():
                    if file.suffix not in ('.css','.js','.png','.jpg','.jpeg','.webp','.ico','.woff2') or file.stat().st_size>1048576:
                        raise ShinError('unsupported static asset: '+file.name)
                    dest=assets/file.relative_to(public)
                    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest)
        # Dynamic API-backed apps should be served, not exported as static sites.
        if any(method!='GET' for method,_,_,_ in application.routes):
            raise ShinError('application contains write/API routes; use serve rather than static build')
        stage.rename(target)
    return len(paths)
