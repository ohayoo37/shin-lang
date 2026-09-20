# Roadmap

The original direction is **AI freedom inside explicit authority**. The first release makes that idea executable. Milestones below are proposals, not implemented features or delivery promises.

| Stage | Deliverable | Evidence required |
|---|---|---|
| v0.1 alpha — implemented | Reference compiler/VM, capabilities, validation, budgets, CLI | Language and security regression tests; reproducible examples |
| v0.2 | Static types, definite assignment, typed schemas, source spans | Positive/negative language conformance suite |
| v0.3 | Effect-aware task graph, bounded concurrency, batching | Deterministic scheduling tests, cancellation and grant-propagation tests |
| v0.4 | Native/Wasm runtime and compact bytecode format | Differential tests against this reference; speed, RSS and startup measurements |
| Later | Scoped data capabilities, safe provider SDK, editor integration | Adversarial tests, independent review, explicit compatibility policy |

Do not add filesystem, shell or arbitrary network access as convenience builtins. Design the host capability boundary and revocation behavior first. Automatic caching of model responses must be opt-in and account for privacy, model identity and nondeterminism.

Performance priorities: avoid copying large values, bound temporary allocations, batch model calls only where semantics permit, and separate inference time from orchestration overhead. A language cannot remove the model's underlying computation merely by changing syntax.
