# Contributing

Run `python3 -m unittest discover -s tests -v` and `python3 benchmarks/run.py` before proposing a change. Tests use deterministic providers and a loopback HTTP fixture; they need no cloud keys or model download.

Submit a small issue or pull request with the behavior, an executable SHIN example, compatibility impact and tests. Changes to permissions, untrusted values or budgets also need an update to SECURITY.md. Never add real prompts, credentials, user records or private source to fixtures.

Prefer standard-library implementations. Keep language semantics separate from model adapters. Performance claims need reproducible measurements, clear environments and identical workloads. Alpha syntax may change; update examples and both README files when it does.
