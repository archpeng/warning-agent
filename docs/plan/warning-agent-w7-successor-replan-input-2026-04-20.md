# warning-agent W7 successor replan input

- status: `replan-input`
- predecessor_plan: `warning-agent-production-integration-bridge-2026-04-20`
- predecessor_closeout: `docs/plan/warning-agent-production-integration-bridge-2026-04-20_CLOSEOUT.md`
- generated_at: `2026-04-20`
- owner: `plan-creator`

## 1. What W6 proved

W6 已证明：

- external outcome admission baseline 已落地
- first vendor delivery seam 已落地为 env-gated bridge
- provider real-adapter contract + runtime gate 已落地
- operator-visible rollout evidence baseline 已覆盖新的 external surfaces

## 2. What W6 did not claim

W6 **没有**证明：

- production-ready rollout completed
- multi-environment secret / auth / deployment governance ready
- remote vendor credential rollout ready
- provider serving / client governance beyond local proof ready

## 3. Recommended W7 theme

建议把 W7 定义为：

> `rollout governance and environment-specific hardening for the already-landed W6 integration bridge`

## 4. Candidate waves

### wave-1 / external admission governance

候选 slice：

- auth / caller contract hardening for `/outcome/admit`
- admission policy / queue boundary if external producers multiply
- durable operator identity / provenance truth

### wave-2 / delivery rollout governance

候选 slice：

- credential / secret handling policy for `adapter-feishu`
- remote rollout policy and fail-closed governance
- operator-facing rollout checklist for vendor bridge enablement

### wave-3 / provider rollout governance

候选 slice：

- local_primary real adapter enablement policy beyond env-only proof
- cloud_fallback real adapter runtime governance and failure policy
- serving / client lifecycle contract for real provider rollout

### wave-4 / successor audit

候选 slice：

- reality audit for any new live rollout claims
- residual freeze for post-rollout feedback compounding work

## 5. Governing evidence to carry forward

- `docs/warning-agent-integration-rollout-evidence.md`
- `docs/warning-agent-provider-boundary.md`
- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_CLOSEOUT.md`
- `docs/plan/README.md`
- current repo surfaces:
  - `app/integration_evidence.py`
  - `app/feedback/outcome_api.py`
  - `app/delivery/*`
  - `app/investigator/provider_boundary.py`
  - `app/runtime_entry.py`

## 6. Non-goals for W7 planning

- do not reopen W6 just to restate already-landed bridge truth
- do not claim production rollout complete before new evidence exists
- do not collapse auth / credential / deployment / provider governance into one oversized slice
