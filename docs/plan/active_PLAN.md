# warning-agent local autopilot active plan

- status: `active-machine-pack`
- source_pack: `warning-agent-architecture-clarity-optimization-2026-04-20`
- mirror_last_updated: `2026-04-20`

## Goal

- enable `pi-sdk` local autopilot to read/write repo-local active control-plane truth for the architecture-clarity optimization workstream
- keep the runnable machine truth aligned with the richer source pack while the repo performs bounded code-architecture clarity optimization with `3.5` / `3.6` as the primary focus
- prepare the smallest safe groundwork for `docs/future/warning-agent-3.5-3.6-learning-optimization-minimal-engineering.md` without widening product scope or overengineering the repo

## In Scope

- repo-local active pack files under `docs/plan/active_*`
- current active slice `AC.RV1`
- queued AC slices through `AC.RV1`
- deterministic local autopilot writeback compatibility for the architecture-clarity pack
- terminal closeout truth and successor routing after architecture-clarity completion

## Non-Goals

- replacing the richer source pack
- bypassing the `pi-sdk` local dirty-repo initial-run guard
- changing canonical contracts or current provider topology inside the planning pack itself
- widening into `warning-core`, generic policy framework, or platform work

## Verification Ladder

1. targeted control-plane compatibility tests
2. active slice targeted validation
3. relevant analyzer / investigator targeted tests for the current slice
4. `uv run pytest`
5. `uv run ruff check app tests scripts`

## Slice Definitions

#### `AC.S1a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `highest`

目标：

- freeze architecture-clarity guardrails before code motion starts
- make the hotspot/seam inventory for `3.5` and `3.6` explicit and operator-readable

交付物：

1. explicit no-overengineering and protected-surface truth
2. hotspot / seam map for later `3.5` / `3.6` refactor slices

必须避免：

1. starting broad refactor before the boundary is frozen
2. inventing generic `app/state/*` or `app/policies/*` trees in a design slice

#### `AC.S1b`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- convert current dependency/import concerns into an explicit move map
- separate runtime ownership from benchmark/training ownership at the planning boundary

交付物：

1. dependency hygiene target map
2. runtime-vs-benchmark ownership inventory

必须避免：

1. silently turning the inventory slice into full refactor
2. leaving move targets ambiguous for execute-plan

#### `AC.S2a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- clean up `3.5` runtime vs training/benchmark boundaries
- keep `local-analyzer-decision.v1` and analyzer behavior stable while structure gets clearer

交付物：

1. clearer analyzer module ownership
2. passing targeted analyzer + benchmark proofs

必须避免：

1. changing external decision semantics
2. mixing structural cleanup with unrelated scorer redesign

#### `AC.S2b`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- add minimal `3.5` assist/audit groundwork
- prepare future-note internal objects without growing a new runtime layer

交付物：

1. narrow assist/audit internal seams
2. targeted proof that canonical analyzer output remains unchanged

必须避免：

1. turning `3.5` into a second chat-agent system
2. introducing online-learning semantics

#### `AC.S3a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- split `3.6` local-primary internals by responsibility
- isolate resident lifecycle, abnormal-path policy, and provider materialization seams

交付物：

1. clearer local-primary internal modules or ownership slices
2. targeted runtime/local tests proving semantics still hold

必须避免：

1. changing current resident/fallback semantics
2. implying external serving-platform work is now required

#### `AC.S3b`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- split `3.6` cloud-fallback internals by responsibility
- isolate handoff/compression, guard logic, transport, and response mapping

交付物：

1. clearer cloud-fallback internal seams
2. targeted cloud/runtime proofs still passing

必须避免：

1. turning cloud into the default investigation plane
2. widening into generic vendor SDK work

#### `AC.S3c`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- reduce execution-spine cross-layer coupling
- clean up normalized-alert / packet / runtime glue directions

交付物：

1. narrower import directions across packet / receiver / runtime
2. passing runtime/receiver/bootstrap proofs

必须避免：

1. bundling unrelated product behavior changes
2. leaving the runtime spine harder to reason about than before

#### `AC.S4a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- land the smallest future-note groundwork that supports later learning optimization
- align docs/benchmarks/runbook with the clarified module boundaries

交付物：

1. minimal internal learning objects / seams for `3.6`
2. aligned docs and benchmark surfaces

必须避免：

1. introducing a heavy state/policy framework
2. claiming learning-loop completion in a groundwork slice

#### `AC.RV1`

- Owner: `execution-reality-audit`
- State: `READY`
- Priority: `high`

目标：

- audit whether the architecture became clearer without overengineering drift
- freeze honest residuals and successor routing after the clarity pack closes

交付物：

1. architecture-clarity audit verdict
2. residual freeze and successor handoff note

必须避免：

1. claiming clarity uplift without proof-carrying evidence
2. smuggling unlanded future-learning ambitions into closeout truth
