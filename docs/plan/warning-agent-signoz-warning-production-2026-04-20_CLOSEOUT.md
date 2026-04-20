# warning-agent signoz warning production closeout

- plan_id: `warning-agent-signoz-warning-production-2026-04-20`
- closeout_date: `2026-04-20`
- verdict: `accept_with_residuals`
- next_handoff: `plan-creator`

## 1. Scope audited

审计对象：`W7 signoz warning production`

claimed outcomes：

- governed Signoz warning ingress 已真实落地为 dedicated route，而不是 fixture-only runtime path
- accepted warnings 已具备 durable raw / normalized / receipt / provenance truth
- duplicate firing、worker retry、dead-letter 边界 已变成 machine-readable queue truth
- admitted warnings 已稳定复用 current canonical runtime spine，而不是长出第二套 analyzer / investigator
- partial evidence、delivery status、investigation stage、human review requirement 已具备 machine-readable processing result truth
- `/readyz` 已覆盖 ingress auth、queue/backlog/failure/deferred/fallback operator truth
- W7 remaining residuals 已可诚实冻结到 successor planning，而无需继续混在 W7 execution 中

## 2. Findings

### confirmed

1. governed Signoz ingress truth 已真实落地：
   - `app.receiver.signoz_ingress` 提供 `/webhook/signoz`
   - explicit `accepted / rejected / deferred` receipt contract 已存在
   - caller header + shared-token auth contract 已通过 targeted tests 固定
2. durable admission truth 已真实落地：
   - accepted warning 现在会持久化 raw payload、normalized alert、admission receipt、provenance truth
   - `app.storage.signoz_warning_store` 为 warning-plane 提供 durable artifact + index truth
3. queue / dedupe / worker boundary 已真实落地：
   - deterministic dedupe key 已 materialize
   - queue state 已显式区分 `pending / processing / completed / failed / dead_letter / deduped`
   - worker retry / backoff / dead-letter 行为已有 direct proof
4. admitted warning -> canonical runtime spine 已真实落地：
   - worker path 复用 `build_signoz_first_evidence_bundle(...)` + `execute_runtime_inputs(...)`
   - packet / decision / optional investigation / report 仍沿用当前 canonical contract
5. non-happy-path truth 已真实落地：
   - processing result 现在显式记录 `evidence_state`、`delivery_status`、`investigation_stage`、`human_review_required`
   - worker failure 现在留下 structured queue error truth，而不是 silent loss
6. operator readiness truth 已真实落地：
   - `/readyz` 现在返回 `signoz_warning_plane`
   - ingress auth state、queue backlog、delivery deferred count、cloud fallback ratio 都已 operator-visible
7. full regression / hygiene 通过：
   - `uv run pytest` → `174 passed`
   - `uv run ruff check app tests scripts` → pass

### drift fixed

1. predecessor drift：Signoz-first runtime 之前只能通过 CLI / smoke materialize，缺 dedicated governed ingress route。
2. predecessor drift：accepted warning 之前没有 durable raw / normalized / receipt / provenance truth。
3. predecessor drift：duplicate firing / worker retry / dead-letter 之前没有 queue-level machine truth。
4. predecessor drift：`/readyz` 之前只覆盖 outcome / delivery / provider gate，不覆盖 warning-plane ingress / queue truth。

### uncertain

none remaining inside current W7 scope.

## 3. Evidence added / reused

### targeted tests

- `uv run pytest tests/test_signoz_alert_receiver.py tests/test_signoz_ingress_api.py tests/test_signoz_admission_storage.py tests/test_signoz_queue_contract.py tests/test_signoz_worker_runtime.py tests/test_signoz_warning_readiness.py tests/test_alertmanager_webhook.py tests/test_integration_evidence.py tests/test_live_signoz_runtime.py`
- `uv run pytest tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py`

### direct proof

- dedicated governed ingress now returns explicit receipt state and caller provenance without synchronous runtime execution
- accepted warning now lands durable artifacts under `data/signoz_warnings/<warning_id>/`
- duplicate ingress now lands as `deduped` queue truth rather than silent replay
- worker proof confirmed both:
  - `failed -> retry -> completed`
  - `failed -> dead_letter`
- `/readyz` now surfaces warning-plane queue metrics and ingress auth state directly

### full gates

- `uv run pytest` → `174 passed`
- `uv run ruff check app tests scripts` → pass

## 4. Fixes landed during W7

- dedicated governed Signoz ingress route
- durable warning admission storage and provenance truth
- deterministic dedupe key and queue ledger
- worker retry / backoff / dead-letter boundary
- admitted-warning runtime bridge to canonical packet/analyzer/investigation/report spine
- machine-readable processing result truth for partial evidence / delivery / human review state
- operator-visible readiness truth for ingress / queue / backlog / deferred / fallback
- terminal source + machine control-plane updates for W7 closeout

## 5. Successor residuals / W8 replan input

1. current ingress auth is still minimal shared-token env gating；尚未进入 multi-env secret rotation / signature governance。
2. current queue / worker 仍是 repo-local sqlite + file truth；尚未进入 scaled retention / replay / lease governance。
3. current delivery policy on real admitted warnings 仍需要更强的 operator controls、destination policy、environment-specific hardening。
4. repo 现在可以诚实声称：
   - `governed Signoz warning plane landed`
   - **not** `production-ready rollout completed`

W8 successor focus 应收敛为：

- ingress auth / secret / provenance hardening by environment
- queue retention / replay / operator control / scale governance
- delivery policy hardening on real admitted warnings
- feedback compounding on durable production warning truth

具体 replan 输入见：

- `docs/plan/warning-agent-w8-successor-replan-input-2026-04-20.md`

## 6. Closeout verdict

`W7` 可以 honest closeout 为 `completed`，并带 successor residuals。

理由：

- W7 plan 中定义的 governed ingress、durable admission、queue/worker boundary、runtime handoff、operator readiness 都已被代码、tests、artifacts、queue truth、readiness truth 共同支撑。
- 当前 scope 内已无未证实 claim。
- remaining residuals 都属于 successor hardening / scale / environment governance，而不是 W7 implementation 未闭合。

## 7. Successor handoff

- 当前停止在 `closeout / replan` boundary。
- 若继续推进，必须进入 successor planning；不得继续在 W7 pack 内混做 W8。
