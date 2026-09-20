# Contributing to SHIN

[日本語](CONTRIBUTING.ja.md) · [Discussions](https://github.com/ohayoo37/shin-lang/discussions) · [Issues](https://github.com/ohayoo37/shin-lang/issues) · [Governance](GOVERNANCE.md)

Everyone is welcome to help: report a reproducible bug, improve documentation, translate the website, build examples, review a proposal, or contribute code. You do not need to be an expert or obtain permission to fork SHIN. Follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Find a place to start

- Use Discussions for questions, early ideas and showing what you built. English and Japanese are welcome; other languages are welcome too, though maintainers may need translation help.
- Use Issues for reproducible bugs and concrete improvements. Search existing issues first. A minimal example is more useful than a large project archive.
- Look for `good first issue` or `help wanted` labels when available. You can also propose a small documentation or translation fix directly; an issue is not required.
- For language semantics, new dependencies, native runtimes or security boundaries, discuss the design before investing in a large implementation. Include compatibility impact and an executable example.
- Report vulnerabilities privately through [Security → Report a vulnerability](https://github.com/ohayoo37/shin-lang/security/advisories/new), not a public issue. See [SECURITY.md](SECURITY.md).

## Your first pull request

1. Fork the repository on GitHub and clone your fork. Create a branch from current `main`.
2. Make one focused change. Explain the problem, resulting behavior and compatibility impact. Add a regression test for a behavior change; prose-only corrections do not require new tests.
3. Run the relevant checks below and record their results in the pull request. Update related examples and documentation if behavior changes.
4. Push the branch to your fork and open a pull request against `ohayoo37/shin-lang:main`. Draft pull requests are welcome for work in progress.
5. Respond to review feedback. A maintainer reviews and merges accepted changes; CI success alone does not imply acceptance.

Python 3.9+ and Git are sufficient to run from source. No third-party runtime packages, cloud credentials or downloaded models are needed for the tests.

```sh
python3 -m unittest discover -s tests -v
python3 -m shin check examples/ai.shin
python3 tools/build_site.py --check
python3 tools/build_playground.py --check
```

For runtime or compiler performance changes, also run `python3 benchmarks/run.py` and report the environment, identical workloads and before/after measurements. For packaging changes, run `python3 tools/build_release.py` and exercise the resulting zipapp. CI checks Python 3.9, 3.11 and 3.13.

## Website translations

Edit `docs/i18n/<locale>.json`, then run `python3 tools/build_site.py` and commit both the dictionary and generated pages. Keep the same keys as `en.json`, preserve technical limitations, and check narrow-screen layouts and links. To add a language, extend `LOCALES` in the generator and provide a complete dictionary. Native-speaker corrections are especially welcome. Do not edit generated homepages directly.

## Engineering expectations

Prefer the Python standard library. Keep language semantics separate from model adapters. Changes to permissions, untrusted values or execution budgets need boundary tests and an update to SECURITY.md. Performance claims need reproducible evidence. Alpha syntax may change; update examples and both README files when it does.

Never put credentials, real private prompts, user records or confidential source in issues, patches or fixtures. Review any AI-assisted contribution yourself; explain and test its behavior as you would any other contribution.

Contributions are accepted under the repository's existing MIT license. Preserve applicable copyright and license notices. Submit only material you have the right to contribute; no separate CLA is required by this project.

Review is voluntary and no response time is guaranteed. For current decision-making and maintainer responsibilities, see [GOVERNANCE.md](GOVERNANCE.md).

Browser runtime changes: regenerate `runtime.json` with `python3 tools/build_playground.py`. See [playground architecture](docs/playground/README.md) for the trust boundary and browser checks.
