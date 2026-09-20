"""Generate the English-first, script-independent multilingual public website."""
import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
BASE = 'https://ohayoo37.github.io/shin-lang/'
REPO = 'https://github.com/ohayoo37/shin-lang'
LOCALES = ['en', 'ja', 'es', 'fr', 'de', 'pt-BR', 'zh-CN', 'ko']


def generate():
    translations = {lang: json.loads((DOCS / 'i18n' / (lang + '.json')).read_text()) for lang in LOCALES}
    for lang, values in translations.items():
        if values.keys() != translations['en'].keys() or any(not isinstance(v, str) or not v for v in values.values()):
            raise ValueError('Incomplete translation: ' + lang)
    outputs = {}
    for route in [''] + LOCALES:
        lang = route or 'en'
        t = {k: html.escape(v, quote=True) for k, v in translations[lang].items()}
        prefix = '../' if route else ''
        alternates = ''.join(f'<link rel="alternate" hreflang="{code}" href="{BASE}{code}/">' for code in LOCALES)
        menu = ''.join(f'<a lang="{code}" hreflang="{code}" href="{prefix}{code}/"' + (' aria-current="page"' if code == lang else '') + f'>{html.escape(translations[code]["name"])}</a>' for code in LOCALES)
        cards = ''.join(f'<article class="card"><span class="number">{label}</span><h3>{t[key+"_title"]}</h3><p>{t[key+"_body"]}</p>{link}</article>' for key, label, link in [
            ('website', 'WEBSITE', f'<p><a href="{prefix}demo/">{t["demo"]}</a> <small lang="en">(English)</small></p>'),
            ('app', 'APPLICATION', ''), ('cms', 'CMS', f'<p><a href="{REPO}/blob/main/docs/web.md">{t["guide"]}</a></p>')])
        contributing = 'CONTRIBUTING.ja.md' if lang == 'ja' else 'CONTRIBUTING.md'
        metrics = ''.join(f'<div><strong>{t[key]}</strong><span>{t[key+"_note"]}</span></div>' for key in ['deps', 'bytecode', 'effects'])
        page = f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t['title']}</title><meta name="description" content="{t['description']}"><meta name="theme-color" content="#101715">
<link rel="canonical" href="{BASE}{lang}/">{alternates}<link rel="alternate" hreflang="x-default" href="{BASE}">
<meta property="og:title" content="{t['title']}"><meta property="og:description" content="{t['description']}"><meta property="og:url" content="{BASE}{lang}/"><meta property="og:type" content="website">
<link rel="stylesheet" href="{prefix}site.css"><script src="{prefix}site.js" defer></script></head>
<body><a class="skip" href="#main">{t['skip']}</a><div class="wrap">
<nav aria-label="{t['nav']}"><a class="brand" href="./">SHIN</a><div class="navlinks"><a class="hide-mobile" href="#start">{t['start']}</a><a href="{REPO}">GitHub ↗</a><details class="languages"><summary aria-label="{t['language']}">{t['name']}</summary><div class="language-menu">{menu}</div></details></div></nav>
<main id="main"><div class="hero"><div><div class="eyebrow">WEB · APPS · CMS · AI</div><h1>{t['headline1']}<br><em>{t['headline2']}</em></h1><p class="lead">{t['lead']}</p><span class="pill">v0.2.0a2 / EXPERIMENTAL / MIT</span><div class="actions"><a class="button primary" href="#start">{t['try']}</a><a class="button" href="{REPO}/releases">{t['release']}</a></div></div>
<div class="codebox"><div class="codehead"><span>answer.shin</span><span>SHIN</span></div><pre><span class="kw">permit model</span> <span class="str">"demo"</span>;
<span class="kw">budget</span> steps = 1000;

<span class="kw">fn</span> answer(prompt) {{
    <span class="kw">let</span> draft = infer(<span class="str">"demo"</span>, prompt);
    <span class="kw">return</span> check_text(draft, 200);
}}

print(answer(<span class="str">"Hello, SHIN."</span>));</pre><div class="result"><b>✓</b> {t['grant']}<br><b>✓</b> {t['validate']}<br>{t['mock']}</div></div></div>
<div class="strip">{metrics}</div>
<section id="web"><div class="sectionhead"><h2>{t['web_title']}</h2></div><div class="cards">{cards}</div><p class="note limits">{t['limits']}</p></section>
<section id="start"><div class="sectionhead"><h2>{t['start_title']}</h2></div><div class="quick"><div><p>{t['requirements']}</p><p>{t['local_model']}</p><a class="button" href="{REPO}/blob/main/docs/web.md">{t['guide']}</a></div><div class="codebox"><div class="codehead"><span>TERMINAL</span><button class="copy" id="copy" type="button" data-success="{t['copied']}" data-failure="{t['copy_failed']}">{t['copy']}</button></div><pre id="commands">git clone https://github.com/ohayoo37/shin-lang.git
cd shin-lang
python3 -m shin init my-site --template website
python3 -m shin serve my-site --port 8000</pre><div class="result" id="copy-status" aria-live="polite">{t['open_local']}</div></div></div></section>
<section><div class="sectionhead"><h2>{t['status_title']}</h2></div><div class="status"><div><p>{t['status_body']}</p><a href="{REPO}/tree/main/tests">{t['tests']}</a></div><div><p class="note">{t['performance']}</p><p><a href="{REPO}/blob/main/docs/roadmap.md">{t['roadmap']} ↗</a></p></div></div></section>
<section id="community"><div class="sectionhead"><h2>{t['community_title']}</h2></div><p class="lead">{t['community_body']}</p><div class="actions"><a class="button primary" href="{REPO}/blob/main/{contributing}">{t['contribute']}</a><a class="button" href="{REPO}/discussions">{t['discuss']}</a><a class="button" href="{REPO}/issues/new/choose">{t['report']}</a></div></section></main>
<footer class="footer"><div>SHIN · 2026 · MIT</div><div><a href="{REPO}/blob/main/SECURITY.md">{t['security']}</a><a href="{REPO}/blob/main/docs/language.md">{t['spec']}</a></div></footer></div></body></html>
'''
        outputs[DOCS / route / 'index.html'] = page
    outputs[DOCS / 'sitemap.xml'] = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{BASE}{lang}/</loc></url>' for lang in LOCALES) + '</urlset>\n'
    return outputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for path, content in generate().items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit('Stale generated file: ' + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
    print('Verified' if args.check else 'Generated', '8 languages and English default.')
