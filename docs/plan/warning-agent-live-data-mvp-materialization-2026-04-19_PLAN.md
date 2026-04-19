# warning-agent live-data MVP materialization plan

- plan_id: `warning-agent-live-data-mvp-materialization-2026-04-19`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- current_wave: `closeout / live-data MVP complete`
- last_updated: `2026-04-19`

## 1. Goal

把当前 repo 从 replay-first evidence bundle runtime，提升为一个**诚实可运行的 live-data MVP**：

```text
alert/replay
  -> live Prometheus + SigNoz evidence collection
  -> incident packet
  -> local analyzer
  -> bounded live follow-up investigation
  -> markdown report
```

## 2. Final outcome

本 pack 已完成并 closeout。

closeout truth：

- live evidence query/config surface 已冻结
- runtime / webhook 已支持 explicit `fixture | live` evidence mode
- live packet 现在可以不依赖 `fixtures/evidence/*.json` 进入 packet -> analyzer -> report 主链路
- local-primary 现在可对 live refs 做 bounded Prometheus + SigNoz + repo follow-up
- live smoke / honest claim boundary / runbook 已落地
- runtime metadata 已同步到 terminal `live-data-mvp / none`

## 3. Honest claim boundary after closeout

当前 repo 现在可以诚实宣称：

- 已能从真实 Prometheus / SigNoz collector surface **自动取数并自动分析**
- 已具备 **bounded initial localization** 能力（当 live packet 进入 investigation 路径时）
- 已具备 **可演示 / 可试跑** 的 live-data MVP

当前 repo 仍不宣称：

- production rollout ready
- external operator admission plane
- unbounded root-cause exploration
- guaranteed real promotion / rollout

## 4. Successor rule

- 本 pack 到此终止，不再继续执行。
- 若要继续 external admission、真实更大规模 live query family 调优、production rollout 或 multi-env 发布，必须显式新开 successor pack。
