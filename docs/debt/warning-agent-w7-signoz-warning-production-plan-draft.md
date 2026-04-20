# warning-agent W7 Signoz warning production plan draft

- status: `draft / successor planning input`
- scope: `production-usable Signoz warning ingress + bounded analysis and localization handoff`
- predecessor: `warning-agent-production-integration-bridge-2026-04-20`
- last_updated: `2026-04-20`

## 1. Planning goal

W7 的目标不是重做 `warning-agent` 的分析引擎。

W7 的目标是：

> 把当前已经落地的 Signoz-first warning runtime，
> 推进成一个可以在生产环境中长期运行的告警接入与治理面；
> 让真实 Signoz 告警能够稳定进入 `packet -> analyzer -> investigation -> report` 主链路，
> 同时保持 fail-closed、可审计、可回放、可观测。

通俗地说：

- `SigNoz` 继续负责持续监控和触发告警
- `warning-agent` 负责稳定接收告警、落盘、去重、排队、拉证、分析、定位、出报文、留证据

## 2. Core product target for W7

W7 完成后，`warning-agent` 应该能诚实地说：

> production Signoz warning can be pushed into warning-agent through a governed ingress surface,
> warning-agent can durably admit the warning,
> run bounded analysis and localization on it,
> and emit an operator-usable report with auditable evidence and rollback-safe runtime behavior.

当前仓库已经具备的部分：

- Signoz-first input contract
- Signoz-first evidence collection
- bounded analyzer / investigator / report path
- outcome admission baseline
- delivery seam
- provider runtime gate
- operator-visible rollout evidence baseline

W7 要补齐的，是把这些能力变成生产可治理的整体，而不是单点 demo。

## 3. After warning receipt: what the system must do

基于当前项目核心目标，拿到警报后，系统的职责不是“无限制全面分析”，而是“有边界地完成足够全面的分析和定位”。

收到一条告警后，系统必须完成三件事：

1. 判断这条告警的严重程度和处理级别。
2. 给出最可能的问题位置：
   - 哪个 service / operation
   - 哪个 downstream dependency
   - 哪个 trace / top operation / status code 证明了这个判断
3. 产出标准化结论：
   - 为什么会报
   - 当前影响范围
   - 建议谁处理
   - 下一步怎么查

这条主线保持不变：

```text
Signoz warning
  -> governed ingress
  -> durable admission
  -> bounded evidence collection
  -> incident packet
  -> local analyzer
  -> optional investigation
  -> markdown report
  -> delivery / feedback / audit evidence
```

## 4. Non-goals

W7 不做：

- 不把 `warning-agent` 做成新的 observability platform
- 不把 `warning-agent` 做成默认全量轮询 SigNoz 的数据平面
- 不重写 analyzer / investigator 的核心产品哲学
- 不把 root-cause 目标膨胀成“每次都必须自动 100% 定位”
- 不在同一轮里混入完整 multi-environment secret platform 或 deployment platform

## 5. Execution slices

### `W7.S1` Signoz ingress contract and durable admission

目标：

- 建立一个生产可用的 Signoz 告警接入面，让真实 warning 可以不依赖 fixture / replay 进入系统

核心任务：

1. 新增 dedicated Signoz ingress surface：
   - 例如 `/webhook/signoz` 或 `/ingest/signoz-alert`
2. 冻结 caller contract：
   - payload shape
   - required fields
   - auth / signature / caller identity
3. 建立 durable admission truth：
   - raw payload 落盘
   - normalized alert 落盘
   - admission receipt 落盘
   - producer identity / provenance 写入
4. 明确 fail-closed receipt：
   - auth failed
   - malformed payload
   - admission unavailable

必须避免：

- 直接把 Signoz ingress 绑定到同步完整调查执行
- 没有 caller identity 就接受生产外部流量
- 只返回 HTTP 200 却没有 durable receipt truth

done_when：

- live Signoz push 有明确 ingress route
- ingress 可显式区分 `accepted / rejected / deferred`
- 每条 accepted warning 都有 durable admission record 和 provenance truth

### `W7.S2` Dedupe, queue, and worker boundary

目标：

- 把“收到告警”和“执行分析”拆开，形成可重试、可回压、可恢复的生产处理边界

核心任务：

1. 设计 dedupe key：
   - `rule_id`
   - `service`
   - `operation`
   - `status`
   - `startsAt / evalWindow`
2. 建立 queue / ledger truth：
   - pending
   - processing
   - completed
   - failed
   - dead-letter
3. 建立 retry / backoff / poison message policy
4. 新增 worker path：
   - 只消费 durable accepted warnings
   - 不依赖 HTTP request 生命周期完成整条链路

必须避免：

- duplicate firing 反复触发同一问题的完整分析
- queue 无 backlog truth
- worker crash 后事件 silent loss

done_when：

- accepted warnings 会进入 durable queue/ledger
- worker 可重复恢复并继续消费
- dedupe 和 retry 行为可直接证明

### `W7.S3` Production analysis and localization handoff

目标：

- 让每条 admitted Signoz warning 都能稳定进入现有的 bounded 分析与定位链路

核心任务：

1. 把 queue worker 接到现有主链路：
   - `normalize_signoz_alert_payload`
   - Signoz-first evidence bundle
   - `incident packet`
   - local analyzer
   - optional investigation
   - markdown report
2. 冻结“告警后分析”最小 contract：
   - severity / action
   - suspected primary cause
   - routing / owner
   - evidence refs
   - unknowns
3. 让失败路径显式可见：
   - evidence partial
   - investigation fail-closed
   - delivery deferred
   - human review handoff
4. 把 artifacts / metadata / retrieval refresh / rollout evidence sidecar 继续保持为当前 truth

必须避免：

- 为生产 ingress 重新长出第二套 analyzer / investigator 逻辑
- 在 worker path 中偷放无边界 logs / traces 扫描
- 把 cloud fallback 重新长成默认推理平面

done_when：

- admitted warning 可以稳定产出 packet / decision / optional investigation / report
- 每个阶段都有 machine-readable artifact
- “为什么报警、怀疑哪里、建议谁处理”可以直接从 report 中读出

### `W7.S4` Operator governance, readiness, and successor audit

目标：

- 让 operator 能判断系统是不是可以开、现在开到了什么程度、出了问题如何停和查

核心任务：

1. 扩展 operator-visible readiness truth：
   - ingress auth state
   - queue health
   - backlog size
   - oldest pending age
   - deduped count
   - processing failure count
   - delivery deferred count
   - cloud fallback ratio
2. 建立 environment-specific rollout checklist：
   - 哪些 env vars / secrets / endpoints 是必须项
   - 哪些状态下必须 fail closed
3. 建立 live rollout audit rule：
   - 什么证据才允许 claim live-ready
   - 什么 residual 必须冻结
4. 完成 W7 successor audit / closeout input

必须避免：

- 只有功能跑通，没有 operator truth
- 把 local proof 误写成 production-ready
- readiness 只报告“服务在线”，不报告 ingress/queue/provider/delivery gate truth

done_when：

- operator 可以通过统一 surface 判断当前 rollout state
- live claim 和 residual freeze 都有显式 audit 证据

## 6. Dependency order

顺序固定为：

1. `W7.S1`
2. `W7.S2`
3. `W7.S3`
4. `W7.S4`

原因：

- `S1` 先定义什么叫“合法进入系统的 Signoz warning”
- `S2` 再保证进入后的 warning 不会丢、不重复炸、不被 HTTP 生命周期绑死
- `S3` 再把已 admitted 的 warning 接到现有分析和定位链路
- `S4` 最后为整条生产路径补 operator readiness、rollout governance、audit truth

依赖关系图：

```text
W7.S1 ingress contract + durable admission
  -> W7.S2 dedupe + queue + worker boundary
    -> W7.S3 production analysis/localization handoff
      -> W7.S4 operator governance + audit
```

## 7. First concrete move

如果 W7 进入 execution，第一步不该是改 analyzer。

第一步应该是：

> 先落 `W7.S1`，建立一个 dedicated Signoz ingress route 和 durable admission receipt，
> 明确外部告警是如何可信进入系统的。

只有这个入口被证明后，后面的 queue、worker、analysis governance 才有真实对象可以承接。
