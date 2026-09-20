# Web, applications and CMS — SHIN 0.2 alpha

SHIN can now define server-rendered pages and JSON API handlers, export static websites, and read published content from a small SQLite CMS. Browser JavaScript can call SHIN APIs. This is an early web toolkit, not a finished WordPress replacement, native mobile toolkit or production hosting platform.

## Start from a working project

```sh
python3 -m shin init my-site --template website
python3 -m shin serve my-site --port 8000
```

Open `http://127.0.0.1:8000/`. The built-in server listens only on loopback. Restart it after editing SHIN source or routes; hot reload is not implemented. Templates:

| Template | Included behavior |
|---|---|
| `website` | Home + About pages, responsive stylesheet |
| `api` | GET `/api/health`, POST `/api/echo` (JSON) |
| `app` | Browser estimate form → POST `/api/estimate` → SHIN calculation |
| `cms` | Published article list + `/pages/:slug`, separate opt-in Content Studio |

`init` refuses an existing directory. You own the generated `app.shin`, `app.json`, and optional `public/` assets.

## Routing and handlers

`app.json` is trusted host configuration:

```json
{"routes":[{"method":"GET","path":"/hello/:name","handler":"hello"}]}
```

`app.shin`:

```text
fn hello(request) {
    let req = check_json(request, {
        "method":"text", "path":"text", "params":"record",
        "query":"record", "body":"record"
    });
    return respond(200, html("<h1>Hello, {{name}}</h1>", {
        "name": req["params"]["name"]
    }));
}
```

Each request gets a fresh VM and budgets; compiled code is reused. Main statements run before the handler. A handler takes one untrusted request value and returns `respond(status, body)`. The request contains method, path, named parameters, query values and a JSON body. It contains no arbitrary headers, cookies or credentials. Query values are strings; duplicates are rejected. Mutating requests require JSON objects, a Content-Length, and at most 32 KiB. Schema-check application-specific fields and ranges; structural request validation does not authorize user actions.

Literal routes precede parameterized routes; otherwise manifest order breaks ties. Duplicate route shapes are rejected. GET, POST, PUT, PATCH and DELETE may be declared; HEAD runs the GET handler and omits the body. `/assets` and `/_shin` are reserved. A missing route returns 404, wrong method 405. Internal errors return a generic 500 without stack traces.

Response bodies: `HTML` fragments → `text/html`; ordinary strings → `text/plain`; ordinary records/arrays/scalars → JSON. Supported status values: 200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503. Request/response checks do not turn SHIN into an authorization framework.

## HTML and assets

`html("literal template", bindings)` requires a **literal** template. Placeholders `{{name}}` are allowed only in text nodes. Scalar values are HTML-escaped. Already constructed `HTML` fragments can be nested; `html_join(array)` combines fragments. Collections are not automatically rendered. Placeholder use in attributes or comments is rejected. Use `link(url, label)` and `url_part(text)` for dynamic links.

Templates accept an allowlist of ordinary document, layout and form tags/attributes. No event handlers, inline styles, iframe or dynamic tag/attribute construction. Static `<script src="/assets/app.js" defer></script>` is supported; inline script content is forbidden. Use a separately authored asset file for application JavaScript. URLs accept `/path`, `#anchor`, or http(s), and reject protocol-relative and javascript/data URLs. This is deliberately narrower than arbitrary HTML templating.

`/assets/site.css` serves the bundled stylesheet unless the project supplies `public/site.css`. `public/` files are available under `/assets/` for css, js, png, jpg, jpeg, webp, ico and woff2, with a 1 MiB limit per file. Traversal outside this directory and symlinked public roots are rejected. Application sources, database files and arbitrary file types are not served. Host-authored assets are trusted code; do not place user uploads here. Static exports reject asset symlinks entirely.

## CMS: edit, save, publish

```sh
python3 -m shin init journal --template cms
python3 -m shin token journal/admin.token
python3 -m shin serve journal --port 8000 \
  --content-db journal/content.sqlite --allow-content pages \
  --admin-token-file journal/admin.token
```

Open `http://127.0.0.1:8000/_shin/admin`, then paste the token from your private file. `token` creates a new file with restrictive permissions and refuses overwrites. The generated `.gitignore` excludes tokens and SQLite databases. Keep the token private. The editor stores it only in browser memory; refresh/log out requires re-entry.

Content Studio creates and updates articles with slug, title, plain-text body, published state and revision. Save without the publication checkbox for drafts; check it to publish; uncheck it to unpublish. Public views immediately reflect the current published content. Restarting the server preserves the database. A stale revision produces 409 instead of silently overwriting another edit. Revision is a concurrency counter, **not** historical version recovery.

The administrative API is opt-in and uses Bearer authentication for every content read and write. It rejects cross-origin requests and unrecognized Host headers; no credential cookies or CORS are enabled. No default token is shipped. There is one administrator capability, not user accounts or role-based access control. Media uploads, rich text, deletion, revision history and audit logs are not implemented. Alpha storage limits: 1,000 total records, 200-character titles, 16 KiB UTF-8 bodies; editor lists 25 per page.

Source must declare `permit content "pages";` and the host must grant `--allow-content pages`. `content_list("pages")` returns **Untrusted JSON** shaped `{"items":[...]}` (first 25 published articles, slug order). `content_get("pages", slug)` returns `{"found":boolean,"item":record}` and never exposes drafts. Use `check_json` before use, and HTML escaping at rendering. Source code receives published read access only; no SQL or CMS write builtin is exposed. The separate trusted editor owns write capability.

## Static website export

```sh
python3 -m shin build my-site --output site-output --path / --path /about
```

This creates `index.html`, `about/index.html`, and assets in a **new** directory. Serve this directory with any static host. Use `--base-path /project/site` for a subdirectory deployment. Rebuild after content changes. To export CMS pages, pass the same database/content grant plus explicit published paths, e.g. `--path /pages/hello`. Builds fail if an explicitly selected route is missing or does not return HTML 200. Applications with non-GET routes are rejected; an API-backed app cannot be made static by copying its HTML.

## WSGI deployment boundary

The adapter is a WSGI callable:

```python
from shin.web import Application
application = Application('/absolute/path/to/project', allowed_hosts=['example.com'])
```

A separate WSGI server can host it. Configure a reverse proxy with TLS, request/concurrency limits, a private database/token, backup policy and a trusted Host header. Never expose the bundled development server as production infrastructure. Python describes [wsgiref as a reference implementation, not recommended for production](https://docs.python.org/3/library/wsgiref.html). [SQLite parameter binding and transactions](https://docs.python.org/3/library/sqlite3.html) are used for content storage.

The alpha has no general login/session framework, payments, general ORM, multi-tenant CMS, queues, WebSocket/ASGI, native GUI/mobile compiler or horizontally distributed data store. Generic API routes are public unless the host supplies its own authorization layer; the CMS token protects only the administrative API. The built-in server is single-process development tooling, and VM budgets are not OS isolation. Production readiness must be assessed for each application.
