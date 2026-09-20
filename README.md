# SHIN

[**Try SHIN in your browser**](https://ohayoo37.github.io/shin-lang/playground/) · [Install on Windows, macOS or Linux](https://ohayoo37.github.io/shin-lang/start/)

The playground runs the actual Python reference VM locally through Pyodide. No account or API key; demo model calls only echo text. Browser runtime assets download from jsDelivr on first run.

**Flexible thinking. Explicit authority.**

An experimental language for websites, web applications, CMS and AI workflows: a small compiler, a dedicated stack VM, explicit model capabilities, and validation boundaries for model output. Version **0.2.0a2** is a working reference implementation, not a production sandbox or a native-performance claim.

[日本語](README.ja.md) · [Website](https://ohayoo37.github.io/shin-lang/) · [Language reference](docs/language.md) · [Security model](SECURITY.md) · [Roadmap](docs/roadmap.md)

```text
permit model "demo";
budget steps = 1000;

fn answer(prompt) {
    let draft = infer("demo", prompt);
    return check_text(draft, 200);
}

print(answer("Ideas can be flexible. Permissions should be explicit."));
```

## Try it in a minute

Python 3.9+ is required. Running from this checkout uses **zero third-party runtime packages**. The demo provider echoes text; it does not pretend to be an LLM.

```sh
git clone https://github.com/ohayoo37/shin-lang.git
cd shin-lang
python3 -m shin run examples/hello.shin
python3 -m shin run examples/functions.shin
python3 -m shin run examples/ai.shin --allow-model demo
python3 -m shin run examples/structured.shin --allow-model demo
python3 -m shin run examples/input.shin --input examples/input.json
```

Without `--allow-model demo`, the AI example is rejected **before execution**. Source permission alone cannot grant host authority.

Optional installation in a virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
shin --version
```

The install uses setuptools as a build dependency. No package has been published to PyPI; install from this repository or its release archive.

## Build a website, app, API or CMS

```sh
python3 -m shin init my-site --template website
python3 -m shin serve my-site --port 8000
```

Open `http://127.0.0.1:8000`. Choose `--template app`, `api` or `cms` for other starters. The new web toolkit includes routing, escaped HTML fragments, JSON responses, static assets, static site export, and an opt-in SQLite CMS editor with drafts and publication. [Web/CMS guide](docs/web.md) · [Generated website demo](https://ohayoo37.github.io/shin-lang/demo/) · [Example projects](examples/).

This alpha targets websites and browser/server applications. It does not compile native mobile/desktop apps. The included server is development-only; production hosting, authentication for your own API routes and operational controls remain the host's responsibility.

## What works

- Own lexer and compiler → SHIN bytecode → stack VM. No translation through Python `eval` or `exec`.
- Functions, recursion, lexical block scopes, rebinding, `if` / `else`, `while`, short-circuit booleans.
- Numbers, UTF-8 strings, arrays, records, indexing, and immutable collection operations.
- Static model-effect inventory, including effects inside unused functions; host grant checked before execution and again at the call.
- Untrusted model/input wrappers; `check_text` and exact-key `check_json` validation.
- Instruction, call-depth, value-size, cumulative logical-allocation, output, and cooperative wall-time budgets.
- Explicit host model configuration: deterministic mock and loopback Ollama adapters.
- `check`, `disasm`, and `run --stats` commands, regression tests, and a reproducible microbenchmark.

## Connect a local model

Start your own Ollama server and install a model separately. Replace `your-installed-model` in `examples/models.json` with its installed name, then run:

```sh
python3 -m shin run examples/ollama.shin \
  --model-config examples/models.json --allow-model assistant
```

The adapter implements [Ollama's `/api/generate` API](https://docs.ollama.com/api/generate), requests a non-streaming response and up to 256 output tokens. Only explicit numeric loopback HTTP origins are supported in this release. Redirects and environment proxies are disabled. The 5-second default wall budget requires a warm, responsive model; cold startup may time out. The model server is a separately trusted process, with its own resource and network behavior.

The adapter's HTTP contract is tested against a local fixture server. Actual model quality and live Ollama inference were **not** validated for this release. Cloud providers, GPU execution, batch scheduling and parallel tasks are not implemented.

## Check and inspect

```sh
python3 -m shin check examples/ai.shin
python3 -m shin disasm examples/functions.shin
python3 -m shin run examples/functions.shin --stats
python3 -m unittest discover -s tests -v
python3 benchmarks/run.py
```

`check` verifies syntax, named function calls and declared model effects. It is **not** a static type or definite-assignment checker. Runtime checks enforce value operations and trust boundaries.

## Performance, honestly

The Python reference VM is slower than native Python on the included sum-loop benchmark. The checked-in [measurement](benchmarks/reference.json) compares the same 1,000-iteration loop, reports compile and execution time separately, and includes the environment and seven-run median. It excludes startup and AI inference. Runtime source size is reported in the benchmark, excluding Python itself; this is **not** a standalone executable size or a memory-footprint measurement.

Our next performance milestone is a compatible native/Wasm runtime with measured parity and a differential test suite. No speedup, memory-safety proof, prompt-injection immunity or universal novelty is claimed.

## Contribute

SHIN is open source under the [MIT license](LICENSE). Code, translations, documentation, examples, bug reports and reviews are welcome, including first-time contributions.

- [Contribution guide](CONTRIBUTING.md) · [日本語の参加ガイド](CONTRIBUTING.ja.md)
- [Ask questions and discuss ideas](https://github.com/ohayoo37/shin-lang/discussions)
- [Report a bug or propose an improvement](https://github.com/ohayoo37/shin-lang/issues/new/choose)
- [Governance and review decisions](GOVERNANCE.md) · [Code of Conduct](CODE_OF_CONDUCT.md)

Fork the repository and submit a pull request; accepted changes enter the official version after maintainer review. Report vulnerabilities through the [private security channel](https://github.com/ohayoo37/shin-lang/security/advisories/new).

## Website languages

[English](https://ohayoo37.github.io/shin-lang/en/) · [日本語](https://ohayoo37.github.io/shin-lang/ja/) · [Español](https://ohayoo37.github.io/shin-lang/es/) · [Français](https://ohayoo37.github.io/shin-lang/fr/) · [Deutsch](https://ohayoo37.github.io/shin-lang/de/) · [Português](https://ohayoo37.github.io/shin-lang/pt-BR/) · [简体中文](https://ohayoo37.github.io/shin-lang/zh-CN/) · [한국어](https://ohayoo37.github.io/shin-lang/ko/)

The public website is available in eight languages. Technical documentation is available in English, with a Japanese README. The website starter and public demo use English; the app and CMS editor interfaces currently use Japanese. Edit `docs/i18n/*.json` and run `python3 tools/build_site.py` to update the public pages.
