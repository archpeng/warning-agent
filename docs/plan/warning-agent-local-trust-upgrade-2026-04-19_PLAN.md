# warning-agent local trust upgrade plan

- plan_id: `warning-agent-local-trust-upgrade-2026-04-19`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- current_wave: `closeout / W3 complete`
- last_updated: `2026-04-19`

## 1. Goal

在 `W2 runtime materialization` 已 honest closeout 之后，进入 `W3 local trust upgrade`：

- 冻结可重复 benchmark surface
- 引入 packet temporal context v2 与时序特征
- 落 learned scorer + calibration
- 升级 routing / handoff correctness

W3 的目标不是再接 runtime glue，而是提升 **本地判断可信度**。

## 2. Governing truth

本 plan 的 SSOT 输入固定为：

- `docs/plan/warning-agent-runtime-materialization-2026-04-19_CLOSEOUT.md`
- `docs/future/warning-agent-local-trust-acceptance-and-minimal-upgrade.md`
- `docs/warning-agent-architecture.md`
- `docs/analyse/warning-agent-local-first-investigation-path.md`
- 当前 benchmark truth：
  - `data/benchmarks/local-analyzer-baseline-summary.json`
  - `data/benchmarks/local-primary-baseline-summary.json`
  - `data/benchmarks/cloud-fallback-baseline-summary.json`

## 3. Final outcome

W3 已 completed，closeout 证据见：

- `docs/plan/warning-agent-local-trust-upgrade-2026-04-19_CLOSEOUT.md`

closeout truth：

- benchmark surface 已冻结并可重复生成
- packet temporal context / feature extraction 已 landed
- trained scorer 已真实进入 runtime + benchmark path
- routing / handoff correctness 已有实际 benchmark truth
- successor residuals 已明确 handoff 到 W4 planning，而不是遗留在 W3 实现面内

## 4. Successor rule

- W3 到此终止，不再继续执行。
- 下一控制面动作是：`plan-creator` 生成 W4 新 pack。
- 在新的 W4 pack 出现前，不得 claim W4 active execution。
