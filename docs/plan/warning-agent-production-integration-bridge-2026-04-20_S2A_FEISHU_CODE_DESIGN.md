# warning-agent W6.S2a Feishu delivery code design

- status: `planning-support / queued-slice-prep`
- owner: `W6.S2a`
- plan_id: `warning-agent-production-integration-bridge-2026-04-20`
- parent_doc: `docs/plan/warning-agent-production-integration-bridge-2026-04-20_FEISHU_DELIVERY_BRIDGE.md`
- last_updated: `2026-04-20`

## 1. Scope of this design

本设计只覆盖 `W6.S2a live delivery adapter contract + env config seam`。

本设计明确 **不** 覆盖：

- real HTTP dispatch to `adapter-feishu`（这是 `W6.S2b`）
- `warning-agent` report polling API
- callback orchestration
- multi-provider matrix
- secret manager / deployment auth

S2a 的目标是把 `page_owner -> adapter_feishu` 的 contract、config、payload、env gate 和 artifact truth 冻结为可验证代码面。

## 2. File-level delta

### 2.1 Extend existing files

- `app/delivery/runtime.py`
- `configs/delivery.yaml`
- `tests/test_delivery.py`
- `tests/test_runtime_entry.py`
- `tests/test_alertmanager_webhook.py`

### 2.2 Add new files

- `app/delivery/adapter_feishu.py`
- `app/delivery/env_gate.py`
- `tests/test_delivery_adapter_feishu.py`

### 2.3 Do not add in S2a

以下文件留给 `W6.S2b`，S2a 不引入：

- `app/delivery/http_client.py`
- `app/delivery/bridge_result.py`

## 3. Exact type additions

### 3.1 `app/delivery/runtime.py`

```python
LocalDurableAdapter = Literal[
    "markdown_only",
    "local_ticket_queue",
    "local_page_queue",
    "local_review_queue",
]
LiveVendorAdapter = Literal["adapter_feishu"]
DeliveryAdapter = LocalDurableAdapter | LiveVendorAdapter
DeliveryMode = Literal["local_durable", "env_gated_live"]

@dataclass(frozen=True)
class LocalDurableRoute:
    delivery_class: DeliveryClass
    adapter: LocalDurableAdapter
    delivery_mode: Literal["local_durable"]
    queue: str

@dataclass(frozen=True)
class FeishuTargetEnvConfig:
    channel: Literal["feishu"]
    chat_id_env: str | None
    open_id_env: str | None
    thread_id_env: str | None

@dataclass(frozen=True)
class EnvGatedLiveRoute:
    delivery_class: DeliveryClass
    adapter: Literal["adapter_feishu"]
    delivery_mode: Literal["env_gated_live"]
    provider_key: Literal["warning-agent"]
    endpoint_env: str
    timeout_seconds: int
    target: FeishuTargetEnvConfig

DeliveryRoute = LocalDurableRoute | EnvGatedLiveRoute

@dataclass(frozen=True)
class DeliveryConfig:
    routes: dict[DeliveryClass, DeliveryRoute]

@dataclass(frozen=True)
class DeliveryDispatchResult:
    record: dict[str, object]
    dispatch_path: Path
    payload_path: Path
    bridge_payload_path: Path | None = None
```

Design rules:

1. `LocalDurableRoute` 保持 W5 语义：本地 durable queue truth。
2. `EnvGatedLiveRoute` 只支持 `adapter = "adapter_feishu"`。
3. `page_owner` 是 S2a 唯一允许转成 `EnvGatedLiveRoute` 的 delivery class。
4. `DeliveryDispatchResult.bridge_payload_path` 只在 `env_gated_live` + env ready 时非空。

### 3.2 `app/delivery/env_gate.py`

```python
EnvGateState = Literal["ready", "missing_env"]

@dataclass(frozen=True)
class ResolvedFeishuTarget:
    channel: Literal["feishu"]
    chat_id: str | None = None
    open_id: str | None = None
    thread_id: str | None = None

@dataclass(frozen=True)
class EnvGatedLiveResolution:
    state: EnvGateState
    endpoint: str | None
    target: ResolvedFeishuTarget | None
    missing_env: tuple[str, ...]
```

### 3.3 `app/delivery/adapter_feishu.py`

```python
AdapterFeishuSeverity = Literal["info", "warning", "critical"]

@dataclass(frozen=True)
class AdapterFeishuFact:
    label: str
    value: str

@dataclass(frozen=True)
class AdapterFeishuTarget:
    channel: Literal["feishu"]
    chatId: str | None = None
    openId: str | None = None
    threadId: str | None = None

@dataclass(frozen=True)
class AdapterFeishuNotificationPayload:
    providerKey: Literal["warning-agent"]
    reportId: str
    runId: str
    summary: str
    title: str
    occurredAt: str
    severity: AdapterFeishuSeverity
    bodyMarkdown: str
    target: AdapterFeishuTarget
    facts: tuple[AdapterFeishuFact, ...]
```

Design rules:

1. `runId` 在 S2a 固定取 `packet_id`。
2. `providerKey` 必须显式写成 `warning-agent`，即使 adapter 有 default provider。
3. `reportUrl` / `incidentId` / `actions` 在 S2a 不进 payload dataclass。
4. `facts` 只放 operator-facing短字段；不要把全 packet dump 进去。

## 4. Exact loader design

### 4.1 `load_delivery_config(...)` 保持入口不变

```python
def load_delivery_config(config_path: str | Path = Path("configs/delivery.yaml")) -> DeliveryConfig:
    ...
```

### 4.2 Add internal helpers in `app/delivery/runtime.py`

```python
def _load_route(delivery_class: DeliveryClass, route_payload: dict[str, object]) -> DeliveryRoute: ...

def _load_local_durable_route(
    delivery_class: DeliveryClass,
    route_payload: dict[str, object],
) -> LocalDurableRoute: ...

def _load_env_gated_live_route(
    delivery_class: DeliveryClass,
    route_payload: dict[str, object],
) -> EnvGatedLiveRoute: ...
```

### 4.3 Loader rules

#### Local durable route

判定条件：

- `delivery_mode` 缺失时默认 `local_durable`
- 或 `delivery_mode == "local_durable"`

Required fields:

- `adapter`
- `queue`

Validation:

- `adapter` 必须是当前四个 local adapter 之一
- `queue` 必须非空字符串

#### Env-gated live route

判定条件：

- `delivery_mode == "env_gated_live"`

Required fields:

- `adapter`
- `provider_key`
- `endpoint_env`
- `timeout_seconds`
- `target.channel`
- at least one of:
  - `target.chat_id_env`
  - `target.open_id_env`

Validation:

- `delivery_class` 必须是 `page_owner`
- `adapter` 必须是 `adapter_feishu`
- `provider_key` 必须是 `warning-agent`
- `timeout_seconds` 必须是正整数
- `target.channel` 必须是 `feishu`
- `target.thread_id_env` 可选

### 4.4 Recommended config result

S2a 之后 `configs/delivery.yaml` 目标形状：

```yaml
schema_version: delivery-config.v1
routes:
  observe:
    adapter: markdown_only
    delivery_mode: local_durable
    queue: observe
  open_ticket:
    adapter: local_ticket_queue
    delivery_mode: local_durable
    queue: ticket_queue
  page_owner:
    adapter: adapter_feishu
    delivery_mode: env_gated_live
    provider_key: warning-agent
    endpoint_env: WARNING_AGENT_ADAPTER_FEISHU_BASE_URL
    timeout_seconds: 5
    target:
      channel: feishu
      chat_id_env: WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID
      open_id_env: WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID
      thread_id_env: WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID
  send_to_human_review:
    adapter: local_review_queue
    delivery_mode: local_durable
    queue: review_queue
```

## 5. Exact env resolver design

### 5.1 Public function

In `app/delivery/env_gate.py`:

```python
def resolve_adapter_feishu_env_gate(
    route: EnvGatedLiveRoute,
    env: Mapping[str, str | None] = os.environ,
) -> EnvGatedLiveResolution:
    ...
```

### 5.2 Resolution rules

1. `endpoint_env`
   - read `env[route.endpoint_env]`
   - trim whitespace
   - strip trailing `/`
   - if empty -> missing
2. `chat_id_env`
   - if configured, read + trim
   - empty string counts as missing
3. `open_id_env`
   - if configured, read + trim
   - empty string counts as missing
4. `thread_id_env`
   - optional; read + trim; empty -> `None`
5. ready condition:
   - endpoint exists
   - at least one of `chat_id` / `open_id` exists
6. missing target condition:
   - if both missing, resolution is `missing_env`
   - `missing_env` should list whichever configured target env names were empty

### 5.3 Exact return semantics

#### Ready

```python
EnvGatedLiveResolution(
    state="ready",
    endpoint="http://127.0.0.1:8787",
    target=ResolvedFeishuTarget(
        channel="feishu",
        chat_id="oc-test-chat",
        open_id=None,
        thread_id=None,
    ),
    missing_env=(),
)
```

#### Missing endpoint

```python
EnvGatedLiveResolution(
    state="missing_env",
    endpoint=None,
    target=None,
    missing_env=("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL",),
)
```

#### Missing target

```python
EnvGatedLiveResolution(
    state="missing_env",
    endpoint="http://127.0.0.1:8787",
    target=None,
    missing_env=(
        "WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID",
        "WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID",
    ),
)
```

### 5.4 No hidden defaults

S2a 不允许：

- base URL fallback to localhost when env missing
- target fallback to hard-coded chat/open id
- auto-converting missing env into local success state

## 6. Exact payload builder design

### 6.1 Public functions in `app/delivery/adapter_feishu.py`

```python
def build_adapter_feishu_notification_payload(
    report_record: Mapping[str, object],
    *,
    target: ResolvedFeishuTarget,
) -> AdapterFeishuNotificationPayload:
    ...


def serialize_adapter_feishu_notification_payload(
    payload: AdapterFeishuNotificationPayload,
) -> dict[str, object]:
    ...
```

### 6.2 Required report fields

Payload builder must require these string fields from `report_record`:

- `report_id`
- `packet_id`
- `generated_at`
- `severity_band`
- `delivery_class`
- `investigation_stage`
- `service`
- `markdown`

Optional-but-consumed:

- `operation`
- `owner`

### 6.3 Exact field mapping

| payload field | report source | exact rule |
|---|---|---|
| `providerKey` | constant | `warning-agent` |
| `reportId` | `report_id` | direct copy |
| `runId` | `packet_id` | direct copy |
| `occurredAt` | `generated_at` | direct copy |
| `severity` | `severity_band` | `P1->critical`, `P2->warning`, `P3/P4->info` |
| `bodyMarkdown` | `markdown` | direct copy |
| `target.channel` | constant | `feishu` |
| `target.chatId` | resolved target | direct copy if present |
| `target.openId` | resolved target | direct copy if present |
| `target.threadId` | resolved target | direct copy if present |

### 6.4 Exact title builder

```python
def _build_adapter_feishu_title(report_record: Mapping[str, object]) -> str:
    ...
```

Rule:

- if `operation` non-empty:
  - `[{severity_band}] {service} {operation}`
- else:
  - `[{severity_band}] {service}`

Examples:

- `[P1] checkout POST /api/pay`
- `[P2] inventory`

### 6.5 Exact summary builder

```python
def _build_adapter_feishu_summary(report_record: Mapping[str, object]) -> str:
    ...
```

Stage phrase mapping:

- `none -> without investigation escalation`
- `local_primary -> after local_primary investigation`
- `cloud_fallback -> after cloud_fallback investigation`

Summary rule:

- if `operation` non-empty:
  - `{service} {operation} requires {delivery_class} {stage_phrase}`
- else:
  - `{service} requires {delivery_class} {stage_phrase}`

Example:

- `checkout POST /api/pay requires page_owner after cloud_fallback investigation`

### 6.6 Exact facts builder

```python
def _build_adapter_feishu_facts(report_record: Mapping[str, object]) -> tuple[AdapterFeishuFact, ...]:
    ...
```

Include only:

1. `service`
2. `operation` when present
3. `delivery_class`
4. `investigation_stage`
5. `owner` when present

Do **not** add these to `facts` in S2a because adapter-feishu already appends them during normalize:

- `report`
- `run`

## 7. Exact runtime integration design

### 7.1 Keep the public entrypoint name

S2a 仍然保留：

```python
def persist_report_delivery(...)
```

但其内部逻辑改为按 route type 分流。

### 7.2 Add internal helpers in `app/delivery/runtime.py`

```python
def _persist_local_durable_delivery(... ) -> DeliveryDispatchResult: ...

def _persist_env_gated_live_delivery(... ) -> DeliveryDispatchResult: ...

def _markdown_snapshot_path(
    artifact_store: JSONLArtifactStore,
    *,
    dispatch_id: str,
    delivery_class: str,
) -> Path: ...

def _bridge_payload_path(
    artifact_store: JSONLArtifactStore,
    *,
    adapter: str,
    dispatch_id: str,
) -> Path: ...
```

### 7.3 Local durable path

行为保持 W5 兼容，只新增：

- `delivery_mode = "local_durable"`
- `env_gate_state = None`
- `bridge_payload_path = None`

### 7.4 Env-gated live path in S2a

S2a **不发 HTTP request**。

流程：

1. resolve env gate
2. always write Markdown snapshot for operator/runtime truth
3. if env missing:
   - do not write live JSON payload snapshot
   - write dispatch record with `status = "deferred"`
4. if env ready:
   - build `AdapterFeishuNotificationPayload`
   - serialize to JSON
   - write JSON payload snapshot
   - write dispatch record with `status = "queued"`

### 7.5 Exact dispatch record delta

#### Local durable route record

```json
{
  "schema_version": "delivery-dispatch.v1",
  "dispatch_id": "ddp_checkout_post_api_pay_20260418t120008z_page_owner",
  "report_id": "rpt_checkout_post_api_pay_20260418t120008z",
  "packet_id": "ipk_checkout_post_api_pay_20260418t120008z",
  "decision_id": "lad_checkout_post_pay_20260418t120010z",
  "delivery_class": "open_ticket",
  "route_adapter": "local_ticket_queue",
  "delivery_mode": "local_durable",
  "queue": "ticket_queue",
  "status": "queued",
  "env_gate_state": null,
  "generated_at": "2026-04-18T12:00:24Z",
  "payload_path": ".../deliveries/ticket_queue/ddp_....md",
  "bridge_payload_path": null
}
```

#### Env-gated live route record, env missing

```json
{
  "schema_version": "delivery-dispatch.v1",
  "dispatch_id": "ddp_checkout_post_api_pay_20260418t120008z_page_owner",
  "report_id": "rpt_checkout_post_api_pay_20260418t120008z",
  "packet_id": "ipk_checkout_post_api_pay_20260418t120008z",
  "decision_id": "lad_checkout_post_pay_20260418t120010z",
  "delivery_class": "page_owner",
  "route_adapter": "adapter_feishu",
  "delivery_mode": "env_gated_live",
  "queue": null,
  "status": "deferred",
  "env_gate_state": "missing_env",
  "missing_env": [
    "WARNING_AGENT_ADAPTER_FEISHU_BASE_URL",
    "WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID",
    "WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID"
  ],
  "target_channel": "feishu",
  "target_ref": null,
  "live_endpoint": null,
  "generated_at": "2026-04-18T12:00:24Z",
  "payload_path": ".../deliveries/page_owner/ddp_....md",
  "bridge_payload_path": null
}
```

#### Env-gated live route record, env ready

```json
{
  "schema_version": "delivery-dispatch.v1",
  "dispatch_id": "ddp_checkout_post_api_pay_20260418t120008z_page_owner",
  "report_id": "rpt_checkout_post_api_pay_20260418t120008z",
  "packet_id": "ipk_checkout_post_api_pay_20260418t120008z",
  "decision_id": "lad_checkout_post_pay_20260418t120010z",
  "delivery_class": "page_owner",
  "route_adapter": "adapter_feishu",
  "delivery_mode": "env_gated_live",
  "queue": null,
  "status": "queued",
  "env_gate_state": "ready",
  "missing_env": [],
  "target_channel": "feishu",
  "target_ref": "oc-test-chat",
  "live_endpoint": "http://127.0.0.1:8787/providers/webhook",
  "generated_at": "2026-04-18T12:00:24Z",
  "payload_path": ".../deliveries/page_owner/ddp_....md",
  "bridge_payload_path": ".../deliveries/adapter_feishu/ddp_....json"
}
```

## 8. Exact test plan

### 8.1 Update `tests/test_delivery.py`

#### `test_load_delivery_config_maps_mixed_local_and_live_routes`

Asserts:

- `config.routes["observe"]` is `LocalDurableRoute`
- `config.routes["observe"].delivery_mode == "local_durable"`
- `config.routes["page_owner"]` is `EnvGatedLiveRoute`
- `config.routes["page_owner"].adapter == "adapter_feishu"`
- `config.routes["page_owner"].target.channel == "feishu"`

#### `test_persist_report_delivery_keeps_local_route_behavior_for_open_ticket`

Asserts:

- local durable route still writes Markdown snapshot
- `status == "queued"`
- `delivery_mode == "local_durable"`
- `bridge_payload_path is None`

### 8.2 Add `tests/test_delivery_adapter_feishu.py`

#### `test_resolve_adapter_feishu_env_gate_ready_with_chat_id`

Setup:

- set `WARNING_AGENT_ADAPTER_FEISHU_BASE_URL`
- set `WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID`
- unset `WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID`

Asserts:

- resolution state is `ready`
- endpoint trimmed, no trailing slash
- target.chat_id set
- `missing_env == ()`

#### `test_resolve_adapter_feishu_env_gate_ready_with_open_id_only`

Setup:

- base URL set
- chat id unset
- open id set

Asserts:

- resolution state is `ready`
- target.open_id set

#### `test_resolve_adapter_feishu_env_gate_missing_endpoint`

Setup:

- base URL missing
- target env present

Asserts:

- state is `missing_env`
- `WARNING_AGENT_ADAPTER_FEISHU_BASE_URL` listed in `missing_env`

#### `test_resolve_adapter_feishu_env_gate_missing_target`

Setup:

- base URL present
- chat/open target env both missing

Asserts:

- state is `missing_env`
- `WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID` and `WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID` listed in `missing_env`

#### `test_build_adapter_feishu_notification_payload_maps_report_record`

Asserts:

- `providerKey == "warning-agent"`
- `reportId == report_record["report_id"]`
- `runId == report_record["packet_id"]`
- `severity == "critical"` for `P1`
- title and summary use frozen wording
- full Markdown copied into `bodyMarkdown`

#### `test_build_adapter_feishu_notification_payload_omits_optional_fields_when_absent`

Setup:

- `operation = None`
- `owner = None`

Asserts:

- title falls back to `[P2] inventory`
- facts omit `operation` and `owner`

#### `test_persist_report_delivery_marks_page_owner_deferred_when_env_missing`

Asserts:

- `route_adapter == "adapter_feishu"`
- `delivery_mode == "env_gated_live"`
- `status == "deferred"`
- `env_gate_state == "missing_env"`
- no JSON bridge payload snapshot exists
- no local queue field is written

#### `test_persist_report_delivery_materializes_feishu_payload_snapshot_when_env_ready`

Asserts:

- `status == "queued"`
- `env_gate_state == "ready"`
- `bridge_payload_path` exists
- serialized JSON payload matches adapter-feishu contract
- `live_endpoint` ends with `/providers/webhook`

### 8.3 Extend `tests/test_runtime_entry.py`

#### `test_execute_runtime_entrypoint_marks_page_owner_live_route_deferred_when_feishu_env_missing`

Use `monkeypatch.delenv(...)` to ensure env missing.

Asserts from stored delivery record:

- `route_adapter == "adapter_feishu"`
- `delivery_mode == "env_gated_live"`
- `status == "deferred"`
- `env_gate_state == "missing_env"`

#### `test_execute_runtime_entrypoint_materializes_feishu_payload_snapshot_when_env_ready`

Use `monkeypatch.setenv(...)` for base URL + chat id.

Asserts:

- stored dispatch record status is `queued`
- `bridge_payload_path` exists
- payload JSON has `providerKey == "warning-agent"`

### 8.4 Extend `tests/test_alertmanager_webhook.py`

#### `test_webhook_runtime_path_marks_page_owner_live_route_deferred_when_feishu_env_missing`

Use `TestClient(create_app(...))` with env missing.

Asserts:

- webhook still returns accepted runtime receipt
- delivery record is explicit `deferred`
- no silent success / no local queue adapter

#### `test_webhook_runtime_path_materializes_feishu_payload_snapshot_when_env_ready`

Use env present.

Asserts:

- webhook still returns runtime receipt
- delivery record is `queued`
- `bridge_payload_path` exists

## 9. Recommended validation commands for S2a

- `uv run pytest tests/test_delivery.py tests/test_delivery_adapter_feishu.py`
- `uv run pytest tests/test_runtime_entry.py tests/test_alertmanager_webhook.py`
- `uv run ruff check app tests scripts`

## 10. S2a exit gate restated in code terms

`W6.S2a` can claim done only when all of the following are true:

1. `configs/delivery.yaml` contains a typed `page_owner -> adapter_feishu` env-gated route.
2. `load_delivery_config(...)` returns explicit union route truth instead of stringly-typed mixed route dict assumptions.
3. env resolver can deterministically return `ready` vs `missing_env`.
4. payload builder can deterministically materialize adapter-feishu-compatible JSON without any HTTP call.
5. runtime path and webhook path both persist explicit env-gated delivery truth.
6. env missing never appears as success.
7. no HTTP client, callback flow, report polling API, or real Feishu SaaS dependency is introduced.
