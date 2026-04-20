# warning-agent local autopilot active plan

- status: `active-machine-pack`
- source_pack: `warning-agent-warning-plane-production-stability-2026-04-20`
- mirror_last_updated: `2026-04-20`

## Goal

- enable `pi-sdk` local autopilot to read/write repo-local active control-plane truth for the warning-plane production-stability workstream
- keep the runnable machine truth aligned with the richer source pack while the repo advances toward `Gemma4 26B resident local-primary + Neko GPT-5.4 xhigh cloud-fallback` production-operable stable output inside the current architecture boundary

## In Scope

- repo-local active pack files under `docs/plan/active_*`
- current active slice `PS.RV1`
- queued PS slices through `PS.RV1`
- deterministic local autopilot writeback compatibility for the production-stability pack

## Non-Goals

- replacing the richer source pack
- bypassing the `pi-sdk` local dirty-repo initial-run guard
- widening product scope beyond the current warning-plane / triage / investigation architecture boundary

## Verification Ladder

1. targeted control-plane compatibility tests
2. active slice targeted validation
3. benchmark / smoke proofs when the current slice requires them
4. `uv run pytest`
5. `uv run ruff check app tests scripts`

## Slice Definitions

#### `PS.S1a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `highest`

目标：

- freeze the model-role split and resident runtime contract before runtime implementation starts
- make `Gemma4 26B resident local-primary` and `Neko GPT-5.4 xhigh cloud-fallback` machine-readable

交付物：

1. explicit provider role split and readiness semantics
2. targeted proof for fallback-or-queue contract and operator-visible readiness truth

必须避免：

1. claiming live rollout complete before runtime proof exists
2. changing canonical runtime contracts in a contract-freeze slice

#### `PS.S1b`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- greatly expand local-primary budget for the 26B resident role
- align rollout evidence fields with the new model topology

交付物：

1. explicit high-budget local-primary contract
2. operator-visible evidence alignment for the new provider split

必须避免：

1. sneaking runtime lifecycle implementation into a budget-contract slice
2. leaving downstream slices with budget ambiguity

#### `PS.S2a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- materialize the Gemma4 26B resident local-primary lifecycle
- keep warning-agent on a no-cold-start normal path for 3.6 calls

交付物：

1. boot-prewarm-once and resident-service semantics
2. 3.6-only invocation path with ready/not-ready truth

必须避免：

1. turning warning-agent into a full model-serving platform
2. exposing per-warning cold-start as the normal path

#### `PS.S2b`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- define and land local not-ready -> fallback or queue behavior
- keep the abnormal path machine-readable and operator-visible

交付物：

1. explicit fallback-or-queue runtime policy
2. targeted proof for queue-wait and degraded fallback behavior

必须避免：

1. hidden blocking behavior when the resident model is unavailable
2. turning queue semantics into generic workflow orchestration

#### `PS.S2c`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- convert cloud fallback to the Neko GPT-5.4 xhigh identity and bounded adapter path
- preserve compressed handoff semantics and sparse fallback behavior

交付物：

1. cloud fallback model/runtime contract for Neko GPT-5.4 xhigh
2. targeted bounded handoff proof

必须避免：

1. making cloud the default investigation plane
2. widening into generic multi-provider SDK work

#### `PS.S2d`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- re-anchor the `3.5 -> 3.6` gates under the new model split
- make invocation/fallback/queue-wait/latency behavior measurable

交付物：

1. benchmark-backed stability gates
2. targeted proof for degraded validity and latency budgets

必须避免：

1. hand-waving stability without measurable evidence
2. rewriting first-pass into a prompt-heavy system

#### `PS.S3a`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- update warning-plane governance for the new resident-local / fallback / queue-wait topology
- keep ingress, queue, delivery, and feedback truth operator-visible

交付物：

1. governance contract updates for the new model topology
2. targeted queue/delivery/feedback/readiness proof

必须避免：

1. turning the repo into a deployment/orchestration platform
2. hiding operational semantics only in prose

#### `PS.S3b`

- Owner: `execute-plan`
- State: `READY`
- Priority: `high`

目标：

- assemble the end-to-end production evidence pack and operator runbook
- make the current model topology claim auditable without session memory

交付物：

1. end-to-end evidence pack for the new topology
2. operator runbook for enable/disable/rollback/triage

必须避免：

1. claiming beyond the current evidence boundary
2. leaving operational procedure only in conversation context

#### `PS.RV1`

- Owner: `execution-reality-audit`
- State: `READY`
- Priority: `high`

目标：

- run an evidence-driven audit against the production-stability claim
- freeze honest residuals and successor routing after execution closes

交付物：

1. audit verdict for the current architecture boundary
2. residual freeze and successor handoff note

必须避免：

1. claiming production-ready completion without audit-grade evidence
2. reopening earlier PS slices unless the audit proves real drift
