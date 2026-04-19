# warning-agent compounding learning loop plan

- plan_id: `warning-agent-compounding-learning-loop-2026-04-19`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- current_wave: `closeout / W4 complete`
- last_updated: `2026-04-19`

## 1. Goal

在 `W3 local trust upgrade` 已 honest closeout 之后，完成 `W4 compounding learning loop`：

- materialize outcome ingest path
- refresh retrieval and assemble training / compare corpus from landed outcomes
- retrain / evaluate / compare candidate local analyzers
- write explicit promote-or-hold decision with frozen governance / rollback truth

## 2. Governing truth

本 plan 的 SSOT 输入为：

- `docs/plan/warning-agent-local-trust-upgrade-2026-04-19_CLOSEOUT.md`
- `docs/future/warning-agent-local-trust-acceptance-and-minimal-upgrade.md`
- `docs/warning-agent-architecture.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/warning-agent-schema-draft.md`
- `data/models/local-analyzer-trained-scorer.v1.json`

## 3. Final outcome

W4 已 completed，closeout 证据见：

- `docs/plan/warning-agent-compounding-learning-loop-2026-04-19_CLOSEOUT.md`

closeout truth：

- `incident-outcome.v1` 已作为 feedback layer canonical artifact landed
- outcome ingest / persistence / metadata / retrieval refresh 已 materialize
- replay + landed outcome compare corpus 已可重复组装
- candidate retrain / compare summary 已 materialize
- promotion report + explicit hold decision 已落地
- cadence / rollback governance 已通过 config + docs freeze
- runtime metadata drift 已修正为 terminal `feedback-governance / none`

## 4. Successor rule

- `W4` 到此终止，不再继续执行。
- `docs/future/*` 当前 roadmap 已收口；若要继续推进新的 learning / rollout / external admission 能力，必须显式 replan。
- 下一控制面动作若存在，只能在新的 successor pack 中定义。
