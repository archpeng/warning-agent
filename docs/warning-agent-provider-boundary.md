# warning-agent provider boundary

## Current truth

`warning-agent` 的 investigator plane 现在已经进入 **runtime-gated provider boundary**：

- default path 仍是 deterministic smoke provider
- future real adapter contract 已冻结在 config
- runtime 现在会显式解析 env-opt-in gate
- gate missing/client missing 时会显式 fail closed，而不是静默 pretend live-ready

当前 SSOT：

- `configs/escalation.yaml`
- `configs/provider-boundary.yaml`
- `app/investigator/provider_boundary.py`

## Current active smoke providers

| provider | default mode | active smoke identity | fail-closed action |
|---|---|---|---|
| `local_primary` | `deterministic_smoke` | `local_vllm / local-primary-smoke` | `send_to_human_review` |
| `cloud_fallback` | `deterministic_smoke` | `openai / cloud-fallback-smoke` | `send_to_human_review` |

这表示：

1. repo 默认仍运行 smoke provider，不会因配置文件存在 real adapter contract 就自动切到 live path。
2. `investigation-result.v1` 的默认 `model_name` 仍诚实表明当前 smoke 身份。
3. real adapter gate 只有在 opt-in env 明确满足时才会进入 ready state。

## Frozen real adapter contracts

以下 contract 已冻结，并已接到 runtime gate；但 **仍是 local-proof / env-opt-in seam，不是 production rollout claim**。

| provider | frozen real adapter | transport | activation seam | required env seam | timeout |
|---|---|---|---|---|---|
| `local_primary` | `local_vllm_openai_compat` | `openai_compatible_http` | `env_opt_in` via `WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED` | `WARNING_AGENT_LOCAL_PRIMARY_BASE_URL`, `WARNING_AGENT_LOCAL_PRIMARY_MODEL` | `45s` |
| `cloud_fallback` | `openai_responses_api` | `openai_responses_api` | `env_opt_in` via `WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED` | `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `WARNING_AGENT_CLOUD_FALLBACK_MODEL` | `90s` |

runtime gate semantics：

1. gate off → `smoke_default`
2. gate on but env missing → explicit fail-closed fallback
3. gate ready but runtime client missing → explicit fail-closed fallback
4. gate ready + injected client → local proof path can consume the frozen real adapter contract

## Why this boundary exists

在 real provider integration 真正 rollout 前，repo 不能把 smoke provider 的成功路径误写成 production-safe vendor path。

因此当前规则固定为：

1. smoke provider 继续承担默认 bounded investigation proof。
2. real adapter contract 先通过 env gate 接到 runtime，但不代表 remote vendor rollout 已完成。
3. provider missing env / missing client / unavailable path 必须显式 fail closed。
4. 没有 `W6.S4a` rollout evidence 和后续 reality audit 前，不得 claim live provider ready。

## Observable proof surfaces

- `tests/test_provider_boundary.py`
- `tests/test_local_primary.py`
- `tests/test_cloud_fallback.py`
- `tests/test_investigation_runtime.py`

这些 proof 现在覆盖：

- current smoke identity 与 future real adapter contract 同时可加载
- env gate 的 `smoke_default / missing_env / ready` 状态可直接证明
- `local_primary` gate ready 时可消费 injected real adapter provider；env missing 时显式 fail closed
- `cloud_fallback` gate ready 时可消费 injected real adapter client；client missing 时 runtime 显式 fail closed
- fail-closed action 仍固定为 `send_to_human_review`
