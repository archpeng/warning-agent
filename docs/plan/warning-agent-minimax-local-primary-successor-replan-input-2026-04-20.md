# warning-agent minimax local-primary successor replan input

- status: `successor-input`
- predecessor_plan: `warning-agent-minimax-local-primary-real-adapter-2026-04-20`
- created_at: `2026-04-20`
- intended_handoff: `plan-creator`

## 1. Why this successor exists

前序 bounded pack 已完成：

- local-primary boundary/API-key contract freeze
- OpenAI-compatible real adapter client
- runtime auto-wiring
- schema-valid `InvestigationResult` mapping
- fail-closed proof

但它没有也不应该在同一 pack 内继续 claim：

- live `neko api:minimax-m2.7-highspeed` rollout readiness
- environment-specific auth/secret governance
- timeout / retry / latency budget calibration on a real endpoint
- broader model/runtime governance

## 2. Residuals carried forward

1. 缺少真实 local Neko endpoint 的 smoke / latency / auth evidence。
2. `WARNING_AGENT_LOCAL_PRIMARY_API_KEY` 语义虽然已冻结为 optional，但不同环境下是否需要 key 仍需 rollout-grade operator truth。
3. 当前 adapter 仅证明 bounded contract path landed；尚未证明 real endpoint 下的 long-tail failure modes（timeout、partial JSON、non-2xx）在 operator expectations 下可接受。
4. 若未来要同时治理 local-primary 与 cloud-fallback 的真实 provider rollout，应该升格到更广的 model/runtime governance pack，而不是继续塞进这个 bounded adapter pack。

## 3. Safe next themes

### theme A — live local-primary rollout proof

目标：

- 在真实 `neko api:minimax-m2.7-highspeed` endpoint 下补 live smoke / auth / latency evidence

边界：

- 不改 canonical investigation contract
- 不扩成 generic multi-provider SDK

### theme B — model/runtime governance hardening

目标：

- 把 local-primary / cloud-fallback 的 real provider rollout truth、secret handling、timeout budgets、operator guardrails 收到统一 successor pack

边界：

- 仍保持 `warning-agent` 为 bounded alert investigation runtime
- 不进入 remediation / workflow / orchestration

## 4. Recommended next handoff

推荐默认进入 `plan-creator`，由新 successor pack 决定：

- 是否只做 `live local-primary rollout proof`
- 还是进入更广的 `model/runtime governance` hardening
