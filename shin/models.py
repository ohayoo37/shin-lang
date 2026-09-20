"""Explicit host-configured adapters. v0.1 supports mock and loopback Ollama."""
import json
import urllib.error
import urllib.parse
import urllib.request
from .compiler import ShinError


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ShinError('model endpoint redirects are forbidden')


def mock_model(response=None):
    def call(prompt, timeout, max_bytes):
        return prompt if response is None else response
    return call


def ollama_model(url, model):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', '::1')
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('', '/')):
        raise ShinError('Ollama endpoint must be an explicit loopback HTTP origin')
    try:
        port = parsed.port
    except ValueError:
        raise ShinError('invalid endpoint port') from None
    if port is not None and not 1 <= port <= 65535:
        raise ShinError('invalid endpoint port')
    if type(model) is not str or not model or len(model) > 200:
        raise ShinError('invalid Ollama model name')
    origin = url.rstrip('/')
    # Ignore environment proxy settings; never follow server redirects.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(prompt, timeout, max_bytes):
        data = json.dumps({'model': model, 'prompt': prompt, 'stream': False,
                           'options': {'num_predict': 256}}).encode('utf-8')
        request = urllib.request.Request(origin + '/api/generate', data=data,
                                         headers={'Content-Type': 'application/json'})
        try:
            with opener.open(request, timeout=max(0.001, timeout)) as response:
                raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ShinError('model response exceeds value_bytes budget')
            result = json.loads(raw)
            if type(result) is not dict or type(result.get('response')) is not str:
                raise ShinError('invalid Ollama response shape')
            return result['response']
        except ShinError:
            raise
        except (OSError, ValueError, RecursionError, urllib.error.URLError):
            raise ShinError('Ollama request failed; check the local server and model') from None
    return call


def load_models(config):
    if type(config) is not dict or set(config) != {'models'} or type(config['models']) is not dict:
        raise ShinError('model config requires exactly one models object')
    models = {}
    for name, spec in config['models'].items():
        if type(spec) is not dict:
            raise ShinError('invalid model configuration')
        if spec.get('provider') == 'mock':
            if set(spec) - {'provider', 'response'}:
                raise ShinError('unknown mock configuration field')
            response = spec.get('response')
            if response is not None and type(response) is not str:
                raise ShinError('mock response must be text')
            models[name] = mock_model(response)
        elif spec.get('provider') == 'ollama':
            if set(spec) != {'provider', 'url', 'model'}:
                raise ShinError('Ollama requires provider, url, model')
            if type(spec['url']) is not str:
                raise ShinError('Ollama url must be text')
            models[name] = ollama_model(spec['url'], spec['model'])
        else:
            raise ShinError('unknown model provider')
    return models
