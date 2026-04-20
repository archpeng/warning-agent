# warning-agent adapter-feishu notify-first closeout debt

- status: `implementation debt / closeout support`
- scope: `warning-agent -> adapter-feishu -> Feishu/Lark`
- last_updated: `2026-04-20`

## 1. Goal

本阶段已经明确完成目标：

```text
warning-agent 产出最终通知内容
  -> POST adapter-feishu /providers/webhook
  -> adapter-feishu 负责 Feishu message/card delivery
```

本文件不是新的架构设计稿，而是给当前 `warning-agent` 仓库一个可收口的实现债务说明：

- 当前 dirty worktree 里已经出现了一版 `adapter_feishu` live bridge
- 该桥接面已经覆盖了 notify-first 主链路
- 本文件记录：
- 当前代码已经落在哪些文件
- 这些文件的关键函数签名是什么
- 若要从干净分支复刻，应如何落地
- 还剩哪些债务没有收口

## 1.1 Practical onboarding link

如果对接方要看 `adapter-feishu` 侧的实操接入说明，而不是 warning-agent 内部 debt 说明，请直接看 sibling repo 文档：

- `/home/peng/dt-git/github/adapter-feishu/docs/runbook/adapter-feishu-warning-agent-onboarding.md`

## 2. Current code surfaces

当前仓库里，notify-first bridge 已经触达这些文件：

- `app/delivery/runtime.py`
- `app/delivery/adapter_feishu.py`
- `app/delivery/env_gate.py`
- `app/delivery/http_client.py`
- `app/delivery/bridge_result.py`
- `configs/delivery.yaml`
- `tests/test_delivery.py`
- `tests/test_delivery_adapter_feishu.py`
- `tests/test_runtime_entry.py`
- `tests/test_alertmanager_webhook.py`

当前语义：

- `page_owner` route 已经从 `local_page_queue` 切到 `adapter_feishu`
- route mode 已经区分为：
  - `local_durable`
  - `env_gated_live`
- 当前 notify-first payload builder 已经能把 `report_record` 映射成 adapter-feishu 接受的 payload
- 当前 runtime 已经会在 env ready 时真实发 HTTP request 到：
  - `${WARNING_AGENT_ADAPTER_FEISHU_BASE_URL}/providers/webhook`

## 3. File-level delta if re-applied on a clean branch

如果从一个没有这些改动的干净分支重做，本阶段只需要改下面这些文件。

### 3.1 Extend existing files

- `app/delivery/runtime.py`
- `configs/delivery.yaml`
- `tests/test_delivery.py`
- `tests/test_runtime_entry.py`
- `tests/test_alertmanager_webhook.py`

### 3.2 Add new files

- `app/delivery/adapter_feishu.py`
- `app/delivery/env_gate.py`
- `app/delivery/http_client.py`
- `app/delivery/bridge_result.py`
- `tests/test_delivery_adapter_feishu.py`

## 4. Exact signatures that matter

下面列的是当前实现已经采用、并且建议保持稳定的函数签名。

### 4.1 `app/delivery/runtime.py`

```python
def load_delivery_config(
    config_path: str | Path = Path("configs/delivery.yaml"),
) -> DeliveryConfig: ...

def persist_report_delivery(
    *,
    report_record: dict[str, object],
    artifact_store: JSONLArtifactStore,
    config_path: str | Path = Path("configs/delivery.yaml"),
) -> DeliveryDispatchResult: ...
```

推荐保持内部 helpers 分层：

```python
def _load_route(
    delivery_class: DeliveryClass,
    route_payload: dict[str, object],
) -> DeliveryRoute: ...

def _load_local_durable_route(
    delivery_class: DeliveryClass,
    route_payload: dict[str, object],
) -> LocalDurableRoute: ...

def _load_env_gated_live_route(
    delivery_class: DeliveryClass,
    route_payload: dict[str, object],
) -> EnvGatedLiveRoute: ...

def _persist_local_durable_delivery(
    *,
    report_record: dict[str, object],
    artifact_store: JSONLArtifactStore,
    route: LocalDurableRoute,
    dispatch_id: str,
) -> DeliveryDispatchResult: ...

def _persist_env_gated_live_delivery(
    *,
    report_record: dict[str, object],
    artifact_store: JSONLArtifactStore,
    route: EnvGatedLiveRoute,
    dispatch_id: str,
) -> DeliveryDispatchResult: ...
```

当前核心 dataclass：

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

### 4.2 `app/delivery/env_gate.py`

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

def resolve_adapter_feishu_env_gate(
    route: EnvGatedLiveRoute,
    *,
    env: Mapping[str, str | None] | None = None,
) -> EnvGatedLiveResolution: ...
```

建议保持这层只做 env resolution，不做 HTTP，不做 payload build。

### 4.3 `app/delivery/adapter_feishu.py`

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

def build_adapter_feishu_notification_payload(
    report_record: Mapping[str, object],
    *,
    target: ResolvedFeishuTarget,
) -> AdapterFeishuNotificationPayload: ...

def serialize_adapter_feishu_notification_payload(
    payload: AdapterFeishuNotificationPayload,
) -> dict[str, object]: ...
```

当前 builder 的稳定映射规则：

- `providerKey = "warning-agent"`
- `reportId = report_record["report_id"]`
- `runId = report_record["packet_id"]`
- `occurredAt = report_record["generated_at"]`
- `severity`:
  - `P1 -> critical`
  - `P2 -> warning`
  - `P3/P4 -> info`
- `bodyMarkdown = report_record["markdown"]`

### 4.4 `app/delivery/http_client.py`

```python
def post_adapter_feishu_notification(
    *,
    endpoint: str,
    payload: dict[str, object],
    timeout_seconds: int,
) -> BridgeDispatchResult: ...
```

当前成功判定规则应保持：

- HTTP `202`
- JSON `code == 0`
- provider `status in {"delivered", "duplicate_ignored"}`

### 4.5 `app/delivery/bridge_result.py`

```python
@dataclass(frozen=True)
class BridgeDispatchResult:
    status: Literal["delivered", "failed"]
    response_code: int | None
    provider_key: str | None
    provider_status: str | None
    message: str | None
    external_ref: str | None
    raw_response: dict[str, object] | None
```

## 5. Config shape that should stay frozen

`configs/delivery.yaml` 当前推荐保持为：

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

当前 scope 内必须视为 required 的 env：

- `WARNING_AGENT_ADAPTER_FEISHU_BASE_URL`
- `WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID` or `WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID`

## 6. Current implementation debt to close

当前 dirty worktree 已经基本覆盖 notify-first 主链路，但还留着几项需要收口的债务。

### 6.1 Missing adapter webhook auth support

`adapter-feishu` 现在已经支持 provider webhook auth：

- `Authorization: Bearer <token>`
- 或 `x-adapter-provider-token: <token>`

但 `warning-agent` 当前 `post_adapter_feishu_notification(...)` 还没有 header seam。

建议最小补法：

```python
def post_adapter_feishu_notification(
    *,
    endpoint: str,
    payload: dict[str, object],
    timeout_seconds: int,
    auth_token: str | None = None,
) -> BridgeDispatchResult: ...
```

配套 env：

- `WARNING_AGENT_ADAPTER_FEISHU_PROVIDER_WEBHOOK_AUTH_TOKEN`

发请求时：

```python
headers = {"content-type": "application/json"}
if auth_token:
    headers["authorization"] = f"Bearer {auth_token}"
```

这是当前最值得优先补的 debt；否则 warning-agent 只能对“未开启 provider auth 的 adapter-feishu”工作。

### 6.2 Target is still env-scoped, not per-recipient dynamic

当前 `page_owner -> adapter_feishu` 仍然是 env-gated 单目标：

- 一个固定 `chatId`
- 或一个固定 `openId`

这对“先把结果发到一个固定群或固定个人”已经够用，但它不是动态收件人路由。

如果后续要按 alert owner / service owner / oncall rotation 动态决定接收人，建议不要直接破坏当前 dataclass，而是新增一层 target resolver：

```python
def resolve_delivery_target(
    report_record: Mapping[str, object],
    route: EnvGatedLiveRoute,
) -> ResolvedFeishuTarget: ...
```

但这不属于当前阶段的 blocker。

### 6.3 No retry / backoff / circuit-breaker

当前 HTTP dispatch 是 bounded single-shot call：

- 网络错误 -> `failed`
- adapter 返回 reject -> `failed`

这对 honest closeout 是够的，但还不是生产级 delivery reliability。当前阶段可以先不补。

### 6.4 No provider auth / response identifiers persisted as first-class truth

当前 artifact record 已经记录：

- `response_code`
- `provider_key`
- `provider_status`
- `external_ref`
- `raw_response`

这已经够排查问题，但还没有把 retry key / correlation id / auth mode 做成一等字段。当前不是 blocker。

### 6.5 Python cache artifacts are dirty noise

当前工作树里有不少 `__pycache__` 和 `.pyc` 变更。它们不该进入提交。

建议在 closeout 前：

- 清理 `__pycache__`
- 更新 `.gitignore` 若仓库还没忽略

## 7. Minimal closeout checklist

如果目标只是把本阶段 notify-first bridge 收口到一个可提交状态，最小 checklist 是：

1. 保留当前 file layout：
   - `runtime.py`
   - `adapter_feishu.py`
   - `env_gate.py`
   - `http_client.py`
   - `bridge_result.py`
2. 给 `http_client.py` 增加 provider webhook auth token 支持
3. 确认 `configs/delivery.yaml` 里 `page_owner` route 仍然走 `adapter_feishu`
4. 保留并跑通这些测试：
   - `tests/test_delivery.py`
   - `tests/test_delivery_adapter_feishu.py`
   - `tests/test_runtime_entry.py`
   - `tests/test_alertmanager_webhook.py`
5. 清理 `__pycache__` 脏文件

## 8. Explicit non-goals

本文件明确不把下面事项当成当前 closeout blocker：

- warning-agent card callback 闭环
- alert-forward orchestration
- report polling API
- 多 provider 抽象
- 动态收件人路由
- secret manager / service mesh / retry worker

当前阶段只要求：

```text
warning-agent materializes final report
  -> adapter_feishu live bridge payload
  -> POST /providers/webhook
  -> adapter-feishu delivers to Feishu
```
