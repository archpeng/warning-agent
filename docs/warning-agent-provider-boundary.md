# warning-agent provider boundary

## Current truth

`warning-agent` 当前的 investigation provider 仍是 **deterministic smoke boundary**，不是 live vendor adapter。

冻结配置见：

- `configs/escalation.yaml`
- `configs/provider-boundary.yaml`

## Boundary modes

### local_primary

- mode: `deterministic_smoke`
- normal path: 允许 bounded local investigation
- failure rule: **fail closed to `send_to_human_review`**

### cloud_fallback

- mode: `deterministic_smoke`
- normal path: 允许 bounded cloud handoff smoke review
- unavailable rule: **fail closed to `send_to_human_review`**

## Why this exists

在 real provider integration 落地前，repo 不能把 smoke provider 的成功路径误写成 production-safe vendor path。

因此当前规则是：

1. smoke provider 可以提供 bounded investigation proof
2. provider failure / unavailable 不能静默沿用原本 page/ticket action
3. provider failure 必须切到 `send_to_human_review`
4. closeout 前不得把此边界说成 live vendor ready

## Observable proof surfaces

- `tests/test_fallback.py`
- `tests/test_cloud_fallback.py`
- `tests/test_provider_boundary.py`

这些 tests 现在显式证明：

- degraded local fallback 会 fail closed 到 `send_to_human_review`
- cloud fallback unavailable 会 fail closed 到 `send_to_human_review`
- provider boundary mode 当前冻结为 `deterministic_smoke`
