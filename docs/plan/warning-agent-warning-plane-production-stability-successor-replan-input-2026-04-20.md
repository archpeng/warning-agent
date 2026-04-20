# warning-agent warning-plane production stability successor replan input

- predecessor_plan: `warning-agent-warning-plane-production-stability-2026-04-20`
- predecessor_closeout: `docs/plan/warning-agent-warning-plane-production-stability-2026-04-20_CLOSEOUT.md`
- generated_at: `2026-04-20`
- intended_handoff: `plan-creator`

## 1. What is already closed

The current pack already landed, with evidence:

- resident `local_primary` lifecycle truth
- explicit direct-fallback / warning-worker-recovery-wait abnormal-path policy
- bounded auto-built cloud fallback real-adapter path
- benchmark-backed `3.5 -> 3.6` stability gates inside the current repo boundary
- operator-visible queue / delivery / feedback governance
- production-stability runbook + rollout evidence pack

## 2. Residuals that were intentionally not claimed as closed

1. real external live rollout proof for local resident serving and cloud vendor path
2. multi-environment secret / auth / provenance hardening
3. distributed queue / lease / replay / retention control plane
4. broader external serving / orchestration platform work

## 3. Honest next-pack candidates

### candidate A — external live rollout evidence pack

Use when the next goal is to prove real environments rather than repo-local stable semantics.

Focus:

- real Gemma4 resident endpoint smoke / latency / recovery proof
- real Neko GPT-5.4 xhigh bounded handoff proof
- environment-scoped auth / secret checks
- operator-grade rollback drill evidence

### candidate B — warning-plane operational hardening

Use when the next goal is to strengthen retention / replay / queue operations without widening product scope.

Focus:

- queue retention / replay controls
- dead-letter remediation procedures
- delivery destination policy hardening
- stronger operator controls around recovery wait and fallback pressure

### candidate C — infra-boundary expansion

Use only if the work truly needs external serving/orchestration infrastructure.

Focus:

- external model-serving control plane
- distributed queue / lease manager
- environment-aware orchestration

This must be treated as a new boundary, not a continuation of the closed pack.

## 4. Replan guardrails

The successor must continue to preserve:

- canonical contracts unchanged
- local-first topology by default
- bounded evidence only
- fail-closed over pretend-live
- no generic multi-provider SDK / workflow-engine / orchestration-platform creep unless that is the explicit new boundary
