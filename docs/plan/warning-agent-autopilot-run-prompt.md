# warning-agent autopilot run prompt

- status: `active-helper`
- purpose: 用于在新会话里尽可能自动、连续、证据驱动地推进 `warning-agent` master plan，直到命中 closeout、replan 或 blocker 边界
- last_updated: `2026-04-19`

## How to use

在仓库根目录启动新会话后，直接粘贴下面整段提示词。

---

你现在在仓库 `/home/peng/dt-git/github/warning-agent` 中执行 `warning-agent` 的 autopilot run。

你的总目标不是做分析停留，而是：

- 严格遵守现有 master plan
- 尽可能自动推进当前 active slice
- 在同一 run 中，只要安全且无歧义，就持续推进到下一个 slice / 下一个 phase
- 直到命中以下任一条件才停止：
  - 当前 slice blocker 无法在边界内解决
  - phase closeout gate 不满足
  - 命中 mandatory replan rule
  - 需要越过产品 non-goals 才能继续
  - 缺乏可验证 evidence

## 必须先读的 source-of-truth

先读并以它们为唯一总控：

1. `docs/plan/warning-agent-autopilot-delivery-2026-04-18_PLAN.md`
2. `docs/plan/warning-agent-autopilot-delivery-2026-04-18_STATUS.md`
3. `docs/plan/warning-agent-autopilot-delivery-2026-04-18_WORKSET.md`
4. 当前 active slice 点名的 governing docs

必要时再读：

- `README.md`
- `docs/warning-agent-architecture.md`
- `docs/warning-agent-schema-draft.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/warning-agent-minimal-repo-skeleton.md`
- `docs/analyse/warning-agent-local-first-investigation-path.md`
- `docs/analyse/*`

## 执行优先级

1. 先遵守 `WORKSET.active_slice`
2. 再遵守 `PLAN` 中的 closeout / numeric gates / stop rules
3. 再在 `STATUS` 中核对 current truth、latest evidence、blockers
4. 优先使用 control-plane、bb-memory、SigNoz、HTTP 探针等 source-of-truth
5. 只有在 source-of-truth 不足时才扩展到 repo 深读

## 严格执行循环

对每个 active slice，必须按这个循环：

```text
read PLAN/STATUS/WORKSET
  -> execute exactly one active slice
  -> run matching validation
  -> update STATUS with concrete evidence
  -> update WORKSET to next active slice only if current slice is truly closed
  -> if phase closeout satisfied, advance phase/wave
  -> else continue serially
```

## 自动推进规则

### 1. 默认连续推进

如果以下条件同时成立，则继续推进：

- 当前 slice 已有明确 deliverable
- 对应 validation 已运行并有 evidence
- `STATUS` / `WORKSET` 已同步
- 下一 slice 已经在 `WORKSET` 中明确、无优先级歧义、无新增 SSOT 缺口

### 2. 只允许串行，不允许并行抢跑

- 任意时刻只能执行一个 `active_slice`
- 不得提前 claim queued slice done
- 可以为下一 slice 读取少量上下文，但不得越过 current slice 的 done-when boundary

### 3. `P5` 后默认停止

`P5` 是当前主计划的默认终点。

完成 `P5` 后：

- 先 closeout
- 如需推进 shadow / rollout / small-model replacement，必须进入显式 replan

## 强制 stop / replan 条件

命中以下任一项时，不要硬顶，直接转 `replan`：

- 需要跨入 remediation / workflow engine / multi-agent / UI suite
- 当前 slice 出现两个同级主目标
- 验证路径不存在或跑不通
- 当前 numeric gate 明显失败，且不属于本 slice 局部修复
- 环境 reality 与现有 phase 设计冲突
- 必须修改 master-plan 边界才能继续
- `P5` 后还想继续自动推进

## 输出与状态回写要求

每完成一个 slice，必须最少做这些事：

1. 更新 `STATUS`
2. 更新 `WORKSET`
3. 若发生 phase 切换或 gate 变化，必要时更新 `PLAN`
4. 在最终回复中明确：
   - 完成了哪些 slice
   - 运行了哪些验证
   - 当前 active slice 是什么
   - 是否进入 replan / closeout

## 产品边界红线

`warning-agent` 产品 runtime 严禁漂移到：

- remediation / 自动执行
- workflow engine
- multi-agent orchestration
- observability suite
- general agent runtime

autopilot 只属于项目交付控制面，不属于产品执行面。

## 本 run 的启动要求

- 从 `WORKSET.active_slice` 开始执行
- 若 `P1` 已全部完成，则直接进入 `P2`
- 若 `P5` 已完成，则停止并进入 closeout / replan 判断

现在开始：先读取 master plan / status / workset，并从当前 active slice 连续推进。

---
