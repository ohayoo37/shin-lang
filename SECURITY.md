# Security model — experimental v0.2

SHIN is an execution-policy experiment, **not an OS security boundary**. Do not run hostile programs in a process that holds valuable secrets. Deploy untrusted workloads in an independently restricted process/container with OS CPU, memory, network and filesystem controls.

## Trust boundaries

1. SHIN source is parsed into our own instructions; it cannot request Python imports, attributes, shell execution, filesystem access or arbitrary URLs.
2. Every `infer` call has a literal model alias. All calls, including unused functions, contribute to the compiled effect set. Missing source declarations fail compilation. Missing host grants/configuration fail before any instruction runs. Calls check grants again.
3. Model results and host JSON input are `Untrusted` values. They may be passed to functions or stored in containers, but printing, arithmetic, conditions and serialization reject them recursively. `check_text` validates nonempty text and character length. `check_json` validates exact keys and top-level field types; it is not full JSON Schema. Array/record schema fields do not recursively validate element semantics.
4. Validation is structural, not factual, authorization-related or prompt-injection detection. Approved model endpoints still receive supplied prompts. The language cannot constrain what an external model server does with its own credentials, tools or network access.
5. Model adapters, Python embedding code, compiled Program objects, Python itself and the host OS are trusted. Passing hostile callbacks or tampering with in-memory bytecode is outside the boundary.

## Limits

- Source and host input/config files: 64 KiB each; parsed value nesting: 32.
- VM defaults: 100,000 instructions; 64 nested calls; 64 KiB logical value size; 8 MiB cumulative logical allocations; 64 KiB output; 5,000 ms cooperative elapsed time.
- Program and host limits can lower defaults, never raise them. Logical allocation conservatively counts many values multiple times; it is not Python RSS or GPU memory. Compilation is bounded by source size/Python recursion diagnostics, not VM instruction budgets.
- Blocking host functions are trusted to honor their timeout. VM wall checks happen at instruction boundaries and after model calls; they cannot forcibly interrupt a host callback. urllib socket timeouts are not hard end-to-end deadlines against a slow-drip server. Use a supervisor for hard deadlines.
- The supplied Ollama adapter ignores environment proxies, rejects redirects, accepts only numeric loopback HTTP origins, bounds response bytes and caps requested output tokens. It never downloads or starts models. A granted local service remains trusted; loopback does not imply that its downstream behavior is safe.
- Collections are immutable language values. `push` returns a new array. There are no cyclic values or references to Python objects in the language.
- The CLI escapes terminal control characters in program output. Embedders must apply output encoding appropriate to their UI. Printed strings are not HTML-safe, shell-safe or database-safe merely because they passed `check_text`.

## Reporting

Use the repository's **Security → Report a vulnerability** private channel when enabled. If unavailable, open an issue asking for a private contact without including exploit details or secrets. Only the latest alpha is maintained. There has been no independent security audit.

## Web/CMS additions in 0.2

HTTP input and published CMS records enter the VM as Untrusted JSON. HTML templates must be literals, use a tag/attribute allowlist and interpolate only text-node values. Scalars are escaped; HTML fragments are opaque language values. Static external scripts under `/assets/` are host-authored trusted code. Source-defined arbitrary HTML strings are returned as plain text, not HTML.

Every HTTP request creates a fresh VM. The WSGI host must explicitly allow its public hostnames; dev mode binds 127.0.0.1 only. Built-in content administration requires an explicit random token file and checks Bearer credentials on every data read/write. No default token, cookie session, CORS, or browser token persistence is provided. The public content capability reads published records only. SQLite queries use bound parameters and updates require the current revision. A shared admin token is not a complete account/role/audit system.

The WSGI response adds CSP, nosniff, frame denial, no-referrer and no-store. Static exports do not carry HTTP headers; configure security headers on their host. Host headers and Origin are checked; missing Origin is allowed for non-browser clients but does not bypass administrative Bearer authentication. This is not a rate-limiting or DDoS defense. The bundled wsgiref server is development-only. Limit concurrent requests, CPU, RAM and request duration in your production host. Applications, static JS assets, manifest files and the selected content database are trusted host inputs. Do not serve user-uploaded files as public JS.

Public JSON endpoints do not acquire user authentication automatically. Add a host-side auth layer before using them for sensitive application data. Administrative actions are not available as SHIN source builtins. Media uploads, file deletion, general SQL execution, multi-tenancy and user account management are outside this alpha.
