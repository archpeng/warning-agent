# warning-agent local autopilot active plan

- status: `active-machine-pack`
- source_pack: `warning-agent-production-integration-bridge-2026-04-20`
- mirror_last_updated: `2026-04-20`

## Goal

- enable `pi-sdk` local autopilot to read/write repo-local active control-plane truth for the current W6 bridge workstream
- keep the runnable machine truth aligned with the richer W6 source pack while the repo progresses from `W6.S4a` to `W6.RV1`

## In Scope

- repo-local active pack files under `docs/plan/active_*`
- current active slice `W6.S4a`
- immediate successor slice `W6.RV1`
- deterministic local autopilot writeback compatibility

## Non-Goals

- replacing the richer W6 source pack
- bypassing the `pi-sdk` local dirty-repo initial-run guard
- widening product scope beyond the current W6 bridge and review boundary

## Verification Ladder

1. targeted control-plane compatibility tests
2. `uv run pytest`
3. `uv run ruff check app tests scripts`

## Slice Definitions

#### `W6.S4a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `highest`

目标：

- materialize operator-visible rollout evidence for the landed external integration surfaces
- keep webhook/runtime proof surfaces aligned with the real delivery env gate and provider runtime gate truth

交付物：

1. operator-visible health/readiness/evidence baseline for outcome admission, delivery env gate, and provider runtime gate
2. machine-readable closeout evidence that can be carried into `W6.RV1`

必须避免：

1. multi-environment deployment platform drift
2. secret-manager or remote rollout expansion
3. observability-suite broadening beyond the current W6 boundary

#### `W6.RV1`

- Owner: `execution-reality-audit`
- State: `READY`
- Priority: `high`

目标：

- run an evidence-driven W6 reality audit against the landed external integration bridge
- freeze honest residuals and W7 replan inputs after W6 execution completes

交付物：

1. reality audit verdict for W6
2. residual freeze and W7 replan input

必须避免：

1. claiming production-ready rollout without evidence
2. reopening earlier W6 execution slices unless the audit proves a real drift
