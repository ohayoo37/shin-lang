# SHIN 0.2 language reference

UTF-8 source, `.shin` extension, `//` comments, semicolon-terminated simple statements. ASCII identifiers; JSON-style double-quoted strings. Whitespace is insignificant. This is a dynamically checked language; static type inference is not implemented.

## Grammar sketch

```text
program   = (permit | budget | function | statement)*
permit    = "permit" "model" STRING ";"
budget    = "budget" NAME "=" INTEGER ";"
function  = "fn" NAME "(" parameters? ")" block
block     = "{" statement* "}"
statement = "let" NAME "=" expression ";"
          | NAME "=" expression ";"
          | "if" expression block ("else" block)?
          | "while" expression block
          | "return" expression? ";"
          | expression ";"
```

Functions are top-level, named, fixed arity, support recursion, and return `null` when reaching the end. Calls may precede definitions. There are no closures, first-class functions, imports, exceptions or mutable object fields. Blocks introduce lexical scopes. `let` cannot redeclare a name in the same scope. Assignment finds the nearest local binding; a function can read globals but cannot assign them.

## Values and operators

Values: `null`, `true`, `false`, signed-64-bit-range integers, finite binary64 numbers, strings, arrays (`[1,2]`) and string-keyed records (`{"name":"SHIN"}`). Arrays and records may be heterogeneous. Duplicate literal record keys fail compilation. Operations reject unexpected types; booleans are not numbers.

Operator precedence, lowest first: `||`, `&&`, `== !=`, `< <= > >=`, `+ -`, `* / %`, unary `! -`, indexing. Logical operators short-circuit and require booleans. Conditions require booleans. Ordering and arithmetic require numbers; `+` also concatenates two strings or two arrays. `/` returns a float; `%` follows Python remainder semantics. Equality compares values with matching outer types; numeric `1 == 1.0` is false. Collections use recursive, type-sensitive structural equality.

Indexing requires a present record key or an integer in `[0, length)` for arrays/strings. Negative indices are forbidden. Strings are indexed by Unicode code point, not grapheme. `push` returns a new array; original values are unchanged.

## Builtins

| Call | Behavior |
|---|---|
| `print(value)` | Print validated data; non-string values use compact JSON; returns null |
| `len(value)` | Text code points, array elements or record keys |
| `str(value)` | Text unchanged, otherwise compact JSON |
| `json(value)` | Compact JSON, including quotes around text |
| `push(array, value)` | New array with appended validated value |
| `keys(record)` | Keys in insertion order |
| `assert(boolean)` | Abort if false |
| `input()` | Host's selected JSON input, wrapped as untrusted JSON text; default null |
| `infer("alias", prompt)` | Host-configured model; literal alias, validated text prompt; returns Untrusted text |
| `check_text(untrusted, max_chars)` | Require nonempty text within a positive character limit; return ordinary text |
| `check_json(untrusted, schema)` | Require a JSON object with exactly schema keys and matching top-level types |

Schema types: `"text"`, `"number"`, `"boolean"`, `"array"`, `"record"`. Booleans do not pass number validation. Duplicate keys, nonstandard numbers, nonfinite values and excessive nesting are rejected. Validate value ranges with `assert`. Structural validation does not establish factual truth or grant permissions.

## Capabilities and budgets

`permit model "alias";` declares potential authority. The host must independently pass `--allow-model alias` and configure the alias. All `infer` expressions are conservatively included in the effect inventory, even in unreachable code. A computed model name is a compilation error. Model aliases are capability names, not downloadable model identifiers.

`budget steps = 1000;` lowers a default ceiling. Supported budgets are `steps` (100000), `depth` (64), `value_bytes` (65536), `allocation_bytes` (8388608), `output_bytes` (65536), `wall_ms` (5000). A source program cannot raise these. Refer to SECURITY.md for accounting and timing limits. Budget exhaustion is a diagnostic with exit status 1; output already emitted is not rolled back.

## CLI and embedding

- `python3 -m shin run file.shin [--allow-model alias] [--model-config config.json] [--input input.json] [--stats]`
- `python3 -m shin check file.shin`: syntax, named-call and effect checks only, no execution.
- `python3 -m shin disasm file.shin`: print generated instructions. No bytecode deserialization is exposed.

```python
from shin import compile_source, VM
program = compile_source('print(2 + 3);')
assert VM(program).run() == ['5']
```

Host adapter call signature: `callback(prompt: str, timeout_seconds: float, max_response_bytes: int) -> str`. Adapters are trusted Python code. The callback must honor its timeout, avoid retaining private data unnecessarily and return bounded UTF-8 text. A VM instance is intended for a single run.


## Web toolkit additions (0.2)

See [Web/CMS reference](web.md) for `init`, `serve`, `build`, `token`, route manifests and deployment boundaries. New builtins: `html(literal, bindings)`, `html_join(fragments)`, `link(url, text)`, `url_part(text)`, `respond(status, body)`, `get(record,key,default)`, `is_number(value)`, `content_list("literal-collection")`, `content_get("literal-collection",slug)`. `HTML` is an opaque fragment type that can be passed, stored and combined through these builtins; it is not an ordinary string. HTML values cannot be JSON-serialized. Collection operations preserve existing trust checks.

`permit content "pages";` declares read access to published content. This requires a matching host grant and configured content store, separate from model grants. The compiler's content effect inventory is conservative like its model inventory. HTTP request data and content results are Untrusted; use `check_json` to validate structure before using values. Exact fields are documented in web.md. No database write capability is exposed to SHIN code.
