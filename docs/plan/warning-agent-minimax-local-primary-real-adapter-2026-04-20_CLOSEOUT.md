# warning-agent minimax local-primary real adapter closeout

- plan_id: `warning-agent-minimax-local-primary-real-adapter-2026-04-20`
- closeout_date: `2026-04-20`
- verdict: `accept_with_residuals`
- next_handoff: `plan-creator`

## 1. Scope audited

审计对象：`MM local-primary real adapter` bounded successor pack。

claimed outcomes：

- `local_primary.real_adapter` 的 boundary/env contract 已从 implicit seam 冻结为 explicit contract
- local-primary 已具备 bounded `OpenAI-compatible HTTP` real adapter client
- `LocalPrimaryInvestigator` 在 gate=`ready` 且未显式注入 fake provider 时会自动装配 real provider
- real adapter path 会直接产出 schema-valid `InvestigationResult`
- upstream unavailable / env missing 等 failure path 仍显式 fail closed
- 当前 pack 已在 bounded seam 内闭合，而没有扩到 cloud rollout / generic SDK platform

## 2. Findings

### confirmed

1. boundary contract 已显式冻结：
   - `configs/provider-boundary.yaml` 现在把 local-primary 的 API key contract 固定为：
     - `WARNING_AGENT_LOCAL_PRIMARY_API_KEY`
     - `api_key_mode: optional`
   - cloud fallback 继续保持 `OPENAI_API_KEY` + `api_key_mode: required`
   - `app.investigator.provider_boundary` 现在能诚实表达 `not_used / optional / required` 语义，而不是把所有非空 `api_key_env` 都当成 required
2. bounded real adapter client 已真实落地：
   - `app/investigator/local_primary_openai_compat.py` 已 landed
   - provider 只消费 bounded `InvestigationRequest`
   - provider 通过 OpenAI-compatible `chat/completions` path 请求模型，并直接映射为 `InvestigationResult`
3. runtime auto-wiring 已真实落地：
   - `app/investigator/local_primary.py` 新增 real provider builder
   - gate=`ready` 时，runtime 不再强制依赖外部 injected fake provider
   - `run_investigation_runtime(...)` 现在可经由 `LocalPrimaryInvestigator.from_config(...)` 自动走到 real adapter seam
4. fail-closed behavior 仍被保留：
   - env 缺失仍进入 explicit degraded local fallback
   - real adapter upstream unavailable 时也会显式 fail closed，而不是静默伪装成功
5. optional env-opt smoke surface 已补齐：
   - `app/live_local_primary_smoke.py` 提供了一个 bounded checkout replay smoke harness
   - `docs/warning-agent-provider-boundary.md` 已记录 local-primary env seam 与 smoke usage note
6. full validation / hygiene 通过：
   - `uv run pytest` → `179 passed`
   - `uv run ruff check app tests scripts` → pass

### drift fixed

1. predecessor drift：local-primary 之前只能在 gate ready 时消费 injected fake provider，runtime 无法自动装配真实 provider。
2. predecessor drift：local-primary 之前没有 explicit API-key env contract，无法诚实表达“有 env 名称但仍是 optional”这种语义。
3. predecessor drift：repo 之前没有 bounded local-primary OpenAI-compatible provider module，也没有 schema-valid result mapping proof。

### uncertain

1. 尚未拿真实本地 `neko api:minimax-m2.7-highspeed` endpoint 做 live smoke / latency / auth proof。
2. 尚未对 live endpoint 下的 timeout / retry / budget calibration 做 operator-grade audit。

## 3. Evidence added / reused

### targeted tests

- `uv run pytest tests/test_provider_boundary.py tests/test_local_primary.py tests/test_local_primary_openai_compat.py tests/test_investigation_runtime.py`

### direct proof

- local-primary contract 现在显式区分：
  - gate off → `smoke_default`
  - gate on + endpoint/model missing → `missing_env`
  - gate on + optional API key omitted → 仍可 `ready`
  - gate on + cloud required API key omitted → `missing_env`
- real adapter path 现在可在 fake OpenAI-compatible response 下 materialize schema-valid `InvestigationResult`
- runtime path 现在可在 env ready 且无显式 injected provider 时 auto-wire real local-primary provider
- upstream unavailable 现在会显式回到 degraded local fallback

### full gates

- `uv run pytest` → `179 passed`
- `uv run ruff check app tests scripts` → pass

## 4. Fixes landed during this pack

- explicit API-key contract modes in `provider_boundary`
- local-primary `WARNING_AGENT_LOCAL_PRIMARY_API_KEY` optional env contract
- new bounded `local_primary_openai_compat` provider implementation
- local-primary runtime auto-wiring via ready gate
- env-opt smoke harness for bounded local-primary seam
- targeted unit/runtime tests and full regression proof

## 5. Successor residuals / replan input

1. 当前 pack 证明了 bounded seam 已 landed；**没有**证明真实 local Neko endpoint 已被 operator-grade live 验证。
2. 若要声称更强 rollout truth，后续 successor 应收敛到：
   - live endpoint smoke evidence
   - auth / secret handling by environment
   - timeout / retry / latency budget calibration on real endpoint
   - broader model/runtime governance（而不是继续改 current bounded adapter pack）
3. 当前 repo 现在可以诚实声称：
   - `local_primary real adapter seam landed`
   - **not** `full production-ready minimax rollout completed`

具体 successor input 见：

- `docs/plan/warning-agent-minimax-local-primary-successor-replan-input-2026-04-20.md`

## 6. Closeout verdict

本 pack 可以以 `accept_with_residuals` closeout。

理由：

- 当前 pack 的 contract freeze、bounded client、runtime auto-wiring、schema-valid mapping、fail-closed proof 都已有代码与测试证据支撑。
- remaining residuals 全都落在 live endpoint rollout / governance / calibration，而不是当前 bounded seam 未闭合。
- 当前 scope 内没有未证实的 landed claim。

## 7. Successor handoff

- 当前停止在 `MM.RV1` terminal truth。
- 若继续推进 live endpoint rollout 或 broader runtime governance，必须进入 successor planning；不得继续在当前 pack 中混做。
