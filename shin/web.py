"""WSGI application adapter. The bundled HTTP server is for loopback development."""
import hmac
import json
from pathlib import Path
import re
from urllib.parse import parse_qs
from http import HTTPStatus
from importlib import resources
from .compiler import ShinError, compile_source
from .runtime import VM, Untrusted, encode, size, unique_object, reject_constant
from .markup import HTML
from .content import ContentError

MAX_BODY=32768
SECURITY_HEADERS=[('X-Content-Type-Options','nosniff'),('Referrer-Policy','no-referrer'),
                  ('X-Frame-Options','DENY'),('Cache-Control','no-store'),
                  ('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")]


class HTTPError(Exception):
    def __init__(self,status,message):
        self.status,self.message=status,message


def bounded_file(path,limit=65536):
    with Path(path).open('rb') as f:
        data=f.read(limit+1)
    if len(data)>limit:
        raise ShinError('application file exceeds size limit')
    return data.decode('utf-8')


def parse_json(raw):
    return json.loads(raw,object_pairs_hook=unique_object,parse_constant=reject_constant)


class Application:
    def __init__(self, directory, content=None, allow_content=(), admin_token=None,
                 allow_models=(), models=None, allowed_hosts=('127.0.0.1','localhost','::1')):
        root=Path(directory).resolve()
        config=parse_json(bounded_file(root/'app.json'))
        if type(config) is not dict or set(config)!={'routes'} or type(config['routes']) is not list or not 1<=len(config['routes'])<=64:
            raise ShinError('app.json requires 1..64 routes')
        self.program=compile_source(bounded_file(root/'app.shin'))
        self.root=root
        self.content=content
        self.allow_content=set(allow_content)
        self.allow_models=set(allow_models)
        self.models=models or {}
        self.allowed_hosts=set(allowed_hosts)
        if not self.allowed_hosts:
            raise ShinError('allowed_hosts cannot be empty')
        if admin_token is not None and (not re.fullmatch(r'[A-Za-z0-9_-]{32,128}',admin_token) or content is None):
            raise ShinError('admin requires content storage and a 32..128 character token')
        self.admin_token=admin_token
        self.routes=[]
        seen=set()
        for route in config['routes']:
            if type(route) is not dict or set(route)!={'method','path','handler'}:
                raise ShinError('route requires method, path and handler')
            method,path,handler=route['method'],route['path'],route['handler']
            if method not in ('GET','POST','PUT','PATCH','DELETE') or type(path) is not str or not path.startswith('/') or len(path)>200 or path.startswith(('/_shin','/assets')):
                raise ShinError('invalid or reserved route')
            parts=path.split('/')[1:]
            names=[]; pattern=[]
            for part in parts:
                if part.startswith(':'):
                    name=part[1:]
                    if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*',name) or name in names:
                        raise ShinError('invalid route parameter')
                    names.append(name); pattern.append('(?P<'+name+'>[^/]+)')
                else:
                    if not re.fullmatch('[A-Za-z0-9_-]*',part):
                        raise ShinError('invalid route path')
                    pattern.append(re.escape(part))
            shape=(method,tuple(':' if p.startswith(':') else p for p in parts))
            if shape in seen:
                raise ShinError('duplicate route pattern')
            seen.add(shape)
            if type(handler) is not str or handler not in self.program.functions or len(self.program.functions[handler].params)!=1:
                raise ShinError('route handler must be a named function with one request parameter')
            self.routes.append((method,re.compile('^/'+'/'.join(pattern)+'$'),handler,len(names)))
        self.routes.sort(key=lambda route:route[3])
        self.new_vm().preflight()

    def new_vm(self):
        return VM(self.program,allow_models=self.allow_models,models=self.models,
                  content=self.content,allow_content=self.allow_content)

    def query(self,environ):
        raw=environ.get('QUERY_STRING','')
        if len(raw)>4096:
            raise HTTPError(414,'query too long')
        parsed=parse_qs(raw,keep_blank_values=True,max_num_fields=32)
        if any(len(v)!=1 for v in parsed.values()):
            raise HTTPError(400,'duplicate query field')
        return {k:v[0] for k,v in parsed.items()}

    def body(self,environ):
        raw_length=environ.get('CONTENT_LENGTH','')
        if environ.get('HTTP_TRANSFER_ENCODING'):
            raise HTTPError(400,'transfer encoding is not supported by this adapter')
        if not raw_length or not re.fullmatch('[0-9]+',raw_length):
            raise HTTPError(411,'content length required')
        length=int(raw_length)
        if length>MAX_BODY:
            raise HTTPError(413,'request body too large')
        if environ.get('CONTENT_TYPE','').split(';')[0].strip()!='application/json':
            raise HTTPError(415,'application/json required')
        raw=environ['wsgi.input'].read(length)
        if len(raw)!=length:
            raise HTTPError(400,'incomplete request body')
        data=parse_json(raw)
        if type(data) is not dict:
            raise HTTPError(400,'request JSON must be an object')
        size(data,65536)
        return data

    def check_host(self,environ):
        host=environ.get('HTTP_HOST','')
        # Explicit hostname matching prevents a browser DNS-rebinding origin.
        match=re.fullmatch(r'(\[[0-9a-fA-F:]+\]|[A-Za-z0-9.-]+)(?::([0-9]{1,5}))?',host)
        if not match or match.group(1).strip('[]').lower() not in self.allowed_hosts:
            raise HTTPError(400,'host not allowed')
        origin=environ.get('HTTP_ORIGIN')
        expected=environ.get('wsgi.url_scheme','http')+'://'+host
        if origin and origin!=expected:
            raise HTTPError(403,'cross-origin request denied')

    def admin(self,environ,path,method):
        if self.admin_token is None:
            raise HTTPError(404,'not found')
        if path=='/_shin/admin' and method in ('GET','HEAD'):
            return 200,'text/html; charset=utf-8',resources.files('shin').joinpath('assets/admin.html').read_bytes()
        if path=='/_shin/admin.js' and method in ('GET','HEAD'):
            return 200,'text/javascript; charset=utf-8',resources.files('shin').joinpath('assets/admin.js').read_bytes()
        if path=='/_shin/admin.css' and method in ('GET','HEAD'):
            return 200,'text/css; charset=utf-8',resources.files('shin').joinpath('assets/admin.css').read_bytes()
        if path!='/_shin/api/content':
            raise HTTPError(404,'not found')
        auth=environ.get('HTTP_AUTHORIZATION','')
        if not hmac.compare_digest(auth.encode('utf-8'),('Bearer '+self.admin_token).encode('utf-8')):
            raise HTTPError(401,'authentication required')
        if method=='GET':
            query=self.query(environ)
            collection=query.get('collection',sorted(self.content.collections)[0])
            if 'slug' in query:
                result=self.content.admin_get(collection,query['slug'])
            else:
                result=self.content.admin_list(collection,int(query.get('offset','0')))
                result['collections']=sorted(self.content.collections)
        elif method=='PUT':
            result=self.content.put(self.body(environ))
        else:
            raise HTTPError(405,'method not allowed')
        return 200,'application/json; charset=utf-8',encode(result).encode('utf-8')

    def dispatch(self,environ):
        self.check_host(environ)
        try:
            path=environ.get('PATH_INFO','/').encode('latin-1').decode('utf-8')
        except UnicodeError:
            raise HTTPError(400,'invalid UTF-8 path')
        method=environ.get('REQUEST_METHOD','GET')
        if len(path)>2048 or any(ord(c)<32 for c in path) or '\\' in path:
            raise HTTPError(400,'invalid path')
        if path.startswith('/_shin'):
            return self.admin(environ,path,method)
        if path=='/assets/site.css' and method in ('GET','HEAD') and not (self.root/'public/site.css').exists():
            return 200,'text/css; charset=utf-8',resources.files('shin').joinpath('assets/site.css').read_bytes()
        if path.startswith('/assets/') and method in ('GET','HEAD'):
            if (self.root/'public').is_symlink():
                raise HTTPError(404,'not found')
            public=(self.root/'public').resolve()
            asset=(public/path[len('/assets/'):]).resolve()
            try:
                asset.relative_to(public)
            except ValueError:
                raise HTTPError(404,'not found')
            types={'.css':'text/css','.js':'text/javascript','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.ico':'image/x-icon','.woff2':'font/woff2'}
            if asset.suffix not in types or not asset.is_file():
                raise HTTPError(404,'not found')
            with asset.open('rb') as handle:
                data=handle.read(1048577)
            if len(data)>1048576:
                raise HTTPError(413,'asset too large')
            return 200,types[asset.suffix],data
        allowed=[]
        for verb,pattern,handler,_ in self.routes:
            match=pattern.fullmatch(path)
            if match is None:
                continue
            allowed.append(verb)
            if verb!=('GET' if method=='HEAD' else method):
                continue
            body=self.body(environ) if method in ('POST','PUT','PATCH','DELETE') else {}
            request={'method':method,'path':path,'params':match.groupdict(),
                     'query':self.query(environ),'body':body}
            result=self.new_vm().invoke(handler,[Untrusted(encode(request))])
            if type(result) is not dict or set(result)!={'status','body'} or type(result['status']) is not int or result['status'] not in (200,201,202,400,401,403,404,409,422,500,503):
                raise ShinError('handler must return respond(status, body)')
            value=result['body']
            if isinstance(value,HTML):
                mime,data='text/html; charset=utf-8',value.value.encode('utf-8')
            elif type(value) is str:
                mime,data='text/plain; charset=utf-8',value.encode('utf-8')
            else:
                mime,data='application/json; charset=utf-8',encode(value).encode('utf-8')
            if len(data)>self.program.limits.get('output_bytes',65536):
                raise ShinError('response exceeds output_bytes budget')
            return result['status'],mime,data
        raise HTTPError(405 if allowed else 404,'method not allowed' if allowed else 'not found')

    def __call__(self,environ,start_response):
        try:
            status,mime,data=self.dispatch(environ)
        except (HTTPError,ContentError) as exc:
            status,mime,data=exc.status,'application/json; charset=utf-8',encode({'error':str(exc) if isinstance(exc,ContentError) else exc.message}).encode()
        except (ValueError,UnicodeError,RecursionError):
            status,mime,data=400,'application/json; charset=utf-8',b'{"error":"invalid request data"}'
        except Exception:
            # Never expose source, SQL, paths, configuration or model prompts to clients.
            status,mime,data=500,'application/json; charset=utf-8',b'{"error":"application error"}'
        headers=[('Content-Type',mime),('Content-Length',str(len(data)))]+SECURITY_HEADERS
        start_response(str(status)+' '+HTTPStatus(status).phrase,headers)
        return [b'' if environ.get('REQUEST_METHOD')=='HEAD' else data]
