# warning-agent autopilot delivery master plan

- plan_id: `warning-agent-autopilot-delivery-2026-04-18`
- plan_class: `master-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- current_master_wave: `closeout / P5 complete`
- workstream: `docs/bootstrap -> runnable local-first warning-agent`
- last_updated: `2026-04-19`

## 1. Goal

把当前已经完成 bootstrap 与 contract materialization 的 `warning-agent` 仓库，推进为一个**可运行、可回放、可 benchmark** 的窄版智能分析-报警器：

```text
alert
  -> bounded evidence collection
  -> incident packet
  -> local retrieval + local analyzer
  -> optional investigator (default local-first)
  -> optional cloud fallback
  -> markdown alert report
  -> outcome feedback
```

当前 master plan 的默认目标到 `P5 cloud fallback only` 为止。

以下内容不再默认进入主线：

- shadow-mode hardening
- rollout / soak / runbook 扩张
- local small model replacement

若后续需要，必须显式 replan。

## 2. Master-plan role

本 pack 明确定位为总控 master plan。

职责分工固定如下：

- `PLAN`：保存产品边界、阶段顺序、数值 gate、closeout / replan 规则
- `STATUS`：保存当前真实状态、最新证据、已完成事项、blockers、下一刀
- `WORKSET`：只保存当前激活 slice 与严格顺序队列

控制规则：

1. 后续 scratch docs 不得覆盖本 master plan。
2. `STATUS` 与 `WORKSET` 的推进必须受本 `PLAN` 约束。
3. 任一 phase 未满足 closeout rule，不得跳到下一 phase。
4. `P5` 完成后如需扩展 shadow / rollout / model replacement，必须进入显式 replan。

## 3. Governing sources read

本计划以下列文档为当前 SSOT 输入：

- `README.md`
- `docs/warning-agent-architecture.md`
- `docs/warning-agent-schema-draft.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/warning-agent-minimal-repo-skeleton.md`
- `docs/analyse/warning-agent-design-decision-table.md`
- `docs/analyse/warning-agent-tech-stack-recommendation.md`
- `docs/analyse/warning-agent-local-first-investigation-path.md`
- `docs/analyse/warning-agent-local-observability-status.md`
- `theBitterLessons.md`

## 4. Boundary freeze

### 4.1 Product in scope

- Alertmanager / replay 输入
- Prometheus + SigNoz bounded 采证
- `incident packet` 统一表示
- 本地检索 + 本地 fast scorer
- 单一 investigator interface
- 默认 `local-primary` provider
- `cloud-fallback` provider
- Markdown 报文输出
- outcome feedback / replay / benchmark

### 4.2 Explicit non-goals

以下能力不进入当前主线：

- remediation / action execution
- workflow engine
- multi-agent orchestration
- observability UI / APM suite
- general agent runtime
- shadow-mode hardening as default delivery objective
- local small model replacement as default delivery objective

### 4.3 Autopilot interpretation

本 workstream 中的 `autopilot` 只指：

- 用 `PLAN / STATUS / WORKSET` 驱动项目交付
- 用 evidence gate 驱动阶段推进
- 用 stop boundary 防止 scope 漂移
- 用 replan / closeout 规则管理长路径执行

不指把 `warning-agent` 产品本身做成自动执行系统。

## 5. Current truth

### 5.1 Repo reality

当前仓库已经不再是 docs-only：

- 已有：架构 SSOT、schema SSOT、contract inventory、最小 skeleton、技术栈、设计决策、local-first investigator 文档、schema files、config samples、tests、基础 contract modules、deterministic packet/report baseline、storage write path、retrieval index/search、fast scorer baseline、accepted labeled replay corpus、accepted P3 baseline summary、accepted P4 local-primary benchmark summary，以及 `P5` 的 cloud-fallback provider / compressed-handoff-only path / audit and cost guard / runtime escalation path / accepted cloud benchmark summary
- 缺失：当前 master plan 边界内无 blocker；后续扩展需显式 replan

### 5.2 Environment reality

从文档与最小验证得到：

- `SigNoz MCP` 当前可调用，可作为 investigator tools 入口
- `Prometheus` 至少两个入口健康可查
- 本地实现建议可直接采用 `Python 3.12 + uv + FastAPI + SQLite + FTS5`

### 5.3 Design maturity

当前文档已经完成一次 SSOT 收敛：

- 两层 / 三层冲突已被替换为 `local-first + cloud-fallback`
- contract wording 不再以 cloud 为默认中心
- delivery 目标不再默认扩张到 shadow

## 6. Master execution order

| Phase | Wave | Depends on | Core objective | Phase closeout artifact |
|---|---|---|---|---|
| `P1` | `wave-1` | `P0 complete` | repo bootstrap + contract materialization | runnable repo + schema/config/tests baseline |
| `P2` | `wave-2` | `P1` | deterministic packet/report baseline | valid packet + report from replay/fixture |
| `P3` | `wave-3` | `P2` | local analyzer baseline | scored replay corpus + benchmark summary |
| `P4` | `wave-4` | `P3` | single investigator interface, local-first | structured investigation result + report enrichment |
| `P5` | `wave-5` | `P4` | cloud fallback only | bounded cloud fallback integration |

## 7. Phase decomposition into proof-carrying slices

### P1. Repo bootstrap and contract materialization

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `P1.S1` runtime contract inventory and naming freeze | 命名、版本、目录映射冻结 | inventory 成立；无未解释命名冲突 | 不进入 runtime 逻辑 |
| `P1.S2` Python runtime bootstrap | `pyproject.toml`、`app/`、`main.py`、基础包结构 | compileall + import smoke pass | 不实现业务逻辑 |
| `P1.S3` schema materialization | `schemas/*.json` + base contract modules | schema load pass | 不做 packet 数据采集 |
| `P1.S4` config scaffolding | `configs/*.yaml` baseline 样例 | config load smoke pass | 不写生产调优 |
| `P1.S5` smoke and contract harness | `tests/`、README quickstart | pytest + ruff pass | 不实现 replay / packet builder |

### P2. Deterministic packet/report baseline

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `P2.S1` replay input path | replay 输入协议、初始 alert fixture、fixture loader | fixture load + replay smoke pass | 不实现 live routing |
| `P2.S2` webhook stub | 最小 receiver 与 payload normalization | webhook contract test pass | 不接真实生产路由 |
| `P2.S3` deterministic collectors | Prometheus + SigNoz collector | collector smoke against known endpoints pass | 不做 agentic exploration |
| `P2.S4` incident packet builder | alert + collectors -> `incident packet` | packet schema validation pass | 不实现 analyzer runtime |
| `P2.S5` markdown report baseline | packet -> report renderer、frontmatter | golden report render pass | 不实现 investigator runtime |

### P3. Local analyzer baseline

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `P3.S1` storage write path | SQLite metadata + JSONL artifact write path | artifacts persisted and reloadable | 不做模型推理 |
| `P3.S2` retrieval render/index/search | render text、FTS index、search API | retrieval tests with known hits pass | 不引入 vector DB |
| `P3.S3` feature extraction and fast scorer | numeric/retrieval features、baseline scorer | scorer outputs deterministic fields | 不引入 local LLM analyzer |
| `P3.S4` calibration and thresholds | calibration、threshold config、`needs_investigation` 决策 | threshold tests + calibration summary pass | 不实现 investigator runtime |
| `P3.S5` decision benchmark harness | replay benchmark runner、baseline metrics writeback | benchmark summary produced and schema-valid | 不接入 investigator |

#### P3 recovery track when closeout is blocked

当 `P3.S5` 已完成、但 benchmark 仍是 scaffold-only 或 closeout gate 未过时，必须先走恢复轨，而不是直接激活 `P4`。

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `P3.R1` corpus contract + benchmark acceptance freeze | corpus sufficiency / label contract、benchmark acceptance helper、targeted tests | corpus/benchmark targeted tests pass；summary 明确区分 scaffold-only 与 accepted baseline | 不扩样本；不调阈值 |
| `P3.R2` labeled replay / outcome corpus expansion | accepted labeled replay、evidence fixtures、outcome labels 扩到最小 gate 规模 | benchmark summary `sample_limited = false` | 不凭样本数量达标就提前宣称 accepted baseline |
| `P3.R3` threshold retune + accepted baseline attempt | 仅基于扩充后 corpus 做阈值/排序校准并重跑 benchmark | `accepted_baseline = true` 且 P3 gates 全过 | 若 gates 仍不过，不进入 `P4` |
| `P3.R4` explicit policy decision (conditional) | 只有在 honest corpus 下仍无法 closeout 时，才更新 benchmark / acceptance policy | evidence-linked decision doc + updated control plane | 不允许静默放宽 gate |

### P4. Single investigator interface, local-first

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `P4.S1` interface and routing freeze | investigator interface、routing contract、budget fields | contract + config proof | 不引入 cloud fallback |
| `P4.S2` local-primary provider | 本地 provider、timeout、token/tool budget | provider smoke proof | 不引入 cloud fallback |
| `P4.S3` bounded tool wrappers | SigNoz / Prometheus / repo wrappers with hard caps | wrapper tests pass | 不允许无边界工具调用 |
| `P4.S4` structured result + report integration | `investigation-result.v1`、report enrichment | schema validation + report checks pass | 不引入 cloud fallback |
| `P4.S5` degraded local fallback | 本地 provider 失败/超预算时稳定降级 | fallback tests pass | 不做 cloud escalation logic |

#### P4 recovery track when closeout is blocked

当 `P4.S1-P4.S5` 已完成、但 local-primary invocation rate 或其他 `P4` closeout evidence 仍未过 gate 时，必须先走恢复轨，而不是直接激活 `P5`。

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `P4.R1` invocation benchmark freeze | local-primary benchmark harness、summary schema、measurement contract、targeted tests | repeatable benchmark summary 产出且明确 invocation / tool / time / completeness / fallback 指标 | 不调 routing；不改 gate |
| `P4.R2` routing-eval corpus freeze / expansion | dedicated P4 replay corpus、expected investigation routing labels、measurement-ready corpus evidence | benchmark summary 可重复计算且 corpus 不再因样本过薄而失真 | 不静默 padding；不调 thresholds |
| `P4.R3` invocation-rate recovery implementation | local analyzer / routing retune 以降低 local-primary invocation rate，并保持 `P3` accepted baseline 不回退 | `P3` benchmark 仍 `accepted_baseline = true` 且 `P4` numeric gates 全过 | 若 gates 仍不过，不进入 `P5` |
| `P4.R4` explicit policy decision (conditional) | 只有在 honest benchmark 与 recovery 尝试后仍无法 closeout 时，才更新 `P4` acceptance / measurement policy | evidence-linked decision doc + updated control plane | 不允许静默放宽 gate |

### P5. Cloud fallback only

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `P5.S1` fallback gate freeze | local -> cloud fallback 触发规则、预算与 audit 字段 | gate tests pass | 不放宽成 cloud-first |
| `P5.S2` cloud-fallback provider | cloud provider client、request/response contract | client smoke + contract tests pass | 不读原始观测洪流 |
| `P5.S3` compressed-handoff-only path | cloud 只消费 handoff + bounded refs | replay proves handoff-only path works | 不重复做完整本地调查 |
| `P5.S4` audit and cost guard | audit metadata、rate/cost ceiling、failure fallback | failure-mode tests pass | 不允许 cloud 成为 hard dependency |
| `P5.S5` phase closeout summary | closeout package、residuals、readiness memo | evidence-linked summary complete | 不宣称 beyond-P5 rollout ability |

当前 `P5` 在 `P5.S4` 后暴露出一个 honest closeout 缺口：

- `P5.S1` 已冻结 cloud trigger / policy 字段
- 但 `P5.S2-P5.S4` 只完成了 provider / handoff / guard / failure fallback
- 尚未把这些 trigger / policy materialize 成真实的 local-primary -> cloud-fallback routing / invocation path

因此 `P5` 进入 recovery track，先补齐缺口，再允许 closeout。

#### P5 recovery track when closeout is blocked

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `P5.R1` cloud escalation routing / invocation materialization | config enablement、cloud route planning、bounded local->cloud execution path、targeted tests | routing/execution tests pass；full regression pass；cloud trigger rules 被真实消费 | 不做 benchmark/closeout summary |
| `P5.R2` cloud benchmark freeze / acceptance | dedicated cloud benchmark harness、routing-eval corpus、summary artifact、targeted tests | repeatable summary 产出且 P5 numeric gates 有明确 pass/fail evidence | 不静默放宽 gate |
| `P5.R3` phase closeout summary | closeout package、residuals、readiness memo、control-plane closeout | evidence-linked summary complete；control plane 标成 completed | 不宣称 beyond-P5 rollout ability |
| `P5.R4` explicit policy decision (conditional) | 只有在 honest benchmark 与 recovery 后仍无法 closeout 时，才更新 `P5` acceptance / measurement policy | evidence-linked decision doc + updated control plane | 不允许静默放宽 gate |

## 8. Numeric gates for P3-P5

### P3 numeric and honesty gates

| Metric | Gate | Intent |
|---|---|---|
| labeled replay corpus sufficiency | `sample_limited = false` with `>= 10` labeled cases and `>= 3` severe cases | 不接受脚手架 summary 充当 closeout 证据 |
| labeled replay severe recall | `>= 0.85` | first-pass 对严重样本不能太差 |
| top-10 investigation precision on labeled replay | `>= 0.60` | 调查排序具备最低可用性 |
| local analyzer p95 latency per packet | `<= 2.0s` | 保持高频路径可接受 |
| investigation-candidate rate | `<= 35%` of replay packets | 防止 every-alert 都升级 |
| decision schema validity | `100%` | 不接受结构化输出破损 |

`P3` closeout 还要求 benchmark summary 明确写出 `accepted_baseline = true`；若 `sample_limited = true`，所有 metric 只可视为 scaffold 指示，不能用于 honest closeout。

### P4 numeric gates

| Metric | Gate | Intent |
|---|---|---|
| local-primary invocation rate | `<= 20%` of total replay packets | 第二层必须稀疏 |
| local-primary p95 wall time | `<= 120s` | 本地深挖必须 bounded |
| average tool calls per investigation | `<= 8` | 防止工具失控 |
| structured investigation completeness | `>= 0.95` required fields present | 结果要稳定可用 |
| degraded local fallback validity | `100%` valid partial result, no crash | 超预算也要稳定降级 |

`P4` closeout evidence 应来自可重复的 local-primary benchmark summary；若 measurement contract / routing-eval corpus 仍未冻结，则 phase metric 只可视为 replan 指示，不能用于激活 `P5`。

### P5 numeric gates

| Metric | Gate | Intent |
|---|---|---|
| cloud fallback rate | `<= 5%` of total packets and `<= 25%` of investigated packets | cloud 必须最稀疏 |
| cloud fallback p95 wall time | `<= 90s` | 防止 cloud 拖垮路径 |
| compressed handoff token estimate | `p95 <= 1200` | 强制压缩输入 |
| final investigation schema validity | `100%` | 不接受结构化结果损坏 |
| cloud-unavailable fallback report success | `>= 0.95` | cloud 不能成为 hard dependency |

## 9. Phase closeout and mandatory replan rules

| Phase | Phase is done when | Mandatory replan triggers | Residuals that must be closed before next phase |
|---|---|---|---|
| `P1` | `P1.S1-P1.S5` 全部完成；repo 可安装/导入/测试；schema/contract/config 已物化 | contract 命名无法冻结；测试骨架无法建立 | contract 命名映射、schema 版本、目录结构 |
| `P2` | 可从 replay/fixture 生成合法 packet + report；collector smoke 通过 | collector 必须依赖非确定性 agent 才能工作；packet contract 无法承载必要证据 | replay input path、packet schema、report rendering contract |
| `P3` | retrieval/scorer/decision 全链路可跑；benchmark summary `sample_limited = false`；`accepted_baseline = true`；P3 numeric / honesty gates 全过 | labeled corpus 仍不足；severe recall 长期低于 gate；升级率失控；decision schema 频繁失真；benchmark policy 需要显式重定义 | accepted baseline、accepted labeled corpus、decision contract、benchmark harness |
| `P4` | local-first investigator 可用；repeatable local-primary benchmark summary 已产出；P4 数值 gates 全过 | 本地 provider 不稳定或工具预算不足；fallback 不稳定；local-primary invocation rate 长期高于 gate；measurement policy 需要显式重定义 | interface contract、tool caps、investigation result schema、local-primary benchmark summary |
| `P5` | cloud fallback 集成完成；P5 数值 gates 全过；cloud unavailable path 可用 | cloud 速率/成本失控；handoff 压缩丢失关键判断；cloud 成为 hard dependency | fallback policy、cloud contract、fallback path |

命中以下任一项，必须停止继续推进并进入 `replan`：

1. 为完成当前 phase 必须引入 remediation / workflow engine / multi-agent runtime。
2. 当前 phase 的 closeout gate 无法定义成可验证 evidence。
3. 当前 slice 需要两个以上同级主目标。
4. `P5` 之后想继续推进 shadow / rollout / small-model replacement，但没有新的主计划。

## 10. Validation ladder

每一阶段都必须走最小但真实的 gate：

1. schema / contract validation
2. targeted unit tests
3. golden fixture replay
4. report rendering checks
5. collector smoke against known endpoints
6. bounded end-to-end replay

没有对应 evidence，不得宣称该阶段 done。

## 11. Autopilot execution model

每个 slice 固定执行：

```text
read current plan/status/workset
  -> execute one bounded slice
  -> run matching validation
  -> write concrete evidence to status
  -> advance or stop at explicit boundary
```

## 12. Known risks and open questions

1. Alertmanager webhook 真实接入尚未验证，`P2` 应先以 replay + webhook stub 双轨推进。
2. owner / repo / blast radius 的 topology source 尚未冻结。
3. `local-primary` provider 的 serving 形态仍未冻结；当前仅完成 interface / smoke / fallback baseline。
4. 当前已建立 dedicated local-primary routing-eval corpus 与 repeatable benchmark；若后续指标漂移，需继续以 benchmark summary 而非临时 shell 统计为准。
5. 当前已建立最小 accepted labeled replay corpus；后续若要继续提升校准可信度，仍需要更多真实 operator outcome 回填。
6. `P5` 完成后若要进入 shadow / rollout / small-model replacement，必须新开 replan。

## 13. Definition of done

当且仅当以下同时成立时，可认为本 workstream 达成当前目标：

- `warning-agent` 可以从 replay 或真实输入生成合法 `incident packet`
- 可以生成结构化 `local analyzer decision`
- 对 hard case 可选地生成 `investigation result`
- cloud fallback 存在或缺席时都能稳定产出 Markdown 报文
- 全链路可回放、可 benchmark
- `P1-P5` 全部满足各自 closeout rule
- 全过程未引入 remediation / workflow / multi-agent / shadow-mode 主线偏航
