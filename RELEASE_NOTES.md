# SHIN 0.1.0-alpha.1

The first executable reference release of **SHIN / 芯**: an experimental AI-workflow language built around explicit authority and checked model output.

Includes a compiler and bytecode VM, functions/recursion, block scopes, arrays/records, model-effect checks, execution budgets, mock and loopback Ollama adapters, CLI, examples, Japanese/English guides, and 48 tests.

Download `shin-0.1.0a1.pyz` and run it with Python 3.9+:

```sh
python3 shin-0.1.0a1.pyz --version
python3 shin-0.1.0a1.pyz run your-program.shin
```

The `.pyz` bundles only SHIN; it is not a standalone native binary. `SHA256SUMS` contains the artifact checksum. Source archives include examples and tests. Package version: `0.1.0a1`. MIT license.

This is an alpha, not a production sandbox. The Python reference VM is slower than Python on the included sum-loop benchmark. Native/Wasm execution, static typing, parallel scheduling and OS isolation are future work. Ollama's protocol is fixture-tested; live model inference and quality were not tested for this release. See SECURITY.md and benchmarks/reference.json for precise limits and measurements.
