# warning-agent Schema Draft

- 状态: `draft-contract`
- 范围:
  - `incident packet`
  - `local analyzer decision`
  - `cloud investigation result`
  - `alert report` Markdown contract

## 1. 设计原则

1. 所有 runtime contract 都版本化。
2. 所有时间使用 `RFC3339 UTC`。
3. 结构化对象是真相，Markdown 是投影。
4. 所有对象必须支持 replay、diff、benchmark。
5. 热路径先产出结构化字段，再生成 prose。

---

## 2. `incident-packet.v1`

### 2.1 作用

`incident packet` 是系统唯一 canonical runtime unit。

它连接：

- evidence collection
- local retrieval
- local analyzer
- cloud investigator
- report generation

### 2.2 Top-level fields

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `schema_version` | string | 是 | 固定 `incident-packet.v1` | schema pin |
| `packet_id` | string | 是 | 正则 `^ipk_[a-z0-9_\\-]+$` | 唯一 id |
| `candidate_source` | string | 是 | `alertmanager_webhook` / `prometheus_scan` / `manual_replay` | 来源 |
| `created_at` | string | 是 | RFC3339 UTC | 生成时间 |
| `environment` | string | 是 | 非空 | 环境 |
| `service` | string | 是 | 非空 | 服务名 |
| `operation` | string or null | 是 | 可空 | 操作或 endpoint |
| `entity_type` | string | 是 | `service` / `service_operation` | 粒度 |
| `entity_key` | string | 是 | 非空 | 检索与 join key |
| `window` | object | 是 | 见下文 | 观测时间窗 |
| `prometheus` | object | 是 | 见下文 | Prometheus 证据 |
| `signoz` | object | 是 | 见下文 | SigNoz 证据 |
| `topology` | object | 是 | 见下文 | owner / repo / blast radius |
| `history` | object | 否 | 见下文 | 历史上下文 |
| `evidence_refs` | object | 是 | 见下文 | 查询引用 |

### 2.3 `window`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `start_ts` | string | 是 | RFC3339 UTC |
| `end_ts` | string | 是 | RFC3339 UTC |
| `duration_sec` | integer | 是 | `>= 60` 且 `<= 3600` |

### 2.4 `prometheus`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `alerts_firing` | array[string] | 是 | 可空 |
| `error_rate` | number or null | 是 | present 时 `>= 0` |
| `error_rate_baseline` | number or null | 是 | present 时 `>= 0` |
| `error_rate_delta` | number or null | 是 | 可空 |
| `latency_p95_ms` | number or null | 是 | present 时 `>= 0` |
| `latency_p95_baseline_ms` | number or null | 是 | present 时 `>= 0` |
| `latency_p95_delta` | number or null | 是 | 可空 |
| `qps` | number or null | 是 | present 时 `>= 0` |
| `qps_baseline` | number or null | 是 | present 时 `>= 0` |
| `qps_delta` | number or null | 是 | 可空 |
| `saturation` | number or null | 是 | present 时 `>= 0` |

### 2.5 `signoz`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `top_error_templates` | array[object] | 是 | 最多 `10` 项 |
| `top_slow_operations` | array[object] | 是 | 最多 `10` 项 |
| `trace_error_ratio` | number or null | 是 | present 时 `0.0-1.0` |
| `sample_trace_ids` | array[string] | 是 | 可空 |
| `sample_log_refs` | array[string] | 是 | 可空 |

#### `top_error_templates[]`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `template_id` | string | 是 | 非空 |
| `template` | string | 是 | 非空 |
| `count` | integer | 是 | `>= 1` |
| `novelty_score` | number | 是 | `0.0-1.0` |

#### `top_slow_operations[]`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `operation` | string | 是 | 非空 |
| `p95_ms` | number | 是 | `>= 0` |
| `error_ratio` | number or null | 是 | present 时 `0.0-1.0` |

### 2.6 `topology`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `tier` | string | 是 | `tier0` / `tier1` / `tier2` / `unknown` |
| `owner` | string or null | 是 | 可空 |
| `repo_candidates` | array[string] | 是 | 可空 |
| `upstream_count` | integer | 是 | `>= 0` |
| `downstream_count` | integer | 是 | `>= 0` |
| `blast_radius_score` | number | 是 | `0.0-1.0` |

### 2.7 `history`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `recent_deploy` | boolean | 否 | 默认 `false` |
| `similar_incident_ids` | array[string] | 否 | 可空 |
| `similar_packet_ids` | array[string] | 否 | 可空 |

### 2.8 `evidence_refs`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `prometheus_query_refs` | array[string] | 是 | 可空 |
| `signoz_query_refs` | array[string] | 是 | 可空 |

### 2.9 示例

```json
{
  "schema_version": "incident-packet.v1",
  "packet_id": "ipk_checkout_post_pay_20260418t120000z",
  "candidate_source": "alertmanager_webhook",
  "created_at": "2026-04-18T12:00:08Z",
  "environment": "prod",
  "service": "checkout",
  "operation": "POST /api/pay",
  "entity_type": "service_operation",
  "entity_key": "checkout:POST /api/pay",
  "window": {
    "start_ts": "2026-04-18T11:55:00Z",
    "end_ts": "2026-04-18T12:00:00Z",
    "duration_sec": 300
  },
  "prometheus": {
    "alerts_firing": ["high_error_rate", "latency_p95_high"],
    "error_rate": 0.21,
    "error_rate_baseline": 0.02,
    "error_rate_delta": 0.19,
    "latency_p95_ms": 2400,
    "latency_p95_baseline_ms": 410,
    "latency_p95_delta": 1990,
    "qps": 122,
    "qps_baseline": 118,
    "qps_delta": 4,
    "saturation": 0.81
  },
  "signoz": {
    "top_error_templates": [
      {
        "template_id": "tmpl_db_timeout",
        "template": "db timeout on order lookup",
        "count": 182,
        "novelty_score": 0.91
      }
    ],
    "top_slow_operations": [
      {
        "operation": "POST /api/pay",
        "p95_ms": 2400,
        "error_ratio": 0.34
      }
    ],
    "trace_error_ratio": 0.34,
    "sample_trace_ids": ["7f8a3c", "7f8a40"],
    "sample_log_refs": ["signoz://logs/query-123/row-18"]
  },
  "topology": {
    "tier": "tier1",
    "owner": "payments-oncall",
    "repo_candidates": ["checkout-service", "payment-gateway-client"],
    "upstream_count": 6,
    "downstream_count": 12,
    "blast_radius_score": 0.88
  },
  "history": {
    "recent_deploy": true,
    "similar_incident_ids": ["INC-1422"],
    "similar_packet_ids": ["ipk_checkout_post_pay_20260411t110000z"]
  },
  "evidence_refs": {
    "prometheus_query_refs": ["prom://query/high_error_rate_window_300s"],
    "signoz_query_refs": ["signoz://trace/query-123", "signoz://logs/query-456"]
  }
}
```

---

## 3. `local-analyzer-decision.v1`

### 3.1 作用

这是本地高频分析器的唯一输出契约。

无论后端是:

- `fast_scorer`
- `small_model`
- `hybrid`

都必须输出同一结构。

### 3.2 Top-level fields

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `schema_version` | string | 是 | 固定 `local-analyzer-decision.v1` | version pin |
| `decision_id` | string | 是 | 正则 `^lad_[a-z0-9_\\-]+$` | 唯一 id |
| `packet_id` | string | 是 | 正则 `^ipk_[a-z0-9_\\-]+$` | join 回 packet |
| `analyzer_family` | string | 是 | `fast_scorer` / `small_model` / `hybrid` | 实现家族 |
| `analyzer_version` | string | 是 | 非空 | 版本号 |
| `severity_band` | string | 是 | `P1` / `P2` / `P3` / `P4` | 本地严重性 |
| `severity_score` | number | 是 | `0.0-1.0` | 风险分数 |
| `novelty_score` | number | 是 | `0.0-1.0` | 新颖度 |
| `confidence` | number | 是 | `0.0-1.0` | 置信度 |
| `needs_cloud_investigation` | boolean | 是 | 布尔值 | 是否升级 |
| `recommended_action` | string | 是 | `observe` / `open_ticket` / `page_owner` / `send_to_human_review` | 建议动作 |
| `reason_codes` | array[string] | 是 | `1-8` 项 | 机器可聚合原因 |
| `risk_flags` | array[string] | 是 | 可空 | 高风险标志 |
| `retrieval_hits` | array[object] | 是 | 最多 `5` 项 | 本地历史证据 |
| `cloud_trigger_reasons` | array[string] | 是 | 未升级时为空 | 升级原因 |

### 3.3 `risk_flags`

允许值：

- `rule_miss`
- `high_blast_radius`
- `new_template`
- `owner_unknown`
- `recent_deploy`
- `service_hotspot`

### 3.4 `retrieval_hits[]`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `packet_id` | string | 是 | 非空 |
| `similarity` | number | 是 | `0.0-1.0` |
| `known_outcome` | string | 是 | `severe` / `benign` / `unknown` |

### 3.5 验证规则

1. 若 `needs_cloud_investigation = false`，则 `cloud_trigger_reasons` 必须为空。
2. 若 `recommended_action = page_owner`，则 `severity_band` 必须是 `P1` 或 `P2`。
3. 若 `confidence < 0.35`，通常应触发升级。
4. `reason_codes` 必须是可检索、可聚合字符串，不能是长句 prose。

### 3.6 示例

```json
{
  "schema_version": "local-analyzer-decision.v1",
  "decision_id": "lad_checkout_post_pay_20260418t120010z",
  "packet_id": "ipk_checkout_post_pay_20260418t120000z",
  "analyzer_family": "fast_scorer",
  "analyzer_version": "fast-scorer-2026-04-18",
  "severity_band": "P1",
  "severity_score": 0.94,
  "novelty_score": 0.87,
  "confidence": 0.61,
  "needs_cloud_investigation": true,
  "recommended_action": "page_owner",
  "reason_codes": [
    "error_rate_spike",
    "template_novelty_high",
    "similar_to_past_severe"
  ],
  "risk_flags": [
    "high_blast_radius",
    "recent_deploy"
  ],
  "retrieval_hits": [
    {
      "packet_id": "ipk_checkout_post_pay_20260411t110000z",
      "similarity": 0.82,
      "known_outcome": "severe"
    }
  ],
  "cloud_trigger_reasons": [
    "novelty_high",
    "blast_radius_high"
  ]
}
```

---

## 4. `cloud-investigation-result.v1`

### 4.1 作用

这是 investigator 层的统一输出契约。

它有两个直接用途：

1. 作为当前一次 deep investigation 的结构化结果
2. 作为后续本地 analyzer / 本地小模型可复用的 teacher-style supervision artifact

最关键的一点是：

- 它不能只服务“云端模型单步分析”
- 它必须同时支持：
  - 本地 `Gemma4` investigator
  - 云端更强模型 final reviewer

也就是说，如果后续采用两步 investigator 链路：

```text
local fast analyzer
  -> local Gemma4 investigator
  -> compressed handoff
  -> cloud supermodel reviewer
```

那么本地 Gemma4 与云端 reviewer 都应该输出同一类对象：

- `cloud-investigation-result.v1`

只是它们的：

- `investigator_tier`
- `model_provider`
- `parent_investigation_id`

不同。

### 4.2 Top-level fields

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `schema_version` | string | 是 | 固定 `cloud-investigation-result.v1` | version pin |
| `investigation_id` | string | 是 | 正则 `^cir_[a-z0-9_\\-]+$` | investigation 唯一 id |
| `packet_id` | string | 是 | 正则 `^ipk_[a-z0-9_\\-]+$` | join 回 packet |
| `decision_id` | string | 是 | 正则 `^lad_[a-z0-9_\\-]+$` | join 回 local decision |
| `parent_investigation_id` | string or null | 否 | 正则 `^cir_[a-z0-9_\\-]+$` | 若是 second-stage reviewer，则指向上一层 investigation |
| `investigator_tier` | string | 是 | `local_gemma4_investigator` / `cloud_final_reviewer` / `single_stage_cloud_investigator` | 调查层级 |
| `model_provider` | string | 是 | `local_vllm` / `openai` / `other` | 模型提供方 |
| `model_name` | string | 是 | 非空 | 实际模型名 |
| `generated_at` | string | 是 | RFC3339 UTC | 生成时间 |
| `input_refs` | object | 是 | 见下文 | 本次分析使用了哪些输入 |
| `summary` | object | 是 | 见下文 | 摘要结论 |
| `hypotheses` | array[object] | 是 | 最多 `5` 项 | 候选故障链 |
| `analysis_updates` | object | 是 | 见下文 | 是否覆盖本地判断 |
| `routing` | object | 是 | 见下文 | owner / repo / escalation hints |
| `evidence_refs` | object | 是 | 见下文 | 实际证据引用 |
| `unknowns` | array[string] | 是 | 至少 `1` 项，可填 `none` | 未解决问题 |
| `compressed_handoff` | object | 否 | 见下文 | 给下一层 investigator 的压缩输入 |

### 4.3 `input_refs`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `packet_id` | string | 是 | 与顶层一致 |
| `decision_id` | string | 是 | 与顶层一致 |
| `retrieval_packet_ids` | array[string] | 否 | 可空 |
| `prometheus_query_refs` | array[string] | 否 | 可空 |
| `signoz_query_refs` | array[string] | 否 | 可空 |
| `code_search_refs` | array[string] | 否 | 可空 |
| `upstream_report_id` | string or null | 否 | 若是 cloud reviewer，可指向本地 investigator 生成的中间报文 |

### 4.4 `summary`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `investigation_used` | boolean | 是 | 布尔值 |
| `severity_band` | string | 是 | `P1` / `P2` / `P3` / `P4` |
| `recommended_action` | string | 是 | `observe` / `open_ticket` / `page_owner` / `send_to_human_review` |
| `confidence` | number | 是 | `0.0-1.0` |
| `reason_codes` | array[string] | 是 | `1-10` 项 |
| `suspected_primary_cause` | string | 是 | 非空 |
| `failure_chain_summary` | string | 是 | 非空 |

### 4.5 `hypotheses[]`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `rank` | integer | 是 | 从 `1` 开始 |
| `hypothesis` | string | 是 | 非空 |
| `confidence` | number | 是 | `0.0-1.0` |
| `supporting_reason_codes` | array[string] | 是 | 可空 |

### 4.6 `analysis_updates`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `severity_band_changed` | boolean | 是 | 布尔值 |
| `recommended_action_changed` | boolean | 是 | 布尔值 |
| `cloud_escalation_was_correct` | boolean or null | 否 | 可空 |
| `notes` | array[string] | 是 | 可空 |

### 4.7 `routing`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `owner_hint` | string or null | 是 | 可空 |
| `repo_candidates` | array[string] | 是 | 可空 |
| `suspected_code_paths` | array[string] | 是 | 可空 |
| `escalation_target` | string or null | 是 | 可空 |

### 4.8 `evidence_refs`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `prometheus_ref_ids` | array[string] | 是 | 可空 |
| `signoz_ref_ids` | array[string] | 是 | 可空 |
| `trace_ids` | array[string] | 是 | 可空 |
| `code_refs` | array[string] | 是 | 可空 |

### 4.9 `compressed_handoff`

这个对象用于：

- 本地 Gemma4 investigator -> 云端 final reviewer

也就是说，如果先由本地大模型做高频深挖，再交给云端更强模型终审，就把压缩结果放这里。

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `handoff_markdown` | string | 否 | 非空时表示可直接给下一层模型 |
| `handoff_tokens_estimate` | integer | 否 | `>= 0` |
| `carry_reason_codes` | array[string] | 否 | 可空 |

### 4.10 验证规则

1. 若 `investigator_tier = cloud_final_reviewer`，则 `parent_investigation_id` 应存在。
2. 若 `investigator_tier = local_gemma4_investigator`，则 `model_provider` 应优先为 `local_vllm`。
3. `reason_codes` 必须是结构化短标签，不允许是长 prose。
4. `compressed_handoff` 若存在，则 `handoff_markdown` 必须是压缩摘要，不允许简单复制完整报文。
5. 若 `analysis_updates.severity_band_changed = true`，则 `summary.severity_band` 应与本地 `local analyzer decision` 不同。

### 4.11 示例

```json
{
  "schema_version": "cloud-investigation-result.v1",
  "investigation_id": "cir_checkout_post_pay_20260418t120020z",
  "packet_id": "ipk_checkout_post_pay_20260418t120000z",
  "decision_id": "lad_checkout_post_pay_20260418t120010z",
  "parent_investigation_id": null,
  "investigator_tier": "local_gemma4_investigator",
  "model_provider": "local_vllm",
  "model_name": "gemma-4-26B-A4B-it",
  "generated_at": "2026-04-18T12:00:20Z",
  "input_refs": {
    "packet_id": "ipk_checkout_post_pay_20260418t120000z",
    "decision_id": "lad_checkout_post_pay_20260418t120010z",
    "retrieval_packet_ids": ["ipk_checkout_post_pay_20260411t110000z"],
    "prometheus_query_refs": ["prom://query/high_error_rate_window_300s"],
    "signoz_query_refs": ["signoz://trace/query-123", "signoz://logs/query-456"],
    "code_search_refs": ["/srv/checkout/payment_client.py:88"],
    "upstream_report_id": null
  },
  "summary": {
    "investigation_used": true,
    "severity_band": "P1",
    "recommended_action": "page_owner",
    "confidence": 0.78,
    "reason_codes": [
      "payment_dependency_timeout",
      "trace_error_path_consistent",
      "recent_deploy_risk"
    ],
    "suspected_primary_cause": "payment gateway lookup timeout burst",
    "failure_chain_summary": "checkout -> payment client -> gateway/db timeout burst"
  },
  "hypotheses": [
    {
      "rank": 1,
      "hypothesis": "payment gateway dependency timeout caused checkout latency spike",
      "confidence": 0.78,
      "supporting_reason_codes": [
        "payment_dependency_timeout",
        "trace_error_path_consistent"
      ]
    },
    {
      "rank": 2,
      "hypothesis": "database tier saturation contributed to retry amplification",
      "confidence": 0.41,
      "supporting_reason_codes": [
        "recent_deploy_risk"
      ]
    }
  ],
  "analysis_updates": {
    "severity_band_changed": false,
    "recommended_action_changed": false,
    "cloud_escalation_was_correct": null,
    "notes": [
      "local first-pass severity already reasonable",
      "investigation mainly increased failure-chain confidence"
    ]
  },
  "routing": {
    "owner_hint": "payments-oncall",
    "repo_candidates": ["checkout-service", "payment-gateway-client"],
    "suspected_code_paths": ["/srv/checkout/payment_client.py:88"],
    "escalation_target": "payments-oncall"
  },
  "evidence_refs": {
    "prometheus_ref_ids": ["prom://query/high_error_rate_window_300s"],
    "signoz_ref_ids": ["signoz://trace/query-123", "signoz://logs/query-456"],
    "trace_ids": ["7f8a3c", "7f8a40"],
    "code_refs": ["/srv/checkout/payment_client.py:88"]
  },
  "unknowns": [
    "whether gateway timeout was primary or database contention was primary"
  ],
  "compressed_handoff": {
    "handoff_markdown": "# Investigation Handoff\n- suspected cause: payment gateway timeout burst\n- severity: P1\n- action: page_owner\n- top evidence: trace path + timeout templates + code path candidate\n- unknowns: gateway vs db primary cause",
    "handoff_tokens_estimate": 180,
    "carry_reason_codes": [
      "payment_dependency_timeout",
      "trace_error_path_consistent",
      "recent_deploy_risk"
    ]
  }
}
```

---

## 5. `alert-report.v1`

### 4.1 作用

这是产品最终输出的 Markdown 契约。

Markdown 报文必须由：

- `incident packet`
- `local analyzer decision`
- 可选 `cloud investigation result`

共同渲染而来。

### 4.2 Frontmatter contract

报文必须以 YAML frontmatter 开头。

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `schema_version` | string | 是 | 固定 `alert-report.v1` |
| `report_id` | string | 是 | 正则 `^rpt_[a-z0-9_\\-]+$` |
| `packet_id` | string | 是 | 正则 `^ipk_[a-z0-9_\\-]+$` |
| `decision_id` | string | 是 | 正则 `^lad_[a-z0-9_\\-]+$` |
| `generated_at` | string | 是 | RFC3339 UTC |
| `severity_band` | string | 是 | `P1` / `P2` / `P3` / `P4` |
| `delivery_class` | string | 是 | `observe` / `open_ticket` / `page_owner` / `send_to_human_review` |
| `cloud_investigation_used` | boolean | 是 | 布尔值 |
| `service` | string | 是 | 非空 |
| `operation` | string or null | 是 | 可空 |
| `owner` | string or null | 是 | 可空 |
| `repo_candidates` | array[string] | 是 | 可空 |
| `prometheus_ref_ids` | array[string] | 是 | 可空 |
| `signoz_ref_ids` | array[string] | 是 | 可空 |

### 4.3 Markdown 正文必须包含的区块

区块顺序固定为：

1. `## Executive Summary`
2. `## Why This Alert Exists`
3. `## Metric Signals`
4. `## Logs And Traces`
5. `## Cloud Investigation`
6. `## Impact And Routing`
7. `## Recommended Action`
8. `## Evidence Refs`
9. `## Unknowns`

### 4.4 区块内容约束

#### `## Executive Summary`

至少包含：

- service
- operation
- window
- severity band
- confidence
- delivery class

#### `## Why This Alert Exists`

至少包含：

- local analyzer `reason_codes`
- local novelty / confidence 摘要
- cloud trigger reasons 或 `none`

#### `## Metric Signals`

至少包含：

- firing alerts
- error rate delta
- p95 delta
- qps delta
- saturation

#### `## Logs And Traces`

至少包含：

- top error templates
- trace error ratio
- top slow operations

#### `## Cloud Investigation`

若 `cloud_investigation_used = true`，必须包含：

- suspected failure chain
- likely repo / module
- code confirmation refs

若 `cloud_investigation_used = false`，必须只包含一条：

- `not used`

#### `## Impact And Routing`

至少包含：

- blast radius 摘要
- owner
- repo candidates

#### `## Recommended Action`

至少包含：

- immediate action
- next checks
- escalation target

#### `## Evidence Refs`

至少包含：

- Prometheus refs
- SigNoz refs
- code refs（若存在）

#### `## Unknowns`

至少包含一条。

若无实质未知项，则写：

- `none`

### 4.5 Frontmatter 示例

```yaml
---
schema_version: alert-report.v1
report_id: rpt_checkout_post_pay_20260418t120030z
packet_id: ipk_checkout_post_pay_20260418t120000z
decision_id: lad_checkout_post_pay_20260418t120010z
generated_at: 2026-04-18T12:00:30Z
severity_band: P1
delivery_class: page_owner
cloud_investigation_used: true
service: checkout
operation: POST /api/pay
owner: payments-oncall
repo_candidates:
  - checkout-service
  - payment-gateway-client
prometheus_ref_ids:
  - prom://query/high_error_rate_window_300s
signoz_ref_ids:
  - signoz://trace/query-123
  - signoz://logs/query-456
---
```

### 4.6 Markdown body 示例

```md
## Executive Summary
- service: `checkout`
- operation: `POST /api/pay`
- window: `2026-04-18T11:55:00Z -> 2026-04-18T12:00:00Z`
- severity band: `P1`
- confidence: `0.61`
- delivery class: `page_owner`

## Why This Alert Exists
- local reason codes: `error_rate_spike`, `template_novelty_high`, `similar_to_past_severe`
- local summary: `novelty=0.87 confidence=0.61`
- cloud trigger reasons: `novelty_high`, `blast_radius_high`

## Metric Signals
- firing alerts: `high_error_rate`, `latency_p95_high`
- error rate delta: `+0.19`
- p95 delta ms: `+1990`
- qps delta: `+4`
- saturation: `0.81`

## Logs And Traces
- top template: `db timeout on order lookup` count=`182` novelty=`0.91`
- trace error ratio: `0.34`
- top slow op: `POST /api/pay` p95=`2400`

## Cloud Investigation
- suspected failure chain: `checkout -> payment gateway lookup -> db timeout burst`
- likely repo or module: `checkout-service/payment lookup path`
- code refs: `[checkout/payment_client.py:88]`

## Impact And Routing
- blast radius: `0.88`
- owner: `payments-oncall`
- repo candidates: `checkout-service`, `payment-gateway-client`

## Recommended Action
- immediate action: `page_owner`
- next checks: `confirm payment gateway error budget and recent deploy`
- escalation target: `payments-oncall`

## Evidence Refs
- Prometheus: `prom://query/high_error_rate_window_300s`
- SigNoz: `signoz://trace/query-123`, `signoz://logs/query-456`
- Code: `[checkout/payment_client.py:88]`

## Unknowns
- whether the timeout burst originated from the database tier or the upstream payment gateway
```

---

## 6. 最终规则

运行时真正的 source of truth 只有：

- `incident packet`
- `local analyzer decision`
- optional `cloud investigation result`

Markdown 报文只是这些对象的稳定投影。
