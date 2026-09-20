import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
import unittest
from shin import ShinError, VM, compile_source
from shin.models import load_models, ollama_model


class Handler(BaseHTTPRequestHandler):
    mode='success'
    seen=None

    def log_message(self, *_):
        pass

    def do_POST(self):
        type(self).seen=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.mode=='redirect':
            self.send_response(302)
            self.send_header('Location','http://example.invalid/forbidden')
            self.end_headers()
            return
        if self.mode=='slow':
            time.sleep(0.05)
        data=(b'x'*2000 if self.mode=='large' else json.dumps({'response':'local result'}).encode())
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        Handler.mode='success'

    def test_http_contract(self):
        model=ollama_model(self.url,'fixture')
        self.assertEqual(model('hello',1,1024),'local result')
        self.assertEqual(Handler.seen['model'],'fixture')
        self.assertEqual(Handler.seen['prompt'],'hello')
        self.assertFalse(Handler.seen['stream'])

    def test_redirect_denied(self):
        Handler.mode='redirect'
        with self.assertRaisesRegex(ShinError,'redirects'):
            ollama_model(self.url,'fixture')('hello',1,1024)

    def test_response_limit(self):
        Handler.mode='large'
        with self.assertRaisesRegex(ShinError,'exceeds'):
            ollama_model(self.url,'fixture')('hello',1,1024)

    def test_network_timeout(self):
        Handler.mode='slow'
        with self.assertRaisesRegex(ShinError,'request failed'):
            ollama_model(self.url,'fixture')('hello',0.005,1024)

    def test_endpoint_restrictions(self):
        for url in ['https://example.com','http://localhost:11434','http://127.0.0.1.evil.test',
                    'http://127.0.0.1:1/path','http://user:pass@127.0.0.1','http://127.0.0.1?x=1',
                    'http://127.0.0.1:99999','file:///etc/passwd']:
            with self.subTest(url=url),self.assertRaises(ShinError):
                ollama_model(url,'fixture')

    def test_config(self):
        models=load_models({'models':{'a':{'provider':'mock','response':'ok'}}})
        self.assertEqual(models['a']('x',1,100),'ok')
        for spec in [{}, {'models':[]}, {'models':{'x':{'provider':'shell'}}},
                     {'models':{'x':{'provider':'mock','response':1}}}]:
            with self.subTest(spec=spec),self.assertRaises(ShinError):
                load_models(spec)

    def test_wall_budget_after_host_callback(self):
        def slow(*_):
            time.sleep(0.02)
            return 'late'
        with self.assertRaisesRegex(ShinError,'wall_ms'):
            VM(compile_source('budget wall_ms=5; permit model "slow"; infer("slow","x");'),
               allow_models=['slow'],models={'slow':slow}).run()


if __name__=='__main__':
    unittest.main()
