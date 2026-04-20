# warning-agent W8 successor replan input

- status: `replan-input`
- predecessor_plan: `warning-agent-signoz-warning-production-2026-04-20`
- predecessor_closeout: `docs/plan/warning-agent-signoz-warning-production-2026-04-20_CLOSEOUT.md`
- generated_at: `2026-04-20`
- owner: `plan-creator`

## 1. What W7 proved

W7 已证明：

- Signoz warning 现在可以通过 governed ingress route 进入 `warning-agent`
- accepted warnings 现在会留下 durable raw / normalized / receipt / provenance truth
- duplicate firing、worker retry、dead-letter 现在都有 machine-readable queue truth
- admitted warnings 现在会稳定进入 current canonical runtime spine
- operator 现在可以从 `/readyz` 直接看到 ingress / queue / backlog / deferred / fallback truth

## 2. What W7 did not claim

W7 **没有**证明：

- production-ready rollout completed
- multi-environment ingress auth / secret / signature governance ready
- scaled queue retention / replay / lease governance ready
- real admitted-warning delivery policy fully hardened for production use
- post-incident feedback compounding on real production warning corpus fully ready

## 3. Recommended W8 theme

建议把 W8 定义为：

> `environment-specific hardening and operator controls for the landed Signoz warning plane`

## 4. Candidate waves

### wave-1 / ingress auth and provenance hardening

候选 slice：

- ingress auth 从单 shared-token env 升级到更明确的 secret / signature / rotation contract
- caller identity / provenance contract 按 environment 冻结
- fail-closed policy for auth drift / secret drift / caller drift

### wave-2 / queue governance and operator controls

候选 slice：

- queue retention / replay / operator requeue controls
- visibility for dead-letter triage and recovery
- stronger lease / retry / scale semantics if repo-local proof is no longer enough

### wave-3 / delivery and feedback hardening on real admitted warnings

候选 slice：

- production routing / destination policy on real admitted warnings
- environment-specific delivery fail-closed rules
- feedback / outcome compounding against durable warning corpus

### wave-4 / successor audit

候选 slice：

- reality audit for any new production-hardening claims
- residual freeze for post-hardening scaling or governance work

## 5. Governing evidence to carry forward

- `docs/warning-agent-integration-rollout-evidence.md`
- `docs/plan/warning-agent-signoz-warning-production-2026-04-20_CLOSEOUT.md`
- `docs/plan/README.md`
- current repo surfaces:
  - `app/receiver/signoz_ingress.py`
  - `app/receiver/signoz_queue.py`
  - `app/receiver/signoz_worker.py`
  - `app/storage/signoz_warning_store.py`
  - `app/integration_evidence.py`

## 6. Non-goals for W8 planning

- do not reopen W7 just to restate already-landed warning-plane truth
- do not claim production rollout complete before new environment / governance evidence exists
- do not collapse auth / secret / queue-scale / delivery-policy / feedback-compounding into one oversized slice
