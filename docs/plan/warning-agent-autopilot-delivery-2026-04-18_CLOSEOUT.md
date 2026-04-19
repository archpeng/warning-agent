# warning-agent autopilot delivery closeout

- plan_id: `warning-agent-autopilot-delivery-2026-04-18`
- status: `completed`
- completed_at: `2026-04-19`
- boundary: `P5 cloud fallback only`

## 1. Closeout verdict

本 master plan 已在当前边界内完成。

已完成的 phase：

- `P1` repo bootstrap + contract materialization
- `P2` deterministic packet/report baseline
- `P3` local analyzer baseline
- `P4` single investigator interface, local-first
- `P5` cloud fallback only

本次 closeout 采用 recovery-carrying 路径完成：

- `P4 recovery` 已把 local-primary invocation rate 恢复到 gate 内
- `P5 recovery` 已把 cloud trigger / policy materialize 到 runtime path，并补齐 benchmark evidence

## 2. Final delivered runtime path

```text
alert
  -> bounded evidence collection
  -> incident packet
  -> local retrieval + local analyzer
  -> optional investigator (default local-first)
  -> optional cloud fallback
  -> markdown alert report
```

当前 cloud fallback truth：

- cloud 不是默认审查平面
- cloud 只消费 compressed handoff + bounded refs
- cloud unavailable 时仍可回退到 schema-valid local investigation result
- Markdown report 在 local/cloud 两种调查结果下都可稳定渲染

## 3. Final evidence snapshot

### P4 baseline
- artifact: `data/benchmarks/local-primary-baseline-summary.json`
- accepted: `true`
- key metrics:
  - `local_primary_invocation_rate = 0.2`
  - `routing_label_alignment_rate = 1.0`
  - `structured_completeness_rate = 1.0`
  - `degraded_fallback_validity_rate = 1.0`

### P5 baseline
- artifact: `data/benchmarks/cloud-fallback-baseline-summary.json`
- accepted: `true`
- key metrics:
  - `cloud_fallback_rate_total = 0.0`
  - `cloud_fallback_rate_investigated = 0.0`
  - `cloud_fallback_p95_wall_time_sec = 0.0`
  - `compressed_handoff_p95_tokens = 0.0`
  - `final_investigation_schema_validity_rate = 1.0`
  - `cloud_unavailable_fallback_report_success_rate = 1.0`

### Validation ladder executed
- `uv run pytest tests/test_investigation_runtime.py tests/test_investigator_router.py tests/test_configs.py`
- `uv run python scripts/run_local_primary_benchmark.py`
- `uv run pytest tests/test_cloud_benchmark.py tests/test_investigation_runtime.py tests/test_cloud_fallback.py tests/test_investigator_router.py tests/test_configs.py`
- `uv run python scripts/run_cloud_fallback_benchmark.py`
- `uv run pytest`
- `uv run ruff check app tests scripts`

## 4. Residuals carried after closeout

这些 residual **不阻塞当前 master plan closeout**，但若继续推进必须显式 replan：

1. topology / owner / repo mapping source-of-truth 仍未冻结
2. Alertmanager webhook 真实输入路径仍未在真实环境验证
3. cloud benchmark corpus 当前是 zero-cloud baseline；runtime cloud correctness 依赖 targeted routing / failure smoke tests 与 deterministic fixture proof

## 5. Future work requires explicit replan

以下内容不在本次 master plan 默认继续范围内：

- shadow-mode hardening
- rollout / soak / runbook 扩张
- local small model replacement

如需继续，必须新开 plan。

## 6. One-line summary

`warning-agent` 现已在当前主计划边界内完成一个可运行、可回放、可 benchmark 的 local-first + bounded cloud-fallback warning agent baseline。
