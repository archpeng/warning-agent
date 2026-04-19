# warning-agent Contract Inventory

- 状态: `active-contract-ssot`
- scope: runtime contract inventory、schema/path/module 映射、命名冻结决定
- last_updated: `2026-04-19`

## 1. Purpose

本文件的目标是：

1. 冻结 canonical runtime contract 名称
2. 冻结 schema -> artifact path -> module family 映射
3. 去掉旧叙事里 cloud-biased 的命名歧义

## 2. Canonical runtime contracts

| Runtime object | Canonical schema_version | Materialized schema file | Primary artifact directory | Owning module family | Notes |
|---|---|---|---|---|---|
| incident packet | `incident-packet.v1` | `schemas/incident-packet.v1.json` | `data/packets/` | `app/packet/*` | 系统唯一 canonical runtime unit |
| local analyzer decision | `local-analyzer-decision.v1` | `schemas/local-analyzer-decision.v1.json` | `data/decisions/` | `app/analyzer/*` | first-pass analyzer 唯一输出契约 |
| investigation result | `investigation-result.v1` | `schemas/investigation-result.v1.json` | `data/investigations/` | `app/investigator/*` | 同时服务 `local-primary` 与 `cloud-fallback` 两个 provider |
| alert report | `alert-report.v1` | `schemas/alert-report-frontmatter.v1.json` | `data/reports/` | `app/reports/*` | JSON schema 只覆盖 frontmatter；正文 section order 由 report contract 固定 |
| incident outcome | `incident-outcome.v1` | `schemas/incident-outcome.v1.json` | `data/outcomes/` | `app/feedback/*` | 反馈层 canonical artifact；连接 packet / decision / investigation / report 与 landed outcome truth |

## 3. Naming freeze decisions

### 3.1 Contract names

下面三个 contract 名称保持不变：

- `incident-packet.v1`
- `local-analyzer-decision.v1`
- `investigation-result.v1`

其中 `investigation-result.v1` 继续作为 investigator-shared object，不再区分 local/cloud 两套顶层名称。

### 3.2 Decision field names

`local-analyzer-decision.v1` 现在统一使用：

- `needs_investigation`
- `investigation_trigger_reasons`

不再使用旧的 cloud-specific 表述：

- `needs_cloud_investigation`
- `cloud_trigger_reasons`

原因：

1. `P3` 的职责是决定是否进入 investigator，而不是直接决定是否进 cloud
2. `P4` 默认是 local-first
3. `P5` 才是 cloud fallback

### 3.3 Report wording

report body 现在统一使用：

- `Investigation`

不再使用：

- `Cloud Investigation`

frontmatter 则统一记录：

- `investigation_stage`

而不是：

- `cloud_investigation_used`

## 4. Investigator tier freeze

`investigation-result.v1` 当前允许的 canonical `investigator_tier` 只保留：

- `local_primary_investigator`
- `cloud_fallback_investigator`

这反映的是：

- investigator 是一个接口
- `local-primary` 是默认 provider
- `cloud-fallback` 是 fallback provider

## 5. Repo layout freeze

### 5.1 Schema files

- `schemas/incident-packet.v1.json`
- `schemas/local-analyzer-decision.v1.json`
- `schemas/investigation-result.v1.json`
- `schemas/alert-report-frontmatter.v1.json`
- `schemas/incident-outcome.v1.json`

### 5.2 Module family ownership

- `incident packet` -> `app/packet/*`
- `local analyzer decision` -> `app/analyzer/*`
- `investigation result` -> `app/investigator/*`
- `alert report` -> `app/reports/*`
- `incident outcome` -> `app/feedback/*`

### 5.3 Artifact path freeze

- `incident packet` -> `data/packets/`
- `local analyzer decision` -> `data/decisions/`
- `investigation result` -> `data/investigations/`
- `alert report` -> `data/reports/`
- `incident outcome` -> `data/outcomes/`

## 6. Compatibility policy

从现在起执行以下规则：

1. 新文档、新 schema、新代码、新测试不得再使用 `cloud-investigation-result.v1` 作为 canonical 名称。
2. 新文档、新 schema、新代码、新测试不得再使用 `needs_cloud_investigation` / `cloud_trigger_reasons` 作为 canonical 字段。
3. `Cloud Investigation` 只可作为历史表述，不再是当前 report contract 名称。

## 7. Residuals not closed by this doc

下面问题仍是 carried residual，但不再属于 contract naming blocker：

- topology / owner / repo mapping source-of-truth
- Alertmanager 真实输入路径
- `local-primary` provider 的 serving / budget / timeout 方案
