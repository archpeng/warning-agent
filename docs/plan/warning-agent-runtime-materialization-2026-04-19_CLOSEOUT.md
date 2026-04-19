# warning-agent runtime materialization closeout

- plan_id: `warning-agent-runtime-materialization-2026-04-19`
- closeout_date: `2026-04-19`
- verdict: `accept_with_residuals`
- next_handoff: `plan-creator`

## 1. Scope audited

审计对象：`W2 runtime materialization baseline`

claimed outcomes：

- replay-first entrypoint 已成为正式 runtime path
- packet / decision / investigation / report 会被活路径真实生成
- artifacts / metadata / retrieval 已形成最小 write/read loop
- local-primary 不再是 zero-tool smoke provider
- webhook-stub 具备 operator-facing runtime receipt

## 2. Findings

### confirmed

1. `app/main.py` 已不再是 bootstrap-only banner；`warning-agent replay <fixture-path>` 可真实 materialize replay runtime。
2. `app/runtime_entry.py` 已把 replay path 接成正式活路径，并写入：
   - JSONL artifacts
   - `MetadataStore`
   - `RetrievalIndex`
3. `app/receiver/alertmanager_webhook.py` 已从单纯 normalize stub 升级为 operator-facing runtime receipt path；webhook receipt 现包含 runtime ids，并会触发活路径 persistence / retrieval refresh。
4. `LocalPrimaryInvestigator` 已真实消费 bounded `repo_search` tool；`analysis_updates.notes` 与 benchmark metrics 已体现 live tool usage。
5. local-primary benchmark 重新验证通过，且保持历史 gate：
   - `accepted_local_primary_baseline = true`
   - `local_primary_invocation_rate = 0.2`
   - `routing_label_alignment_rate = 1.0`
   - `average_tool_calls_per_investigation = 1.0`

### drift

none within W2 scope.

### uncertain

none remaining for W2 closeout；当前 residuals 均已清晰落到 W3/W4 planning boundary。

## 3. Evidence added / reused

### targeted evidence

- `uv run pytest tests/test_runtime_entry.py tests/test_bootstrap.py tests/test_artifact_store.py`
- `uv run pytest tests/test_runtime_entry.py tests/test_bootstrap.py tests/test_sqlite_store.py tests/test_retrieval.py`
- `uv run pytest tests/test_local_primary.py tests/test_investigation_runtime.py tests/test_investigator_tools.py`
- `uv run pytest tests/test_local_primary.py tests/test_cloud_fallback.py tests/test_markdown_builder.py tests/test_investigator_benchmark.py`
- `uv run pytest tests/test_alertmanager_webhook.py tests/test_bootstrap.py tests/test_runtime_entry.py`
- `uv run python scripts/run_local_primary_benchmark.py`

### full gates

- `uv run pytest` → `61 passed`
- `uv run ruff check app tests scripts` → pass

### direct probes

- `WARNING_AGENT_DATA_DIR=$(mktemp -d) uv run python -m app.main replay fixtures/replay/manual-replay.checkout.high-error-rate.json`
- webhook probe via `TestClient(create_app(repo_root=..., data_root=tmp))` returned runtime receipt with:
  - `packet_id = ipk_checkout_post_api_pay_20260418t120008z`
  - `decision_id = lad_checkout_post_pay_20260418t120010z`
  - `investigation_stage = cloud_fallback`
  - `report_id = rpt_checkout_post_api_pay_20260418t120008z`

## 4. Fixes landed during W2

- replay-first runtime entrypoint skeleton
- replay execution path materialization
- artifact writeback materialization
- metadata + retrieval wiring
- local-primary tool contract wiring
- live tool-driven local-primary proof
- operator-facing webhook runtime receipt path

## 5. Successor residuals

1. `W3` local trust upgrade is still required:
   - learned scorer / calibration surface absent
   - packet temporal context v2 absent
   - temporal robustness benchmark surface absent
   - richer routing / handoff corpora still below future planning minima
2. `W4` learning loop remains future work:
   - `app/feedback/outcome_ingest.py` 不存在
   - retrieval refresh / outcome compounding loop 未 materialize
3. real environment Alertmanager webhook path remains unverified outside stub/replay surface.

## 6. Closeout verdict

`W2` can be honestly closed as `completed` with successor residuals.

理由：

- W2 scope 的 runtime glue 已被代码、tests、benchmark、和 direct probes 共同支撑。
- W2 stop boundary 内未留未证实 claim。
- 剩余缺口均属于后继 wave（`W3/W4`）而非 W2 未闭合。

## 7. Successor handoff

新控制面动作：

- `plan-creator` 生成 `W3 local trust upgrade` 的新 `PLAN / STATUS / WORKSET`
- handoff only；不得直接 claim `W3` execution 已开始
