# warning-agent signoz-first warning plane plan

- plan_id: `warning-agent-signoz-first-warning-plane-2026-04-19`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- predecessor_plan: `warning-agent-live-data-mvp-materialization-2026-04-19`
- last_updated: `2026-04-19`

## 1. Goal

把 `warning-agent` 从当前的 `Prometheus + SigNoz mixed live evidence MVP`，重构为一个明确的 **SigNoz-first warning plane**：

```text
SigNoz alert
  -> normalized warning input
  -> SigNoz-first evidence bundle
  -> incident packet
  -> local analyzer / routing
  -> bounded live investigation
  -> final markdown report
```

并明确把 Prometheus 降级为：

```text
optional infra corroboration only
```

## 2. Hard freeze policy

### 2.1 Prometheus freeze

本 pack 生效后，以下事项全部冻结，不做推进：

- 不新增任何 Prometheus query family 作为主能力目标
- 不新增任何 Prometheus-first severity feature
- 不新增任何 Prometheus-first investigation path
- 不把 Prometheus 作为 primary warning input
- 不为更多服务扩写 Prometheus config surface

允许的仅限：

- compatibility / bugfix
- 保持现有 smoke / tests 可运行
- 作为 optional infra corroboration 继续被读取

### 2.2 Scope consequence

这意味着当前 `configs/evidence.yaml` 中已有的 Prometheus query surface，只作为 frozen baseline 存在；
本 pack 不再围绕它扩写、调优、拓展或作为核心判级路径推进。

## 3. Why this successor exists

当前 repo 已完成 live-data MVP，但现实证据表明：

- 当前生产 SigNoz 已具备真实 alert / traces / top operations 能力
- 当前 Prometheus 在真实环境中更像 infra proxy / corroboration，而不是业务预警真相
- 当前 warning-agent 还没有充分利用：
  - SigNoz alert rule payload
  - SigNoz trace hierarchy / status codes / downstream target
  - SigNoz operation-level error count / call count / p95 / p99
- 当前 live runtime 仍容易停在 `packet -> decision -> report`，没有稳定进入 investigation

因此本 pack 的核心不是“继续完善 Prometheus live evidence”，而是：

> 把 warning-agent 的 primary warning truth 改成 SigNoz。

## 4. Scope

### in scope

- SigNoz alert 作为 primary input
- SigNoz traces / top operations / trace details 作为 primary severity evidence
- SigNoz trace hierarchy / downstream target / status code 作为 investigation evidence
- Prometheus 只保留 infra corroboration
- runtime / webhook / smoke / report / docs 全面转成 Signoz-first truth

### out of scope

- production rollout / admission / multi-env orchestration
- Prometheus query family 扩展
- large-scale model retraining beyond what the Signoz-first contract strictly needs
- unlimited observability exploration
- changing cloud fallback scope

## 5. Deliverables

1. **Signoz-first input contract**
   - 新增 Signoz alert normalization surface
   - packet candidate source 明确支持 `signoz_alert`
2. **Signoz-first evidence bundle**
   - Signoz alert + traces + top ops 直接组成 packet-compatible bundle
   - Prometheus 仅补 infra corroboration
3. **Signoz-first severity + routing**
   - analyzer / routing 主要吃 Signoz evidence
   - 不再要求 Prometheus 主导 severity
4. **Signoz-first investigation**
   - local-primary 主要吃 trace details / top ops / logs-by-trace
5. **Signoz-first report + smoke + docs**
   - 真实 Signoz alert -> report 跑通
   - 边界 / honest claim 写清楚

## 6. Verification ladder

1. targeted unit / contract tests
2. targeted runtime / investigation integration tests
3. direct Signoz-first smoke against current real SigNoz surface
4. `uv run pytest`
5. `uv run ruff check app tests scripts`

## 7. Execution outline

| Slice | Summary | Primary outcome |
|---|---|---|
| `S1` | freeze Prometheus role + freeze Signoz-first contracts | no more Prometheus-driven planning ambiguity |
| `S2` | Signoz alert -> evidence bundle materialization | packet truth no longer depends on Prometheus as primary source |
| `S3` | Signoz-first analyzer + routing | severity / investigation decision driven mainly by Signoz |
| `S4` | Signoz-first investigation + report | investigation and final report cite Signoz evidence as primary truth |
| `S5` | runtime/webhook/smoke/closeout | end-to-end Signoz-first path and honest closeout |

## 8. Detailed implementation checklist

### `S1` — freeze Prometheus role + Signoz-first contracts

**Files / surfaces**
- `app/packet/contracts.py`
- `app/receiver/alertmanager_webhook.py`
- `app/receiver/signoz_alert.py` (new)
- `docs/warning-agent-live-data-mvp-runbook.md`
- `docs/warning-agent-signoz-first-runbook.md` (new)
- `tests/test_signoz_alert_receiver.py` (new)
- `tests/test_packet_builder.py`

**Change / add functions**
- `app.packet.contracts.CandidateSource`
  - add `signoz_alert`
- `app.receiver.signoz_alert.normalize_signoz_alert_payload(payload)`
  - input: raw SigNoz alert rule / firing payload
  - output: normalized warning input compatible with packet builder
- `app.receiver.signoz_alert.extract_signoz_alert_refs(payload)`
  - input: raw SigNoz alert payload
  - output: alert metadata refs such as `rule_id`, `service`, `endpoint`, `window`, `query source`
- `app.receiver.alertmanager_webhook.normalize_alertmanager_payload(...)`
  - keep for compatibility, but document it is not the primary future input

**Minimal tests**
- Signoz alert payload normalizes into `service / operation / alertname / candidate_source=signoz_alert`
- packet builder accepts normalized Signoz alert source without Prometheus-first assumptions
- runbook freeze text explicitly states Prometheus is corroboration only

**done_when**
- Signoz alert has a stable normalized input contract
- Prometheus freeze policy is written into repo docs / plan truth
- `execute-plan` can start implementation without ambiguity about source priority

**stop boundary**
- do not yet change analyzer weights
- do not yet implement live Signoz runtime path

---

### `S2` — Signoz alert -> evidence bundle materialization

**Files / surfaces**
- `app/collectors/evidence_bundle.py`
- `app/collectors/signoz.py`
- `configs/evidence.yaml`
- `configs/services.yaml`
- `app/packet/contracts.py`
- `tests/test_signoz_collector.py`
- `tests/test_live_evidence_bundle.py`
- `tests/test_signoz_primary_bundle.py` (new)

**Change / add functions**
- `app.collectors.evidence_bundle.build_signoz_first_evidence_bundle(normalized_alert, ...)`
  - input: normalized Signoz alert + Signoz collector + optional Prometheus collector
  - output: packet-compatible evidence bundle where Signoz fields are required and Prometheus fields optional
- `app.collectors.evidence_bundle.build_prometheus_corroboration(normalized_alert, ...)`
  - input: normalized warning input + optional Prometheus collector
  - output: infra corroboration only; may return all-`None` metrics without failing bundle build
- `app.collectors.signoz.get_trace_details(trace_id, *, time_range="30m")`
  - input: trace id
  - output: full trace hierarchy / spans / downstream targets
- `app.collectors.signoz.search_logs_by_trace_id(trace_id, *, limit=...)` or equivalent generic wrapper
  - input: trace id
  - output: correlated log rows if available

**Minimal tests**
- Signoz-first bundle materializes with Prometheus fully absent / all-`None`
- bundle captures top ops / trace ids / trace error ratio / alert refs / downstream span hints
- trace detail parsing works for current raw SigNoz payload shape

**done_when**
- packet-compatible bundle can be built from Signoz alone
- Prometheus is optional corroboration, not required input truth
- current real SigNoz sample service can build non-fallback Signoz evidence beyond just `service + summary`

**stop boundary**
- do not yet change analyzer scoring rules

---

### `S3` — Signoz-first analyzer + routing

**Files / surfaces**
- `app/analyzer/base.py`
- `app/analyzer/fast_scorer.py`
- `app/analyzer/trained_scorer.py`
- `app/analyzer/calibrate.py`
- `configs/thresholds.yaml`
- `tests/test_fast_scorer.py`
- `tests/test_trained_scorer.py`
- `tests/test_live_runtime_entry.py`
- `tests/test_signoz_first_routing.py` (new)

**Change / add functions**
- `app.analyzer.base.extract_features(packet, retrieval_hits)`
  - input: Signoz-first packet
  - output: feature vector whose primary severity signals come from Signoz alert / traces / top ops
- `app.analyzer.fast_scorer._severity_score(features)`
  - output: severity no longer mainly anchored on Prometheus deltas
- `app.analyzer.fast_scorer._reason_codes(...)`
  - include Signoz-first reasons such as high error ratio / 5xx endpoint / hot failing dependency
- `app.analyzer.calibrate.decide_investigation(...)`
  - primary triggers come from Signoz alert and trace evidence
- `app.analyzer.trained_scorer.score_packet(...)`
  - preserve hybrid path, but ensure Signoz-first packet can cross severity / investigation gates without Prometheus primary metrics

**Minimal tests**
- live-like Signoz alert + top operations can produce non-`P4` severity when current error evidence is strong, even if trace ids are absent in the current live probe window
- live-like Signoz alert + traces can produce non-`P4` severity when current error evidence is strong
- route plan enters investigation on Signoz-primary evidence even when Prometheus corroboration is missing / weak
- Prometheus corroboration may refine confidence but does not decide the route alone

**done_when**
- severity / routing truth is Signoz-first
- current real-case scaffolds can honestly enter investigation when Signoz evidence is strong enough

**stop boundary**
- do not yet rewrite local-primary investigation body

---

### `S4` — Signoz-first investigation + report

**Files / surfaces**
- `app/investigator/tools.py`
- `app/investigator/local_primary.py`
- `app/reports/markdown_builder.py`
- `app/reports/contracts.py`
- `tests/test_investigator_tools.py`
- `tests/test_live_investigation.py`
- `tests/test_markdown_builder.py`
- `tests/test_signoz_first_report.py` (new)

**Change / add functions**
- `app.investigator.tools.BoundedInvestigatorTools.get_signoz_trace_details(trace_id, ...)`
  - input: trace id
  - output: bounded trace hierarchy bundle
- `app.investigator.local_primary.investigate(request)`
  - input: Signoz-first investigation request
  - output: hypotheses / cause chain / downstream dependency hints anchored mainly in Signoz evidence
- `app.reports.markdown_builder.render_alert_report(...)`
  - output: report sections call out Signoz alert context / failing endpoint / status codes / downstream service / trace ids as primary evidence

**Minimal tests**
- local-primary uses trace details / top ops / logs-by-trace as primary live follow-up
- report clearly distinguishes Signoz primary evidence vs Prometheus corroboration
- Prometheus absence does not collapse investigation schema completeness

**done_when**
- final report is Signoz-first in narrative and refs
- local-primary no longer depends on Prometheus as primary live follow-up evidence

**stop boundary**
- do not yet close out pack

---

### `S5` — runtime / webhook / smoke / closeout

**Files / surfaces**
- `app/runtime_entry.py`
- `app/main.py`
- `app/live_signoz_smoke.py` (new)
- `scripts/run_live_signoz_alert_smoke.py` (new)
- `tests/test_live_signoz_runtime.py` (new)
- `tests/test_bootstrap.py`
- `docs/plan/*`
- `docs/warning-agent-signoz-first-runbook.md`

**Change / add functions**
- `app.runtime_entry.execute_signoz_alert_runtime(...)` or equivalent Signoz-first path
  - input: normalized Signoz alert or stored alert payload
  - output: packet / decision / optional investigation / report
- `app.main.build_runtime_entrypoint(...)`
  - add Signoz-first invocation shape if needed
- `app.live_signoz_smoke.run_live_signoz_alert_smoke(...)`
  - input: Signoz alert fixture or current live alert metadata
  - output: runtime summary

**Minimal tests**
- Signoz alert -> packet -> decision -> investigation/report smoke path
- full regression
- direct smoke against current real SigNoz surface

**done_when**
- warning-agent can honestly claim `SigNoz alert as primary input`
- Prometheus is documented and implemented as corroboration only
- closeout evidence shows real Signoz-first runtime behavior

**stop boundary**
- no rollout / admission / broader platformization work

## 9. Risks / blockers

1. 当前 SigNoz logs surface 可能仍无法稳定按 service 命中；需要 trace-id / host / downstream target 作为替代策略。
2. 当前 analyzer / routing 逻辑可能仍然把 Signoz-primary case 判成低 severity；这需要在 `S3` 正面修，不允许靠文案绕过。
3. 若 packet contract 无法诚实容纳 Signoz alert metadata，需要在 `S1` 做显式 schema/contract freeze，而不是临时塞字段。
4. Prometheus freeze 必须是 hard freeze；若执行中又回到 Prometheus-first 调优，视为 replan failure。

## 10. Exit criteria

本 pack 只有在以下全部成立时才能 closeout：

- Signoz alert 已成为 primary input truth
- Signoz traces / top operations / trace details 已成为 primary severity + investigation evidence
- Prometheus 只保留 infra corroboration
- 当前真实 SigNoz live case 至少有一条能走到 investigation or an explicitly justified no-investigation decision whose reason is Signoz-first and evidence-backed
- report / runbook / control-plane truth 一致
