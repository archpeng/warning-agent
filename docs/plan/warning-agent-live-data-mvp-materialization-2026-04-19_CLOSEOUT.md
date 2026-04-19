# warning-agent live-data MVP materialization closeout

- plan_id: `warning-agent-live-data-mvp-materialization-2026-04-19`
- closeout_date: `2026-04-19`
- verdict: `accept_with_residuals`
- next_handoff: `replan-required`

## 1. Scope audited

审计对象：`warning-agent live-data MVP materialization`

claimed outcomes：

- live evidence query/config surface 已冻结
- runtime / webhook live packet materialization 已落地
- local-primary bounded live follow-up 已落地
- live smoke / honest claim boundary / terminal sync 已落地

## 2. Findings

### confirmed

1. live evidence query/config surface 已真实 materialize：
   - `configs/evidence.yaml`
   - `app/collectors/evidence_bundle.py`
   - `PrometheusCollector.instant_scalar_query(...)`
   - `SignozCollector.search_logs(...)`
   - `SignozCollector.search_traces(...)`
2. runtime / webhook live mode 已真实 materialize：
   - `RuntimeEntrypoint.evidence_source = fixture | live`
   - `execute_runtime_entrypoint(..., evidence_source="live")`
   - `build_webhook_receipt(..., evidence_source="live")`
3. local-primary bounded live follow-up 已真实 materialize：
   - `BoundedInvestigatorTools.prometheus_query_scalar(...)`
   - `BoundedInvestigatorTools.signoz_search_logs(...)`
   - `BoundedInvestigatorTools.signoz_search_traces(...)`
   - `LocalPrimaryInvestigator` 只对 explicit live refs 做 bounded follow-up
4. live smoke path 已真实 materialize：
   - `app/live_runtime_smoke.py`
   - `scripts/run_live_runtime_smoke.py`
5. honest claim boundary 已写入：
   - `docs/warning-agent-live-data-mvp-runbook.md`
6. runtime metadata drift 已修正：
   - `app.main.get_app_metadata()` -> `phase = live-data-mvp`, `active_slice = none`
7. full regression 通过：
   - `uv run pytest` → `99 passed`
   - `uv run ruff check app tests scripts` → pass
8. post-closeout reality audit 已补充 proof：
   - `tests/test_live_evidence_bundle.py` 现在显式证明 collector failure 时 packet-compatible bundle 仍可 fallback materialize
   - `tests/test_live_runtime_entry.py` 现在显式证明 live runtime path 在 investigation gate 命中时可进入 `local_primary` 并执行 bounded live follow-up

### direct smoke reality

`uv run python scripts/run_live_runtime_smoke.py` 已成功跑通当前真实 collector surface：

- `evidence_source = live`
- packet / decision / report 正常生成并落盘
- 本次 checkout replay 结果为：`investigation_stage = none`

这说明：

- live auto-analysis 已在当前真实接口上成立
- bounded localization path 已在代码和 tests 中成立
- 但当前真实 checkout smoke 并未跨过 investigation gate，因此不能把这次 smoke 说成“真实环境已验证 live localization 总会触发”

### drift fixed

1. 当前 repo 已不再只依赖 `fixtures/evidence/*.json` 作为唯一 packet evidence source。
2. local-primary 已不再只能做 `repo_search`；对于 live refs，现可做 bounded Prometheus + SigNoz follow-up。

### uncertain

none remaining inside current MVP pack scope.

## 3. Evidence added / reused

### targeted evidence

- `uv run pytest tests/test_prometheus_collector.py tests/test_signoz_collector.py tests/test_live_evidence_bundle.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py tests/test_live_runtime_entry.py tests/test_investigator_tools.py tests/test_local_primary.py tests/test_investigation_runtime.py tests/test_live_investigation.py tests/test_live_runtime_smoke.py tests/test_bootstrap.py` → `36 passed`

### direct smoke evidence

- `uv run python scripts/run_live_runtime_smoke.py`

### full gates

- `uv run pytest` → `99 passed`
- `uv run ruff check app tests scripts` → pass

## 4. Fixes landed during this pack

- live evidence config freeze
- live evidence bundle builder
- runtime/webhook fixture-vs-live mode
- bounded live investigation follow-up
- live smoke script + runbook
- runtime metadata terminal sync

## 5. Successor residuals

1. current `configs/evidence.yaml` 仍是 bounded config surface；若要让 Prometheus query family 更贴近真实环境，需要后续环境调优。
2. current direct live smoke on checkout replay reached live auto-analysis but not investigation; if the next goal is to prove real-world live localization on current infra, that requires richer signal/query tuning or a stronger real case.
3. external admission、production rollout、multi-env rollout governance 仍不在当前 MVP pack 范围内。

## 6. Closeout verdict

本 pack 可以 honest closeout 为 `completed`，并带 successor residuals。

理由：

- 当前计划要求的 live evidence surface、runtime live mode、bounded live follow-up、live smoke、honest claim docs 已全部有代码、tests、脚本与 control-plane 共同支撑。
- 当前 scope 内已无未证实 claim。
- 剩余缺口均属于 successor work，而不是本 pack 未闭合 implementation。

## 7. Successor handoff

- 当前停止在 `review / replan` boundary。
- 若要继续做 real-world live localization proof、external admission、production rollout 或更强 live signal tuning，必须新开 successor `PLAN / STATUS / WORKSET`。
