# Browser playground architecture

The playground executes the unchanged Python compiler and VM from `shin/` in a dedicated Web Worker using pinned Pyodide 0.27.7. It is not a native SHIN/Wasm backend. [Pyodide worker documentation](https://pyodide.org/en/0.27.7/usage/webworker.html).

`python3 tools/build_playground.py` builds `runtime.json` from four reference-runtime modules, the fixed `bridge.py`, and the MIT license. Commit the generated bundle. CI checks synchronization with `--check`; the adapter and examples are tested by `tests/test_playground.py`.

Only trusted bundled Python is passed to `runPython`. User source is serialized as JSON, assigned as data, then passed to SHIN's `compile_source`. Each request creates a fresh VM. No user-selected Python modules, network adapters, content stores or arbitrary URLs are exposed. The only model is an explicitly granted text echo. Output and diagnostics are inserted with `textContent`, never HTML.

Execution limits: 64 KiB source, 50,000 instructions, 1 s cooperative VM time, 8 KiB output, 32 KiB values, 1 MiB cumulative logical allocation. These are logical limits, not process-memory guarantees. A 5 s main-thread watchdog terminates the worker; loading has a separate 60 s timeout. Stop also terminates it, and the next run creates a new one.

The first run loads the pinned Python runtime from jsDelivr. GitHub Pages and the CDN receive ordinary asset requests; SHIN source, input and output are not uploaded. No analytics, accounts, persistent source storage or user-code sharing is implemented. Share links identify bundled examples only. Browser memory/resource limits and the trusted dependency chain still apply.

To preview: `python3 -m http.server 8774 --directory docs`, then open `/playground/`. Check success, missing grant, unchecked output, malformed JSON, budget exhaustion, Stop/restart and load failures. External CDN availability is needed on first load. The interface supports English and Japanese; the eight-language marketing site links to it.
