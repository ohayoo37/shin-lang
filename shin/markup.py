"""HTML fragments: literal templates, text-only placeholders, explicit links."""
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit
from .compiler import ShinError


@dataclass(frozen=True)
class HTML:
    value: str


TAGS = set('html head body title meta main header footer nav section article aside div span p h1 h2 h3 h4 h5 h6 ul ol li a strong em b i code pre blockquote br hr img table thead tbody tr th td dl dt dd time small label button form input textarea select option link script'.split())
VOID = {'meta','br','hr','img','input','link'}
ATTRS = set('class id title href src alt width height lang charset name content rel type value for method action placeholder required disabled rows cols role defer'.split())
PLACEHOLDER = re.compile(r'\{\{\s*([A-Za-z_][A-Za-z_0-9]*)\s*\}\}')


def safe_url(value):
    if type(value) is not str or not value or any(ord(c) < 33 for c in value) or '\\' in value:
        raise ShinError('invalid link URL')
    if value.startswith(('/', '#')) and not value.startswith('//'):
        return value
    parts = urlsplit(value)
    if parts.scheme in ('http','https') and parts.hostname and not parts.username and not parts.password:
        return value
    raise ShinError('link requires /path, #anchor, or an http(s) URL')


class Renderer(HTMLParser):
    def __init__(self, bindings):
        super().__init__(convert_charrefs=False)
        self.bindings, self.output, self.stack = bindings, [], []

    def handle_starttag(self, tag, attrs):
        if tag not in TAGS:
            raise ShinError('HTML tag not supported: ' + tag)
        if tag == 'script':
            fields = dict(attrs)
            if set(fields) - {'src', 'defer'} or not fields.get('src', '').startswith('/assets/'):
                raise ShinError('scripts require a static /assets/ source')
        names=set()
        out=[]
        for key, value in attrs:
            if key in names or (key not in ATTRS and not key.startswith(('aria-','data-'))):
                raise ShinError('HTML attribute not supported: ' + key)
            names.add(key)
            if value and ('{{' in value or '}}' in value):
                raise ShinError('HTML placeholders are allowed only in text nodes; use link() for URLs')
            if key in ('href','src','action'):
                safe_url(value)
            if key=='rel' and value not in ('stylesheet','noopener','noreferrer'):
                raise ShinError('unsupported link relation')
            if tag=='meta' and key not in ('charset','name','content'):
                raise ShinError('unsupported meta attribute')
            out.append(' '+key if value is None else ' '+key+'="'+escape(value,quote=True)+'"')
        self.output.append('<'+tag+''.join(out)+'>')
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self,tag):
        if not self.stack or self.stack[-1]!=tag:
            raise ShinError('HTML template has mismatched closing tags')
        self.stack.pop()
        self.output.append('</'+tag+'>')

    def handle_data(self,data):
        if self.stack and self.stack[-1] == "script" and data.strip():
            raise ShinError("inline script content is forbidden")
        if "<" in data:
            raise ShinError("literal less-than in HTML text must use &lt;")
        def substitute(match):
            key=match.group(1)
            if key not in self.bindings:
                raise ShinError('missing HTML binding: '+key)
            value=self.bindings[key]
            if isinstance(value,HTML):
                if self.stack and self.stack[-1] in ('title','textarea'):
                    raise ShinError('HTML fragments cannot be placed inside title or textarea')
                return value.value
            if type(value) not in (str,int,float,bool) and value is not None:
                raise ShinError('HTML binding must be a scalar or HTML fragment')
            return escape('' if value is None else str(value),quote=True)
        self.output.append(PLACEHOLDER.sub(substitute,data))

    def handle_entityref(self,name):
        self.output.append('&'+name+';')

    def handle_charref(self,name):
        self.output.append('&#'+name+';')

    def handle_comment(self,data):
        if '{{' in data:
            raise ShinError('HTML placeholders cannot appear in comments')
        self.output.append('<!--'+data+'-->')

    def handle_decl(self,decl):
        if decl.lower()!='doctype html':
            raise ShinError('unsupported HTML declaration')
        self.output.append('<!doctype html>')

    def unknown_decl(self,data):
        raise ShinError('unsupported HTML declaration')


def render(template,bindings):
    if type(template) is not str or type(bindings) is not dict:
        raise ShinError('html expects a literal template and a record')
    renderer=Renderer(bindings)
    renderer.feed(template)
    renderer.close()
    if renderer.stack:
        raise ShinError('HTML template contains unclosed tags')
    return HTML(''.join(renderer.output))


def link(url,label):
    if type(label) is not str:
        raise ShinError('link label must be text')
    return HTML('<a href="'+escape(safe_url(url),quote=True)+'">'+escape(label)+'</a>')


def join(fragments):
    if type(fragments) is not list or any(not isinstance(v,HTML) for v in fragments):
        raise ShinError('html_join expects an array of HTML fragments')
    return HTML(''.join(v.value for v in fragments))
