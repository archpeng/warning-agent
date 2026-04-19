# warning-agent live-data MVP materialization status

- plan_id: `warning-agent-live-data-mvp-materialization-2026-04-19`
- plan_class: `execution-plan`
- status: `completed`
- current_wave: `closeout / live-data MVP complete`
- current_step: `closeout complete`
- last_updated: `2026-04-19`

## 1. Current truth

- live-data MVP pack 已完成并 closeout。
- closeout verdict：`accept_with_residuals`
- closeout doc：`docs/plan/warning-agent-live-data-mvp-materialization-2026-04-19_CLOSEOUT.md`
- post-closeout reality audit 已补充两类 proof：
  - live evidence bundle 的 failure-tolerant fallback 行为
  - live runtime path 在 investigation gate 命中时可进入 `local_primary` 并执行 bounded live follow-up

## 2. Recently completed

### `L1` — freeze real evidence query/config surface

landed truth：

- 新增 `configs/evidence.yaml`
- 新增 `app/collectors/evidence_bundle.py`
- 更新 `configs/services.yaml`
- 更新 `app/collectors/prometheus.py`
- 更新 `app/collectors/signoz.py`
- 新增 / 更新 collector/config tests

review verdict：
- `accept`

### `L2` — wire live evidence into runtime/webhook packet materialization

landed truth：

- `RuntimeEntrypoint` 现在显式支持 `evidence_source = fixture | live`
- `execute_runtime_entrypoint(...)` 现在支持 live collectors
- `build_webhook_receipt(...)` / `create_app(...)` 现在支持 live evidence mode
- 新增 `tests/test_live_runtime_entry.py`

review verdict：
- `accept`

### `L3` — make local-primary consume bounded live follow-up tools

landed truth：

- `BoundedInvestigatorTools` 现在支持：
  - `prometheus_query_scalar(...)`
  - `signoz_search_logs(...)`
  - `signoz_search_traces(...)`
- `LocalPrimaryInvestigator` 现在只对 explicit live refs 做 bounded Prometheus + SigNoz follow-up
- fixture packets 继续保持 deterministic / offline-safe
- 新增 `tests/test_live_investigation.py`

review verdict：
- `accept`

### `L4` — smoke, honest claim boundary, closeout

landed truth：

- 新增 `app/live_runtime_smoke.py`
- 新增 `scripts/run_live_runtime_smoke.py`
- 新增 `tests/test_live_runtime_smoke.py`
- 新增 `docs/warning-agent-live-data-mvp-runbook.md`
- 更新 `app/main.py`
- 更新 `tests/test_bootstrap.py`
- direct smoke executed:
  - `uv run python scripts/run_live_runtime_smoke.py`
  - result: `evidence_source = live`, runtime path succeeded, artifacts persisted

review verdict：
- `accept`

### `RV1` — reality audit + closeout

landed truth：

- 本 pack 已切到 terminal completed state
- runtime metadata 现为 terminal `phase = live-data-mvp`, `active_slice = none`

review verdict：
- `accept_with_residuals`

## 3. Next step

- 当前 pack 已完成
- 若要继续 external admission / richer live query tuning / rollout，必须新开 successor plan

## 4. Residuals / risks

1. 当前 `configs/evidence.yaml` 的 Prometheus query family 是 bounded config surface，不保证对所有真实环境即插即用；必要时需后续针对环境调优。
2. direct live smoke 在当前 checkout replay 上成功跑通 live packet -> analyzer -> report，但 investigation stage 为 `none`；这说明 live auto-analysis 已成立，bounded localization path 也已实现，但真实环境是否进入 investigation 仍取决于 live evidence signal 与 routing gates。
3. 当前仍是 MVP 级 try-run / demo 边界，不是 production rollout ready。

## 5. Gate state

| gate | state | evidence |
|---|---|---|
| L1 | pass | collector/config live evidence surface landed |
| L2 | pass | runtime/webhook fixture-vs-live mode landed |
| L3 | pass | bounded live follow-up landed |
| L4 | pass | smoke + runbook + claim boundary landed |
| RV1 | pass | reality audit complete |
| plan closeout | pass | `docs/plan/warning-agent-live-data-mvp-materialization-2026-04-19_CLOSEOUT.md` |

## 6. Latest evidence

- `uv run pytest tests/test_prometheus_collector.py tests/test_signoz_collector.py tests/test_live_evidence_bundle.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py tests/test_live_runtime_entry.py tests/test_investigator_tools.py tests/test_local_primary.py tests/test_investigation_runtime.py tests/test_live_investigation.py tests/test_live_runtime_smoke.py tests/test_bootstrap.py` → `36 passed`
- `uv run python scripts/run_live_runtime_smoke.py`
- `uv run pytest` → `99 passed`
- `uv run ruff check app tests scripts` → pass
