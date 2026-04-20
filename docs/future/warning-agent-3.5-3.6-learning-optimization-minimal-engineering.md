# warning-agent Future Technical Note: Minimal In-Repo Learning Optimization for 3.5 and 3.6

- 状态: `future-technical-note / pre-plan / not-active-execution`
- 范围:
  - `3.5 First-pass` 的可学习化优化
  - `3.6 Investigation` 的可学习化优化
  - 保持现有 `warning-agent` runtime shell、external contracts 与 governance 基线不被重开
- 不覆盖:
  - `docs/plan/*`
  - `warning-core` 新仓迁移执行
  - ingress / delivery / storage / report replatform
  - canonical schema family rename
- 当前关系:
  - 当前 active execution truth 仍以 `docs/plan/*` 为唯一 SSOT
  - 本文只回答：**如果继续在 `warning-agent` 内部做 3.5/3.6 学习优化，最小工程路线应该是什么**
  - 若后续要真的执行本路线，必须新开 explicit `PLAN / STATUS / WORKSET`

## 1. One-sentence decision

当前最省工程量、也最符合 `The Bitter Lesson` 的路线不是立即在 `warning-core` 新目录下重构整个中枢，
而是：

> 在 `warning-agent` 内保留现有 `3.5 / 3.6` 作为运行脚手架，
> 把它们从“人工阶段真相”改造成“可学习的 policy surfaces”，
> 通过 `replay / compare / outcome-governed feedback` 持续优化，
> 等 internal state/action/policy objects 稳定后，再决定是否抽离到 `warning-core`。

一句话压缩：

```text
keep the shell
learn the policies
extract later
```

## 2. Current truth and why this doc exists

## 2.1 Current truth

当前仓库已经具备的事实：

- 已有稳定的 external contracts：
  - `incident-packet.v1`
  - `local-analyzer-decision.v1`
  - `investigation-result.v1`
  - `alert-report.v1`
  - `incident-outcome.v1`
- 已有可运行的 bounded warning path：
  - `warning -> packet -> local decision -> optional investigation -> report -> outcome`
- 已有 feedback governance 基线：
  - `retrieval refresh`
  - `offline compare`
  - `manual promotion only`
- 已有较完整的 shell：
  - packet
  - collectors
  - storage
  - report
  - delivery
  - ingress / queue / worker

## 2.2 Current limitation

当前真正的瓶颈不是“没有更多阶段”，而是：

1. `3.5` 与 `3.6` 仍带有明显人工阶段编排痕迹。
2. 学习信号还不够密：很多 case 最终只留下一个 coarse outcome。
3. attribution 不够清：当前很难说清哪一步工具调用、哪份 brief、哪种 routing 真正提升了最终质量。
4. premium reasoning 的使用语义还不够 policy 化。
5. 现有 feedback loop 仍是 offline/manual-governed，不足以支撑“今天就彻底改成通用 learned loop”。

## 2.3 Why this doc exists

本文不是要证明“现在就废掉 `3.5 / 3.6`”。

本文要冻结的是更现实的技术判断：

- `3.5 / 3.6` 当前仍然是必要执行脚手架
- 但它们不应继续作为最高层真相被不断细写
- 最小工程路线应把优化对象改成：
  - `state`
  - `action`
  - `policy`
  - `outcome truth`

## 3. Entry criteria and execution boundary

## 3.1 Entry criteria

如果未来要执行本路线，前提固定为：

1. **不要直接在当前 dirty 主工作树上启动此 family**。
   - 建议：
     - 等当前 active pack 收口后再开新 branch
     - 或直接新建 clean worktree
2. 当前 active `docs/plan/*` 不得被本文覆盖。
3. external contracts 与 operator-visible shell 默认视为已冻结基线。
4. 学习优化 family 的目标必须限制在 `3.5 / 3.6` 中枢，不得顺手扩写成新一轮 full replatform。

## 3.2 Explicit non-goals

本路线明确不做：

- 现在就把仓库主结构改造成 `warning-core` 最终目录树
- 现在就删掉所有 `3.5 / 3.6` 术语
- 现在就引入 online learning / auto-promotion
- 现在就引入 vector DB / Kafka / workflow engine / multi-agent runtime
- 现在就重写 ingress、delivery、storage、report shell

## 4. Bottom principles

## 4.1 `The Bitter Lesson` 在 warning-agent 中的正确解释

对当前仓库，`The Bitter Lesson` 不等于：

- 让一个更大的模型吞掉全部 logs / traces / code refs
- 删掉结构化对象
- 删掉 boundedness
- 让 premium model 变成默认神谕

正确解释应是：

1. 少把智能固化在人工阶段树里。
2. 多把智能放在：
   - `state representation`
   - `searchable / comparable actions`
   - `learnable policies`
   - `outcome-governed truth`
3. 继续保留 bounded runtime shell 与 structured contracts。

## 4.2 Keep stages as scaffolding, not as final truth

当前阶段最合理的做法是：

- 保留 `3.5 / 3.6` 作为 runtime scaffold
- 不再继续把“聪明程度”主要写进 `3.5A / 3.5B / 3.5C / 3.6A / 3.6B` 叙事
- 把新优化优先写成：
  - triage policy
  - evidence search policy
  - stop policy
  - premium reasoning policy

## 4.3 Learn decisions, not only conclusions

warning 系统里，真正昂贵的往往不是“最后答错”，而是：

- 不必要的调查
- 过多的工具调用
- 过早定性
- 过晚停止
- 不值得的 premium invocation
- 无效的 handoff / brief

因此最该学习的是：

- whether to investigate
- what to search next
- when to stop
- whether premium is worth invoking
- how to compress evidence for one-shot reasoning

而不只是：

- 最终 suspected cause 是什么

## 4.4 Outcome truth must stay external

必须坚持：

- `3.6` 不能给 `3.5` 直接定义训练真值
- premium model 输出不能直接变成 promotion label
- 真值必须继续来自：
  - operator outcome
  - replay label
  - postmortem / landed resolution

## 4.5 Cost-sensitive utility, not raw accuracy only

`3.5 / 3.6` 的优化目标不能只看“对不对”，而要同时约束：

- severe recall
- false page rate
- investigation hit rate
- tool-call efficiency
- premium token efficiency
- routing correctness
- report usefulness

## 5. Minimal target architecture inside warning-agent

## 5.1 Preserve the shell

本路线默认保留下面这些壳层：

- `app/packet/*`
- `app/collectors/*`
- `app/storage/*`
- `app/reports/*`
- `app/delivery/*`
- `app/receiver/*`（除非只做极小 trace hook）
- existing `feedback governance` baseline

原因：

- 这些模块不是当前学习瓶颈
- 把时间花在 shell 搬迁上，不会直接提升 `3.5 / 3.6` learning efficiency

## 5.2 Preserve external contracts

下面 contracts 默认保持不变：

| Object | Keep? | Why |
|---|---|---|
| `incident-packet.v1` | yes | canonical runtime unit，不应因中枢学习优化而重开 |
| `local-analyzer-decision.v1` | yes | first-pass output 仍应稳定 |
| `investigation-result.v1` | yes | report / delivery / feedback 当前都依赖它 |
| `alert-report.v1` | yes | operator-visible product output，不应同步重开 |
| `incident-outcome.v1` | yes | learning truth 入口必须稳定 |

结论：

> 学习优化优先新增 **internal objects**，而不是修改 external canonical contracts。

## 5.3 Introduce internal learning objects

下面对象推荐作为 **non-canonical internal objects** 引入。

它们服务 learning / replay / attribution；
它们不是当前 operator-facing external SSOT。

| Object | Purpose | First owner surface | Persistence |
|---|---|---|---|
| `CaseStateLite` | 将 packet / decision / assist / evidence / brief / final result 聚合成单 case 的 in-memory state | narrow helper，不重开 full runtime tree | optional |
| `SidecarAssistPacket` | 记录 `3.5` 的语义增强、query rewrite、ambiguity、investigation-value hints | `app/analyzer/*` | yes |
| `DecisionAuditRecord` | 记录 `3.5` 为什么判 investigate / why not、哪些 signals 影响 gating | `app/analyzer/*` | yes |
| `InvestigationEvidencePack` | 记录 `3.6` bounded evidence 搜到的关键 refs 与 strongest/conflicting signals | `app/investigator/*` | yes |
| `CompressedInvestigationBrief` | 记录喂给 premium reasoner 的压缩 brief 与 omission rationale | `app/investigator/*` | yes |
| `ActionTrace` | 记录每一步工具调用、成本、结果、stop reason | `app/investigator/*` | yes |
| `OutcomeTruthRecord` | 将粗 outcome 扩充为更可学习的 action/value annotations | `app/feedback/*` | yes |

固定原则：

1. 这些对象先作为 **internal learning objects** 引入。
2. 先服务 replay / compare / offline evaluation。
3. 不要一开始就因为这些对象存在而重构整个 repo layout。

## 5.4 Placement rule

当前仓库内的最小做法不是立刻创建完整：

```text
app/state/
app/policies/
app/runtime/
```

而是：

- 先按现有 ownership 窄幅落位
- 新对象优先放在：
  - `app/analyzer/*`
  - `app/investigator/*`
  - `app/feedback/*`
  - `app/benchmarks/*`
- 只有当 internal object 数量已经明显失控时，才考虑统一 `app/state/*`

这样做的原因：

- 最小工程量
- 最小 import churn
- 最小 runtime glue 重开

## 6. Strict execution order

以下顺序是本文最核心的执行建议。

## 6.1 Step 0 — Freeze boundaries and create a clean execution lane

### Goal

确保学习优化 family 不与当前 active provider/runtime 收尾工作混在一起。

### Must do

1. 从 clean snapshot / branch / worktree 启动。
2. 记录当前 baseline：
   - external contracts
   - key benchmark summaries
   - current governance freeze
3. 把本 family 的 scope 写死为：
   - `3.5 learning optimization`
   - `3.6 learning optimization`
   - 不碰 shell replatform

### Objective

把本 family 从“在脏工作树里继续顺手改”变成“边界清晰、可比、可回滚的独立技术演进”。

### Done when

- 有 clean branch / worktree
- 有基线 benchmark / test 引用点
- 有明确 protected surfaces

## 6.2 Step 1 — Add internal observability and learning objects before changing policy behavior

### Goal

先让系统能记录 **为什么这样做**，再改变它 **如何做**。

### Must do first

优先新增：

- `SidecarAssistPacket`
- `DecisionAuditRecord`
- `ActionTrace`
- `InvestigationEvidencePack`
- `CompressedInvestigationBrief`

### Suggested touch surfaces

- `app/analyzer/*`
- `app/investigator/*`
- narrow runtime glue only if needed to persist internal artifacts
- `tests/test_*`
- `data/benchmarks/*` or new non-canonical diagnostics paths

### Objective

让每个 case 不再只产出：

- decision
- final investigation result

而是额外产出：

- 语义增强结果
- gating audit
- 每一步 action trace
- evidence pack
- compression brief

### Why first

没有这些对象，就无法回答：

- 哪种 query rewrite 真有用
- 哪次工具调用在浪费
- brief 是否保真
- premium invocation 是否值得

### Done when

每个 investigated case 至少能附带回答：

- 调查是如何被触发的
- 调了哪些工具
- 为什么停在这里
- premium input 到底包含了什么

## 6.3 Step 2 — Optimize `3.5` as a learnable triage surface

### Goal

把 `3.5` 从“feature + scorer + hard gate”提升成可学习 triage surface，但不推翻当前 final decision contract。

### What to learn first

1. `retrieval query rewrite`
2. `warning semantic normalization`
3. `ambiguity / uncertainty estimation`
4. `value-of-investigation prediction`
5. `confidence calibration`

### Fixed rule

`3.5` 的 final gate 仍输出当前：

- `severity_band`
- `recommended_action`
- `needs_investigation`

但这些输出应逐步依赖更可学习的中间 signals，而不只是人工 feature tree。

### Suggested implementation contour

- 保持 `local-analyzer-decision.v1` 不变
- 引入 `SidecarAssistPacket` 作为 internal input
- 引入 `DecisionAuditRecord` 记录：
  - top contributing signals
  - why investigate / why not
  - expected value of investigation
  - confidence decomposition

### Primary objective

让 `3.5` 学会：

- 哪些 case 值得进入 `3.6`
- 哪些 case 虽然不确定但不值得花额外预算
- 哪些 case 即使 signal noisy 也必须 investigate

### Do not do here

- 不要把小模型 sidecar 升格为 final judge
- 不要把 premium reasoning 拉进热路径
- 不要让 `3.5` 为了“更聪明”吞掉 unbounded raw logs/traces

### Done when

可以离线比较：

- baseline retrieval query vs rewritten query
- baseline gating vs assist-informed gating
- calibration before vs after
- investigation precision / severe recall uplift

## 6.4 Step 3 — Optimize `3.6` as explicit evidence search + stop policy

### Goal

把 `3.6` 的真正价值从“阶段叙事”转成：

- evidence search policy
- stop policy
- compression policy

### What to learn first

1. 哪个 action 最值得先做
2. 哪些 follow-up 只是在浪费
3. 哪些 evidence 应被保留为 strongest signals
4. 哪些 evidence 属于 conflicting but still necessary
5. 什么时候 evidence 已经足够，不再继续搜索

### Required shape

`3.6` 每次调查至少应产生：

- `ActionTrace`
- `InvestigationEvidencePack`
- `CompressedInvestigationBrief`
- final `InvestigationResult`

### Suggested touch surfaces

- `app/investigator/tools.py`
- `app/investigator/local_primary.py`
- `app/investigator/runtime.py`
- narrow routing helpers if needed
- benchmark / replay / corpus builders

### Primary objective

让 `3.6` 学会的不是“更像一个会聊天的 investigator”，而是：

- 更快搜到高价值证据
- 更少地做无效工具调用
- 在正确的时间停止
- 给 premium reasoner 一个高信噪比 brief

### Do not do here

- 不要把 `3.6A/3.6B` 再写成更细的人工阶段树
- 不要默认每个 investigated case 都必须走 premium
- 不要过早裁掉 conflicting evidence

### Done when

每次 investigation 都可复盘出：

- action order
- action cost
- strongest vs conflicting signals
- explicit stop reason
- brief completeness / omission rationale

## 6.5 Step 4 — Turn premium reasoning into a selected action, not a semantic default

### Goal

将 premium reasoning 从“名义 fallback / 或 investigated default endpoint”改成真正由 policy 选择的高成本 action。

### Policy question to learn

- 什么时候 local evidence 已足够，不值得 premium
- 什么时候 premium invocation 的 expected utility 高于成本
- 什么时候 premium 只是替代了本地应继续学会的能力

### Fixed rule

- premium 不进入 every-alert 热路径
- premium 不直接定义 truth
- premium 输出继续走现有 `investigation-result.v1`

### Objective

让 premium budget 花在：

- high-risk
- unresolved
- conflict-heavy
- high-value investigated cases

而不是花在：

- 所有 investigated cases
- 只是 local confidence 稍低但信息增益很小的 case

### Done when

可以量化：

- premium invocation rate
- premium-only uplift
- premium token cost per accepted investigation
- premium skipped without quality loss 的比例

## 6.6 Step 5 — Close the learning loop offline, not online

### Goal

把 `3.5 / 3.6` 的 policy 优化接入当前 already-frozen governance，而不是重开 online learning。

### Must align with current governance

继续遵守：

- replay / compare first
- batch review
- manual promotion only
- no silent auto-promotion

### Required outputs

至少新增或强化这些 compare surfaces：

- `3.5 query uplift summary`
- `3.5 calibration summary`
- `3.5 investigation-value summary`
- `3.6 action-efficiency summary`
- `3.6 stop-policy summary`
- `3.6 premium-invocation-value summary`

### Objective

让每一次 learning iteration 都能回答：

- policy variant A 比 B 好在哪里
- 改进来自哪类 case
- 成本有没有上升
- false escalation 有没有被换取为虚假 uplift

### Done when

- compare 报告可重复生成
- promotion decision 仍由人工 review 驱动
- 任何 policy uplift 都能落到 benchmark evidence，而非会话直觉

## 6.7 Step 6 — Only then define extraction gate to `warning-core`

### Goal

在内部学习对象与 policy surfaces 稳定之后，再决定是否迁移到 `warning-core`。

### Extraction gate

只有满足下面条件时，迁移才开始变得高效：

1. `CaseStateLite` / assist / evidence / brief / action objects 已稳定
2. `3.5` 与 `3.6` 的优化不再主要依赖当前 repo 的历史叙事
3. external contracts 仍基本不变
4. policy compare / replay / governance surfaces 已稳定存在

### Why last

如果这些对象还没稳定就去 `warning-core`：

- 只会同时承受迁移成本与概念 churn
- 学习速度反而下降

## 7. What to do first, what to do next, what to do later

## 7.1 Do first

1. 冻结 scope 与 protected surfaces
2. 开 clean branch / worktree
3. 给 `3.5 / 3.6` 补 internal learning objects
4. 先补 audit / trace / evidence / brief persistence
5. 建立 baseline compare surfaces

## 7.2 Do next

1. 优化 `3.5 query rewrite / ambiguity / investigation value`
2. 优化 `3.5 calibration`
3. 把 `3.6` 改造成显式 action trace + stop policy
4. 让 premium invocation 受 value policy 控制
5. 用 replay / compare 验证 uplift

## 7.3 Do later

1. 统一更完整的 `CaseState`
2. 更显式的 `policy` module family
3. warning-core 抽离
4. runtime loop 重构

固定顺序：

```text
observe better
compare better
optimize policy
extract later
```

## 8. Allowed-touch surfaces vs protected surfaces

## 8.1 Allowed-touch surfaces

当前 family 允许优先触碰：

- `app/analyzer/*`
- `app/investigator/*`
- `app/benchmarks/*`
- `app/feedback/compare.py`
- `app/feedback/retrieval_refresh.py`
- `fixtures/*` 中的 replay / benchmark corpora
- `tests/test_fast_scorer.py`
- `tests/test_trained_scorer.py`
- `tests/test_investigator_*`
- `tests/test_benchmark.py`
- 新增针对 assist / audit / brief / action trace 的 tests
- `configs/thresholds.yaml`
- `configs/escalation.yaml`（只限 policy/budget tuning，不改 provider topology truth）

## 8.2 Narrow-touch only

下面 surfaces 只允许非常窄的 glue 变更：

- `app/runtime_entry.py`
- `app/main.py`
- `app/receiver/signoz_worker.py`

允许目的：

- emit internal learning artifacts
- attach compare metadata
- expose narrow replay hooks

不允许目的：

- 借机重写 runtime shell
- 借机重组 repo layout

## 8.3 Protected surfaces

下面 surfaces 默认不应成为本 family 主战场：

- `schemas/*`
- `app/packet/*`
- `app/reports/*`
- `app/delivery/*`
- `app/storage/*`
- `app/receiver/signoz_ingress.py`
- `app/receiver/signoz_queue.py`
- auth / ingress governance surfaces
- operator-facing delivery contracts
- report section order / frontmatter contract

## 9. Absolute do-not-touch list

以下事项在本 family 中应视为 **绝对不要碰**。

1. **不要重命名 canonical contracts**
   - 不改 `incident-packet.v1`
   - 不改 `local-analyzer-decision.v1`
   - 不改 `investigation-result.v1`
   - 不改 `alert-report.v1`
   - 不改 `incident-outcome.v1`

2. **不要同步重写 shell 和 brain**
   - 不要一边做学习优化，一边重做 ingress / storage / delivery / report

3. **不要让 premium 变成默认热路径**
   - premium 是 high-cost selected action，不是 every-alert solver

4. **不要让 `3.6` 结果直接反向塑造 truth**
   - premium / investigation 结果不能直接作为 training label

5. **不要为了“更智能”取消 boundedness**
   - 不放开 tool budget
   - 不让模型读 unbounded raw observability flood

6. **不要引入重基础设施平台**
   - 不引入 vector DB
   - 不引入 Kafka
   - 不引入 workflow engine
   - 不引入 multi-agent runtime

7. **不要在没有新 control-plane 的情况下 claim active execution**
   - 本文是 technical note，不是 active plan

8. **不要在当前 dirty 主线里直接堆改动**
   - 必须 clean lane first

## 10. Verification and step goals

## 10.1 `3.5` verification focus

必须至少能比较：

- severe recall
- false page rate
- investigation precision
- confidence calibration
- retrieval uplift from query rewrite
- expected-value-of-investigation quality

## 10.2 `3.6` verification focus

必须至少能比较：

- average useful tool calls per investigation
- stop-policy efficiency
- evidence sufficiency before premium
- premium invocation rate
- premium uplift per token / cost unit
- routing correctness
- report usefulness / operator acceptance proxy

## 10.3 Minimum success condition

本路线只有在下面情况同时成立时，才算成功：

1. `3.5 / 3.6` 变得更可学习，而不是只是多了一层 prose
2. 可以更明确地回答：
   - 哪个 action 有价值
   - 哪个 brief 有价值
   - 哪次 premium invocation 值得
3. external contracts、operator shell 与 governance 基线仍保持稳定
4. 后续若迁移到 `warning-core`，迁移的是 **已验证的 internal objects 和 policies**，而不是一堆仍在快速变化的概念

## 11. Final recommendation

最终建议固定为：

> 在 `warning-agent` 内继续做 `3.5 / 3.6` 的学习优化；
> 优化重点放在 internal learning objects、action trace、policy compare 与 outcome-governed feedback；
> 不要现在就同步开启 `warning-core` 重构执行。

一句话总结：

> **先让当前中枢变得可学习，再决定是否迁移；**
> **先学决策，再学结论；**
> **先做 attribution，再做 extraction。**
