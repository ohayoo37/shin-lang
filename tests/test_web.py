import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from shin import compile_source, VM, ShinError
from shin.markup import render, HTML, link
from shin.content import ContentStore, ContentError
from shin.scaffold import scaffold
from shin.sitebuild import build
from shin.web import Application

TOKEN='t'*43


def request(app,path='/',method='GET',data=None,auth=False,**extra):
    raw=json.dumps(data,ensure_ascii=False).encode() if data is not None else b''
    env={'HTTP_HOST':'127.0.0.1','wsgi.url_scheme':'http','PATH_INFO':path,
         'REQUEST_METHOD':method,'QUERY_STRING':'','CONTENT_LENGTH':str(len(raw)),
         'CONTENT_TYPE':'application/json','wsgi.input':io.BytesIO(raw)}
    if auth:env['HTTP_AUTHORIZATION']='Bearer '+TOKEN
    env.update(extra)
    captured={}
    def start(status,headers):captured.update(status=int(status.split()[0]),headers=dict(headers))
    captured['body']=b''.join(app(env,start))
    return captured


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.db=ContentStore(self.root/'content.sqlite',['pages'])

    def app(self,kind='cms',admin=True):
        root=self.root/kind
        if not root.exists():scaffold(root,kind)
        return Application(root,content=self.db,allow_content=['pages'],admin_token=TOKEN if admin else None)

    def article(self,published=False):
        return {'collection':'pages','slug':'hello','title':'Hello','body':'First body','published':published,'revision':0}

    def test_all_scaffolds_execute(self):
        for kind in ('website','api','cms','app'):
            with self.subTest(kind=kind):
                result=request(self.app(kind),'/api/health' if kind=='api' else '/')
                self.assertEqual(result['status'],200,result['body'])
                self.assertIn('Content-Security-Policy',result['headers'])

    def test_api_json(self):
        result=request(self.app('api'),'/api/echo','POST',{'text':'日本語'})
        self.assertEqual(json.loads(result['body']),{'received':{'text':'日本語'}})

    def test_app_calculates(self):
        app=self.app('app')
        result=request(app,'/api/estimate','POST',{'hours':5,'rate':3000})
        self.assertEqual(json.loads(result['body'])['total'],15000)
        self.assertEqual(request(app,'/api/estimate','POST',{'hours':'bad','rate':3})['status'],422)
        self.assertEqual(request(app,'/api/estimate','POST',{'hours':-1,'rate':3})['status'],422)

    def test_publication_lifecycle_and_restart(self):
        app=self.app()
        created=request(app,'/_shin/api/content','PUT',self.article(),auth=True)
        self.assertEqual(created['status'],200)
        self.assertEqual(request(app,'/pages/hello')['status'],404)
        self.assertNotIn(b'First body',request(app)['body'])
        edit=self.article(True);edit['revision']=1
        self.assertEqual(request(app,'/_shin/api/content','PUT',edit,auth=True)['status'],200)
        reopened=Application(self.root/'cms',content=ContentStore(self.db.path,['pages']),allow_content=['pages'])
        self.assertIn(b'First body',request(reopened,'/pages/hello')['body'])
        edit.update(revision=2,published=False)
        self.assertEqual(request(app,'/_shin/api/content','PUT',edit,auth=True)['status'],200)
        self.assertEqual(request(app,'/pages/hello')['status'],404)

    def test_stale_revision_rejected(self):
        self.db.put(self.article())
        with self.assertRaisesRegex(ContentError,'revision conflict'):
            self.db.put(self.article())
        self.assertEqual(self.db.admin_get('pages','hello')['revision'],1)

    def test_auth_required_for_reads_and_writes(self):
        app=self.app()
        for method,data in [('GET',None),('PUT',self.article())]:
            self.assertEqual(request(app,'/_shin/api/content',method,data)['status'],401)
        self.assertEqual(self.db.admin_list('pages')['items'],[])

    def test_admin_opt_in(self):
        app=self.app(admin=False)
        self.assertEqual(request(app,'/_shin/admin')['status'],404)
        self.assertEqual(request(app,'/_shin/api/content',auth=True)['status'],404)

    def test_admin_ui_static_resources(self):
        app=self.app()
        for path in ('/_shin/admin','/_shin/admin.js','/_shin/admin.css'):
            result=request(app,path)
            self.assertEqual(result['status'],200)
            self.assertNotIn(TOKEN.encode(),result['body'])

    def test_cross_origin_blocked(self):
        result=request(self.app(),'/_shin/api/content','PUT',self.article(),auth=True,HTTP_ORIGIN='https://evil.example')
        self.assertEqual(result['status'],403)

    def test_host_header_blocked(self):
        self.assertEqual(request(self.app(),HTTP_HOST='rebind.example')['status'],400)

    def test_content_grant_required(self):
        scaffold(self.root/'cms','cms')
        with self.assertRaisesRegex(ShinError,'denied content'):
            Application(self.root/'cms',content=self.db)
        with self.assertRaisesRegex(ShinError,'missing permit content'):
            compile_source('content_list("pages");')

    def test_content_results_are_untrusted(self):
        code=compile_source('permit content "pages"; print(content_list("pages"));')
        with self.assertRaisesRegex(ShinError,'untrusted'):
            VM(code,content=self.db,allow_content=['pages']).run()

    def test_content_xss_escaped(self):
        data=self.article(True);data.update(title='<script>alert(1)</script>',body='<img src=x onerror=alert(1)>')
        self.db.put(data)
        result=request(self.app(),'/pages/hello')
        self.assertEqual(result['status'],200)
        self.assertIn(b'&lt;script&gt;',result['body'])
        self.assertNotIn(b'<img src=x',result['body'])

    def test_html_validation(self):
        self.assertEqual(render('<p>{{text}}</p>',{'text':'<img onerror=x>'}).value,'<p>&lt;img onerror=x&gt;</p>')
        for template in ['<script>alert(1)</script>','<img src="/x" onerror="x">','<a href="javascript:x">x</a>',
                         '<a href="{{url}}">x</a>','<scr{{x}}','<iframe src="/x"></iframe>','<p>x</div>']:
            with self.subTest(template=template),self.assertRaises(ShinError):render(template,{'x':HTML('>')})

    def test_dynamic_template_forbidden(self):
        with self.assertRaisesRegex(ShinError,'literal'):
            compile_source('let template="<p>x</p>"; html(template,{});')

    def test_links_and_fragments(self):
        self.assertIn('&lt;x&gt;',link('/pages/hello','<x>').value)
        for url in ('javascript:alert(1)','//evil.example','/\\evil','data:text/html,x'):
            with self.assertRaises(ShinError):link(url,'x')
        self.assertEqual(render('<div>{{part}}</div>',{'part':render('<p>x</p>',{})}).value,'<div><p>x</p></div>')

    def test_http_errors(self):
        app=self.app('api')
        self.assertEqual(request(app,'/nope')['status'],404)
        self.assertEqual(request(app,'/api/health','POST',{})['status'],405)
        self.assertEqual(request(app,'/api/echo','POST',{},CONTENT_LENGTH='999999')['status'],413)
        self.assertEqual(request(app,'/api/echo','POST',{},CONTENT_TYPE='text/plain')['status'],415)
        self.assertEqual(request(app,'/api/echo','POST',{},CONTENT_LENGTH='')['status'],411)
        self.assertEqual(request(app,'/api/echo','POST',{},CONTENT_LENGTH='1',**{'wsgi.input':io.BytesIO(b'{')})['status'],400)
        self.assertEqual(request(app,'/api/health',QUERY_STRING='x=1&x=2')['status'],400)

    def test_request_is_untrusted(self):
        root=self.root/'custom';root.mkdir()
        (root/'app.shin').write_text('fn home(req){return respond(200, req);}')
        (root/'app.json').write_text('{"routes":[{"method":"GET","path":"/","handler":"home"}]}')
        result=request(Application(root))
        self.assertEqual(result['status'],500)
        self.assertNotIn(b'Traceback',result['body'])

    def test_head(self):
        result=request(self.app('website'),method='HEAD')
        self.assertEqual(result['status'],200)
        self.assertEqual(result['body'],b'')
        self.assertGreater(int(result['headers']['Content-Length']),0)

    def test_assets_no_source_or_traversal(self):
        app=self.app('app')
        self.assertEqual(request(app,'/assets/app.js')['status'],200)
        for path in ('/assets/../app.shin','/app.shin','/.env','/assets/../../content.sqlite'):
            self.assertEqual(request(app,path)['status'],404)
        public=self.root/'app/public';(public/'escape.js').symlink_to(self.root/'app/app.shin')
        self.assertEqual(request(app,'/assets/escape.js')['status'],404)

    def test_static_export(self):
        app=self.app('website');target=self.root/'site'
        self.assertEqual(build(app,target,['/','/about'],'/demo'),2)
        self.assertTrue((target/'about/index.html').is_file())
        self.assertIn('href="/demo/assets/site.css"',(target/'index.html').read_text())
        self.assertTrue((target/'assets/site.css').is_file())
        with self.assertRaises(ShinError):build(app,target,['/'])

    def test_static_build_rejects_api_and_bad_paths(self):
        with self.assertRaisesRegex(ShinError,'API routes'):
            build(self.app('app'),self.root/'site',['/'])
        self.assertFalse((self.root/'site').exists())
        for path in ('/../x','/_shin/admin','//evil','/a?x=1'):
            with self.assertRaises(ShinError):build(self.app('website'),self.root/'out',[path])

    def test_cms_validation(self):
        for change in ({'slug':'../x'},{'collection':'other'},{'title':''},{'revision':True},{'body':'x'*16385}):
            data=self.article();data.update(change)
            with self.subTest(change=change),self.assertRaises(ContentError):self.db.put(data)

    def test_scaffold_no_overwrite(self):
        scaffold(self.root/'website','website')
        with self.assertRaises(ShinError):scaffold(self.root/'website','website')

    def test_utf8_route_parameter(self):
        root=self.root/'unicode';root.mkdir()
        (root/'app.shin').write_text('fn greet(r){let req=check_json(r,{"method":"text","path":"text","params":"record","query":"record","body":"record"});return respond(200,req["params"]["name"]);}')
        (root/'app.json').write_text('{"routes":[{"method":"GET","path":"/hello/:name","handler":"greet"}]}')
        path='/hello/日本語'.encode('utf-8').decode('latin-1')
        self.assertEqual(request(Application(root),path)['body'].decode(),'日本語')

    def test_static_route_precedes_parameter(self):
        root=self.root/'custom';root.mkdir()
        (root/'app.shin').write_text('fn dynamic(r){return respond(200,"dynamic");} fn fixed(r){return respond(200,"fixed");}')
        (root/'app.json').write_text(json.dumps({'routes':[{'method':'GET','path':'/:slug','handler':'dynamic'},{'method':'GET','path':'/about','handler':'fixed'}]}))
        self.assertEqual(request(Application(root),'/about')['body'],b'fixed')

if __name__=='__main__':unittest.main()
