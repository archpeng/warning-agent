# warning-agent local autopilot active plan

- status: `active-machine-pack`
- source_pack: `warning-agent-signoz-warning-production-2026-04-20`
- mirror_last_updated: `2026-04-20`

## Goal

- enable `pi-sdk` local autopilot to read/write repo-local active control-plane truth for the closed W7 Signoz warning production workstream
- keep the runnable machine truth aligned with the richer W7 source pack at terminal slice `W7.RV1`

## In Scope

- repo-local active pack files under `docs/plan/active_*`
- terminal closeout slice `W7.RV1`
- preceding operator-governance slice `W7.S4a`
- deterministic local autopilot writeback compatibility for the terminal W7 pack

## Non-Goals

- replacing the richer W7 source pack
- bypassing the `pi-sdk` local dirty-repo initial-run guard
- widening product scope beyond W7 closeout and successor handoff truth

## Verification Ladder

1. targeted control-plane compatibility tests
2. closeout / reality-audit validation
3. `uv run pytest`
4. `uv run ruff check app tests scripts`

## Slice Definitions

#### `W7.S4a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- expose operator-visible ingress / queue / backlog / deferred / fallback truth for the new warning plane
- freeze a rollout checklist that remains honest about current readiness

交付物：

1. readiness / checklist surface for warning-plane governance
2. direct operator-visible proof for queue and ingress gate truth

必须避免：

1. reporting only service liveness while hiding warning-plane backlog or failure truth
2. claiming production-ready rollout before audit evidence exists

#### `W7.RV1`

- Owner: `execution-reality-audit`
- State: `READY`
- Priority: `highest`

目标：

- run an evidence-driven W7 reality audit against the landed warning-plane work
- freeze honest residuals and successor replan inputs after W7 execution closes

交付物：

1. W7 audit verdict
2. residual freeze and successor replan input

必须避免：

1. claiming production-ready rollout without audit-grade evidence
2. reopening earlier W7 slices unless the audit proves real drift
