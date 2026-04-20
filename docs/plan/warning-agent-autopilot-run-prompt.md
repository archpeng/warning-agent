# warning-agent autopilot run prompt

- status: `active-helper`
- purpose: 用于在新会话里尽可能自动、连续、证据驱动地推进 `warning-agent` 当前 active pack，直到命中 closeout、replan 或 blocker 边界
- last_updated: `2026-04-20`

## How to use

在仓库根目录启动新会话后，直接粘贴下面整段提示词。

---

你现在在仓库 `/home/peng/dt-git/github/warning-agent` 中执行 `warning-agent` 的 autopilot run。

你的总目标不是做分析停留，而是：

- 严格遵守 repo-local active control-plane
- 尽可能自动推进当前 active slice
- 在同一 run 中，只要安全且无歧义，就持续推进到下一个 slice / 下一个 phase
- 直到命中以下任一条件才停止：
  - 当前 slice blocker 无法在边界内解决
  - phase closeout gate 不满足
  - 命中 mandatory replan rule
  - 需要越过产品 non-goals 才能继续
  - 缺乏可验证 evidence

## local extension mode 前置要求

1. repo-local active control-plane 以以下文件为机器真相：
   - `docs/plan/README.md`
   - `docs/plan/active_PLAN.md`
   - `docs/plan/active_STATUS.md`
   - `docs/plan/active_WORKSET.md`
2. richer human/source pack 仍是：
   - `docs/plan/warning-agent-production-integration-bridge-2026-04-20_PLAN.md`
   - `docs/plan/warning-agent-production-integration-bridge-2026-04-20_STATUS.md`
   - `docs/plan/warning-agent-production-integration-bridge-2026-04-20_WORKSET.md`
3. local mode 的第一次 `/autopilot-run` 需要从 clean repo state 启动；如果 repo 在启动前已经 dirty，预期会命中 dirty-repo initial-run guard。

## 必须先读的 source-of-truth

先读并以它们为唯一总控：

1. `docs/plan/README.md`
2. `docs/plan/active_PLAN.md`
3. `docs/plan/active_STATUS.md`
4. `docs/plan/active_WORKSET.md`
5. `docs/plan/warning-agent-production-integration-bridge-2026-04-20_PLAN.md`
6. `docs/plan/warning-agent-production-integration-bridge-2026-04-20_STATUS.md`
7. `docs/plan/warning-agent-production-integration-bridge-2026-04-20_WORKSET.md`
8. 当前 active slice 点名的 governing docs

必要时再读：

- `README.md`
- `docs/warning-agent-architecture.md`
- `docs/warning-agent-schema-draft.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/warning-agent-provider-boundary.md`
- `docs/analyse/*`

## 执行优先级

1. 先遵守 `README.md` 指向的 `active_WORKSET.active stage`
2. 再遵守 `active_PLAN` 中的 closeout / stop rules
3. 再用 richer source pack 核对 current truth、latest evidence、blockers
4. 优先使用 control-plane、bb-memory、SigNoz、HTTP 探针等 source-of-truth
5. 只有在 source-of-truth 不足时才扩展到 repo 深读

## 严格执行循环

对每个 active slice，必须按这个循环：

```text
read README + active_PLAN/STATUS/WORKSET
  -> read richer source pack + governing docs
  -> execute exactly one active slice
  -> run matching validation
  -> update richer STATUS/WORKSET with concrete evidence
  -> update active_STATUS/WORKSET only if current slice is truly closed
  -> if phase closeout satisfied, advance phase/wave
  -> else continue serially
```

## 自动推进规则

### 1. 默认连续推进

如果以下条件同时成立，则继续推进：

- 当前 slice 已有明确 deliverable
- 对应 validation 已运行并有 evidence
- richer source pack 与 active machine pack 已同步
- 下一 slice 已经在 `active_WORKSET` 中明确、无优先级歧义、无新增 SSOT 缺口

### 2. 只允许串行，不允许并行抢跑

- 任意时刻只能执行一个 `active_slice`
- 不得提前 claim queued slice done
- 可以为下一 slice 读取少量上下文，但不得越过 current slice 的 done-when boundary

### 3. W6 当前终点

当前 active pack 的默认终点是：

- `W6.S4a`
- `W6.RV1`
- `W6 closeout / W7 replan input`

完成 `W6.RV1` 后：

- 先 reality audit / closeout
- 如需推进新的 rollout / governance / post-rollout work，必须进入显式 successor replan

## 强制 stop / replan 条件

命中以下任一项时，不要硬顶，直接转 `replan`：

- 需要跨入 remediation / workflow engine / multi-agent / UI suite
- 当前 slice 出现两个同级主目标
- 验证路径不存在或跑不通
- 当前 gate 明显失败，且不属于本 slice 局部修复
- 环境 reality 与现有 phase 设计冲突
- 必须修改 W6 边界才能继续
- 完成 `W6.RV1` 后还想继续自动推进

## 输出与状态回写要求

每完成一个 slice，必须最少做这些事：

1. 更新 richer `STATUS`
2. 更新 richer `WORKSET`
3. 更新 machine `active_STATUS` / `active_WORKSET`
4. 若发生 wave / gate 变化，必要时更新 richer `PLAN`
5. 在最终回复中明确：
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

- 从 `docs/plan/README.md` 指向的 `active_WORKSET.Active Stage` 开始执行
- richer source pack 与 active machine pack 若不一致，先修复 control-plane 再执行
- 若 repo 预先 dirty 且仍要使用 local mode，先 checkpoint / 清理，否则预期会被 guard 停止

现在开始：先读取 `docs/plan/README.md` 和 active pack，再从当前 active slice 连续推进。

---
