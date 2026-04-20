# warning-agent Local Autopilot Clean-Start Runbook

- status: `active-runbook-ssot`
- scope:
  - local `pi-sdk` extension-mode startup
  - repo-local machine control-plane preflight
  - dirty-repo clean-start policy
  - same-session resume policy
- owner: `operator / repo maintainer`
- last_updated: `2026-04-20`

## 1. Current truth

`warning-agent` 的 local autopilot 现在依赖两层 truth：

### 1.1 machine control-plane

固定入口：

- `docs/plan/README.md`
- `docs/plan/active_PLAN.md`
- `docs/plan/active_STATUS.md`
- `docs/plan/active_WORKSET.md`

这层 truth 供 `pi-sdk` local autopilot extension 读取 / 写回。

### 1.2 richer source pack

当前 source pack：

- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_PLAN.md`
- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_STATUS.md`
- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_WORKSET.md`

这层 truth 供人类执行、审阅、replan、closeout 使用。

### 1.3 hard rule

在 local mode 下：

1. **第一次** `/autopilot-run` 需要从 clean repo state 启动。
2. 同一 session 内已经开始的 autopilot，可在 dirty worktree 上继续 redispatch；dirty-repo initial-run guard 主要拦的是 **new local run**。
3. 若 machine pack 与 richer source pack 漂移，先修 control-plane，再启动 autopilot。

## 2. Start decision table

| Situation | Action | Why |
|---|---|---|
| 新 session + clean repo | `/autopilot-run <goal>` | 满足 local clean-start gate |
| 同一 session 已 paused / running | `/autopilot-resume` | 不要把 same-session continuation 误当成新 run |
| 新 session + dirty repo + 这些改动值得保留 | 先做 checkpoint commit，再 `/autopilot-run` | 最稳定、最可恢复 |
| 新 session + dirty repo + 改动还不值得提交 | 先整理 / 丢弃 / 导出 patch，恢复 clean tree 后再启动 | local guard 不会替你兜底 |
| `/autopilot-status` 命令不存在 | 先修 `pi-sdk` package autoload / install，再继续 | extension 没加载时 runbook 其余步骤无意义 |
| machine pack 与 source pack 不一致 | 先同步 `docs/plan/README.md` + `active_*` | extension 只信 repo-local machine control-plane |

## 3. Clean-start gate

只有以下同时成立，才算允许开始新的 local autopilot run：

1. 当前目录是 repo root：`/home/peng/dt-git/github/warning-agent`
2. `git status --short` 为空
3. machine control-plane 四个文件存在
4. machine pack 当前 active slice 与 richer source pack 当前 active slice 一致
5. `tests/test_autopilot_control_plane.py` 通过
6. 当前 active slice 没有被 richer source pack 明确标成 blocked / successor-only
7. Pi session 内已加载 `pi-sdk` autopilot commands

## 4. Canonical preflight commands

从 repo root 执行：

```bash
git status --short
uv run pytest tests/test_autopilot_control_plane.py
rg -n "Current Active Slice|active_step:|active_slice:" \
  docs/plan/README.md \
  docs/plan/active_STATUS.md \
  docs/plan/warning-agent-production-integration-bridge-2026-04-20_WORKSET.md
```

预期：

- `git status --short` 无输出
- `tests/test_autopilot_control_plane.py` 通过
- grep 结果能证明：
  - `README.md` 指向的 current active slice
  - `active_STATUS.md` 的 `active_step`
  - richer source pack 的 `active_slice`
  三者仍然对齐

## 5. Canonical fresh-start procedure

### 5.1 最稳的启动方式

```bash
cd /home/peng/dt-git/github/warning-agent
git status --short
uv run pytest tests/test_autopilot_control_plane.py
pi
```

进入 Pi 后先确认 command surface：

```text
/autopilot-status
```

若 command 可用，再启动：

```text
/autopilot-run land the current active slice from docs/plan/README.md and continue serially until blocker, closeout, or mandatory replan
```

### 5.2 启动后的 operator 约束

- 不要在 run 刚开始后立刻新开第二个 `/autopilot-run`
- 让 extension 按 repo-local control-plane serially dispatch
- 若需要人工中断，用 `/autopilot-pause` 或 `/autopilot-stop`
- 若只是同一 session 继续，不要重新 clean-start；用 `/autopilot-resume`

## 6. Dirty-repo recovery policy

### 6.1 Preferred path: checkpoint commit

这是默认推荐路径。

```bash
cd /home/peng/dt-git/github/warning-agent
git switch -c autopilot/$(date +%Y%m%d-%H%M)-checkpoint
git add -A
git commit -m "checkpoint: pre-autopilot clean start"
git status --short
```

然后再跑 clean-start preflight。

原因：

- state 可恢复
- diff 可审计
- 不把关键上下文藏进 stash
- 最适合 repeated local autopilot startup

### 6.2 Fallback path: export patch or stash

仅当你明确不想提交 checkpoint 时使用。

```bash
git diff > /tmp/warning-agent-pre-autopilot.patch
# 或者
# git stash push -u -m "warning-agent pre-autopilot clean start"
```

然后把 worktree 清回 clean state，再启动 local autopilot。

注意：

- `stash` 不是首选，因为它会把 operator context 藏起来
- 若使用 `stash`，恢复后必须重新核对 machine pack 与 source pack 是否仍一致

### 6.3 Never do this

不要期待下面这类启动会“自动工作”：

- repo 已 dirty，但直接新开 `/autopilot-run`
- machine pack 已过时，但只靠会话上下文让 autopilot “自己理解”
- richer source pack 更新了 active slice，但没同步 `docs/plan/README.md` / `active_*`

## 7. Same-session continuation rule

以下情况优先使用 `/autopilot-resume`，**不要** 当成 fresh start：

1. 同一 Pi session 里你只是 pause 了 autopilot
2. 同一 session 经过 compaction / tree navigation 后仍保留 runtime state
3. 当前 session 已经有 autopilot runtime entry，只是需要继续 dispatch

最小操作：

```text
/autopilot-status
/autopilot-resume
```

只有在以下情况才重新做 clean-start：

- 上一个 run 已 closed out
- 你开了全新 session
- 你要基于新的 clean checkpoint 重新开始 local mode

## 8. End-of-run checkpoint rule

每次 autopilot 因为 `pause / stop / blocked / closeout` 停下来后，先做这三件事：

1. 检查 richer source pack：
   - `docs/plan/warning-agent-production-integration-bridge-2026-04-20_STATUS.md`
   - `docs/plan/warning-agent-production-integration-bridge-2026-04-20_WORKSET.md`
2. 检查 machine pack：
   - `docs/plan/README.md`
   - `docs/plan/active_STATUS.md`
   - `docs/plan/active_WORKSET.md`
3. 再决定：
   - 立刻继续同一 session → `/autopilot-resume`
   - 换 session 稍后继续 → 先做 checkpoint commit，确保下次 clean-start 稳定

最稳的结束动作：

```bash
git add -A
git commit -m "checkpoint: post-autopilot <slice-or-closeout>"
```

## 9. Failure matrix

| Symptom | Meaning | Action |
|---|---|---|
| `repo-local active control-plane required for extension-driven autopilot in local mode` | extension 读不到 machine control-plane | 先修 `docs/plan/README.md` + `active_*` |
| `dirty repo guard: ... has N dirty files` | 你在 new local run 前就已经 dirty | 先 checkpoint commit / patch backup / 清理，再重新启动 |
| `/autopilot-status` 不存在 | `pi-sdk` extension 没加载 | 先修 package install / autoload |
| accepted slice 完成了，但没有自动切到下一 slice | machine writeback 或 parser truth 漂移 | 重新跑 `uv run pytest tests/test_autopilot_control_plane.py`，核对 `README.md`、`active_STATUS.md`、`active_WORKSET.md` |
| richer source pack 已切到新 slice，但 machine pack 还停在旧 slice | source/machine pack 漂移 | 先同步 machine pack，再启动或 resume |
| 同一 session 只是 pause 后不想继续 | operator stop，不是 control-plane fault | `/autopilot-stop` 或直接结束 session |

## 10. Stable operator policy

如果目标是“每次都能稳定启动 local autopilot”，默认采用这套策略：

1. **一个 active pack**：所有 run 都服从 `docs/plan/README.md`
2. **一个 serial active slice**：不并行抢跑多个 slice
3. **一次新 session = 一次 clean-start**
4. **session 之间用 checkpoint commit 交接**，不要默认靠 dirty worktree 续做
5. **同一 session 内优先 resume，不要反复 fresh-start**
6. **machine pack 先对齐，再让 extension 调度**

## 11. Minimum daily loop

最小稳定日常循环：

```text
finish current operator edits
  -> checkpoint commit
  -> git status clean
  -> run control-plane preflight
  -> pi
  -> /autopilot-run ...
  -> let same-session redispatch continue
  -> pause/stop/closeout
  -> review richer + machine packs
  -> checkpoint commit again
```

这条循环的关键不是“零 dirty”，而是：

> **new local run 前 clean；same-session 继续时 resume；session 之间用 checkpoint commit 交接。**
