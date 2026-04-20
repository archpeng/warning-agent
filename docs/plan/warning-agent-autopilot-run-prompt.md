# warning-agent autopilot run prompt

- status: `active-helper`
- purpose: 用于在新会话里先读取 repo-local active control-plane，识别当前 active pack 是否仍可执行；若 active pack 已 terminal closeout，则转入 successor replan，而不是继续在旧 pack 内执行
- last_updated: `2026-04-20`

## 当前 pack 状态

当前 active source pack：

- `docs/plan/warning-agent-minimax-local-primary-real-adapter-2026-04-20_PLAN.md`
- `docs/plan/warning-agent-minimax-local-primary-real-adapter-2026-04-20_STATUS.md`
- `docs/plan/warning-agent-minimax-local-primary-real-adapter-2026-04-20_WORKSET.md`

当前 machine truth：

- `docs/plan/README.md`
- `docs/plan/active_PLAN.md`
- `docs/plan/active_STATUS.md`
- `docs/plan/active_WORKSET.md`

当前 active pack 已处于：

- terminal slice: `MM.RV1`
- verdict: `accept_with_residuals`
- intended handoff: `plan-creator`

因此，**不要继续在这个 pack 内做 execute-plan**。

## 新会话默认提示词

在仓库根目录启动新会话后，直接粘贴下面整段提示词。

---

你现在在仓库 `/home/peng/dt-git/github/warning-agent` 中继续 `warning-agent` 的 autopilot 工作。

先做这些事：

1. 读取 `docs/plan/README.md`
2. 读取 `docs/plan/active_PLAN.md`
3. 读取 `docs/plan/active_STATUS.md`
4. 读取 `docs/plan/active_WORKSET.md`
5. 读取当前 source pack 与 closeout artifacts：
   - `docs/plan/warning-agent-minimax-local-primary-real-adapter-2026-04-20_PLAN.md`
   - `docs/plan/warning-agent-minimax-local-primary-real-adapter-2026-04-20_STATUS.md`
   - `docs/plan/warning-agent-minimax-local-primary-real-adapter-2026-04-20_WORKSET.md`
   - `docs/plan/warning-agent-minimax-local-primary-real-adapter-2026-04-20_CLOSEOUT.md`
   - `docs/plan/warning-agent-minimax-local-primary-successor-replan-input-2026-04-20.md`

然后遵守以下规则：

- 如果 machine/source control-plane 仍显示当前 pack 停在 `MM.RV1` terminal truth，下一步默认是 `plan-creator`
- 只允许围绕 successor residuals 创建新的 bounded pack
- 不要继续在 `warning-agent-minimax-local-primary-real-adapter-2026-04-20` pack 内追加 execution
- 若需要 live local-primary rollout proof、auth/secret governance、timeout/latency calibration，必须写入新的 successor plan/status/workset

local extension mode 仍有 clean-start 要求：

- 新 session 的第一次 `/autopilot-run` 需要 clean repo state
- 若 repo 已 dirty，先 checkpoint / 清理，再启动新的 local autopilot run

你的目标不是继续旧 slice，而是：

- 尊重 current terminal truth
- 读取 residuals / successor input
- 创建新的 parser-compatible successor pack
- 同步 `docs/plan/README.md` + `active_*`
- 为下一个 bounded workstream 设定新的 active slice 与 intended handoff

---
