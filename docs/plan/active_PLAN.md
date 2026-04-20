# warning-agent local autopilot active plan

- status: `terminal-machine-pack`
- source_pack: `warning-agent-minimax-local-primary-real-adapter-2026-04-20`
- mirror_last_updated: `2026-04-20`

## Goal

- enable `pi-sdk` local autopilot to read/write repo-local active control-plane truth for the bounded Minimax/local-primary real-adapter workstream
- keep the runnable machine truth aligned with the richer source pack now that the repo has progressed from `MM.S1a` to terminal `MM.RV1`

## In Scope

- repo-local active pack files under `docs/plan/active_*`
- current terminal slice `MM.RV1`
- queued MM slices through `MM.RV1`
- deterministic local autopilot writeback compatibility for the bounded local-primary real-adapter pack

## Non-Goals

- replacing the richer source pack
- bypassing the `pi-sdk` local dirty-repo initial-run guard
- widening product scope beyond the bounded `3.6 local_primary real adapter` seam

## Verification Ladder

1. targeted control-plane compatibility tests
2. active slice targeted validation
3. `uv run pytest`
4. `uv run ruff check app tests scripts`

## Slice Definitions

#### `MM.S1a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `highest`

目标：

- freeze the local-primary real-adapter boundary and API-key semantics for the Minimax/Neko path
- keep downstream adapter/client work free from env-contract ambiguity

交付物：

1. explicit endpoint / model / optional api-key contract for local-primary real adapter
2. targeted boundary proof for `smoke_default / missing_env / ready`

必须避免：

1. implementing the runtime client before the boundary contract is frozen
2. hardcoding vendor-specific env semantics outside the local-primary boundary

#### `MM.S1b`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- add a bounded OpenAI-compatible local-primary provider client
- keep the adapter surface limited to `InvestigationRequest -> InvestigationResult`

交付物：

1. new local-primary OpenAI-compatible adapter module
2. schema-valid adapter unit proof

必须避免：

1. turning the adapter into a generic SDK platform
2. expanding beyond the single local-primary seam

#### `MM.S2a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- auto-wire the real local-primary provider when gate=`ready`
- preserve fake-provider injection for tests while enabling runtime auto-build

交付物：

1. local-primary/runtime auto-wiring path
2. targeted runtime proof for ready-gate execution

必须避免：

1. changing analyzer/router/report contracts
2. touching cloud fallback rollout while landing local-primary wiring

#### `MM.S2b`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- close the bounded integration with targeted verification and optional env-opt smoke
- keep default validation independent from a live endpoint

交付物：

1. targeted tests for missing env / missing client / ready path / runtime path
2. optional env-opt smoke surface or runbook note

必须避免：

1. making live endpoint access a mandatory default gate
2. claiming broader rollout readiness from this bounded adapter proof alone

#### `MM.RV1`

- Owner: `execution-reality-audit`
- State: `READY`
- Priority: `high`

目标：

- run an evidence-driven audit against the landed Minimax/local-primary seam
- freeze honest residuals and successor routing after execution closes

交付物：

1. audit verdict for the bounded adapter integration
2. residual freeze and successor handoff note

必须避免：

1. claiming production-ready model rollout without audit-grade evidence
2. reopening earlier MM slices unless the audit proves real drift
