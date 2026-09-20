# SHIN 0.2.0-alpha.1 — Web, Apps & CMS

SHIN now supports server-rendered websites, browser applications, JSON APIs and a small persistent CMS.

- `shin init --template website|app|api|cms` creates runnable starter projects.
- A WSGI adapter maps literal/parameterized routes to SHIN functions, with fresh VM budgets per request.
- Literal HTML templates escape data; opaque HTML fragments, safe links and static CSS/JS assets support page composition.
- SQLite-backed Content Studio provides token-authenticated editing, drafts/publication and optimistic revision checks. SHIN's content capability can read only published records.
- `shin build` exports explicit HTML paths and assets to a new static directory, including subdirectory-hosting support.
- Tests cover API behavior, publication lifecycle, persistence, authentication, XSS escaping, origin/host checks, traversal, stale edits and static export. The browser CMS save/publish flow and estimate-app API were verified locally.

[Web/CMS guide](https://github.com/ohayoo37/shin-lang/blob/main/docs/web.md) · [Generated website demo](https://ohayoo37.github.io/shin-lang/demo/)

Download `shin-0.2.0a1.pyz` (Python 3.9+ required), then:

```sh
python3 shin-0.2.0a1.pyz init my-site --template website
python3 shin-0.2.0a1.pyz serve my-site
```

This remains an experimental Python reference implementation. The bundled server is for loopback development; production needs an appropriate WSGI host and operational/authentication controls. Native mobile/desktop builds, user accounts, payment processing, general ORM, multi-tenant CMS and OS isolation are not implemented. No speedup or production-security claim is made. `SHA256SUMS` verifies the release artifact. MIT licensed.
