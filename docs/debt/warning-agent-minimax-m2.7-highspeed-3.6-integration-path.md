# warning-agent minimax-m2.7-highspeed 3.6 integration path

- status: `implementation debt / bounded technical path`
- scope: `3.6 Investigation local-primary real adapter`
- target_model: `neko api:minimax-m2.7-highspeed`
- last_updated: `2026-04-20`

## 1. Goal

本文件回答一个非常具体的问题：

> 如果希望 `warning-agent` 在 `3.6 Investigation` 阶段直接使用
> `neko api:minimax-m2.7-highspeed` 作为核心本地调查模型，
> 对照当前代码实现，最小需要改哪些文件、改什么、为什么不是“只配一下 env 就行”。

这里的目标不是重做 `3.6` 的产品逻辑。

这里的目标是：

- 保持现有 `local-first` investigator 架构不变
- 保持现有 `InvestigationRequest -> InvestigationResult` 契约不变
- 只把 `local_primary.real_adapter` 这条 seam 真正接通
- 让 `minimax-m2.7-highspeed` 成为 `3.6` 的真实分析模型

## 2. Assumption boundary

本技术路径建立在一个前提上：

- `neko api` 暴露的是一个 **OpenAI-compatible HTTP** 接口
- 可以通过：
  - `base_url`
  - `model name`
  - 可选 `api key`
  这三类参数完成调用

如果这个前提不成立，本文件就不再是“最小改动路径”，而会退化成“新增 transport 类型”的较大改造。

## 3. Current code truth

### 3.1 What is already landed

当前仓库已经具备：

1. `3.6 Investigation` 的完整业务骨架
   - `app/investigator/runtime.py`
   - `app/investigator/router.py`
   - `app/investigator/local_primary.py`
   - `app/investigator/tools.py`
   - `app/investigator/cloud_fallback.py`
2. `local_primary.real_adapter` 的 config contract
   - `configs/provider-boundary.yaml`
3. `openai_compatible_http` transport 作为被允许的 boundary transport
   - `app/investigator/provider_boundary.py`
4. gate 语义
   - `smoke_default`
   - `missing_env`
   - `ready`

### 3.2 What is not yet landed

当前仓库 **没有** 落地的部分：

1. 自动构造 `local_primary real_adapter_provider` 的 runtime 代码
2. 一个真正可用的 OpenAI-compatible local-primary client
3. 把 real adapter response 映射成标准 `InvestigationResult` 的真实实现
4. `local_primary` 的 API key env contract

### 3.3 Why this is not config-only today

当前 `local_primary` 的运行逻辑是：

1. 读取 provider boundary
2. 解析 real adapter gate
3. 如果 gate = `ready`
4. 直接要求存在 `self.real_adapter_provider`
5. 如果没有，就抛错 fail-closed

也就是说，当前代码不是：

```text
gate ready -> automatically call remote local-primary model
```

而是：

```text
gate ready -> require an injected runtime provider object
```

所以今天仅设置：

- `WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED`
- `WARNING_AGENT_LOCAL_PRIMARY_BASE_URL`
- `WARNING_AGENT_LOCAL_PRIMARY_MODEL`

是不够的。

## 4. File-by-file current gap

### 4.1 `app/investigator/local_primary.py`

当前问题：

- `LocalPrimaryInvestigator` 支持 `real_adapter_provider`
- 但只支持外部注入
- 不支持按 config/env 自动构造

这意味着：

- 测试里可注入 fake provider
- runtime 里不会自动获得真实 provider

### 4.2 `app/investigator/runtime.py`

当前问题：

- `run_investigation_runtime(...)` 默认只调用：
  - `LocalPrimaryInvestigator.from_config(...)`
- 没有 local-primary real adapter auto-wiring

### 4.3 `app/investigator/provider_boundary.py`

当前状态：

- 已支持 `openai_compatible_http`
- 已支持 `enabled_env / endpoint_env / model_env`

当前缺口：

- `local_primary.real_adapter.api_key_env` 现在为空
- 如果 `neko api` 需要 key，这里还不能完整表达

### 4.4 `tests/test_local_primary.py`

当前状态：

- 已证明 gate ready 时可消费 `FakeRealLocalPrimaryProvider`

当前缺口：

- 还没有真实 OpenAI-compatible client 的单元测试
- 还没有真实 response -> `InvestigationResult` 的 contract test

## 5. Minimal implementation path

最小路径建议压成 4 个任务。

### Task 1. Add a real local-primary adapter client

新增一个极小实现文件，例如：

- `app/investigator/local_primary_openai_compat.py`

责任：

- 读取：
  - endpoint
  - model
  - optional api key
  - timeout
- 接收 `InvestigationRequest`
- 组装 bounded prompt
- 调用 OpenAI-compatible HTTP endpoint
- 解析响应
- 输出标准 `InvestigationResult`

这里的关键不是“写一个万能 LLM SDK”，而是：

- 只服务 `3.6 local_primary`
- 只收 `InvestigationRequest`
- 只产出 `InvestigationResult`

### Task 2. Wire the client into local-primary runtime

修改：

- `app/investigator/local_primary.py`

目标：

- 当 gate = `ready` 且没有显式传入 `real_adapter_provider` 时，
  自动基于 boundary/env 构造真实 provider

推荐形态：

```python
def build_real_local_primary_provider(...):
    ...
```

然后在 `from_config(...)` 或 `investigate(...)` 路径里使用。

这样可以保持：

- 测试仍可注入 fake provider
- 运行时也能自动构造真实 provider

### Task 3. Extend local_primary boundary for API key if needed

如果 `neko api` 需要鉴权，修改：

- `configs/provider-boundary.yaml`
- `app/investigator/provider_boundary.py`
- `tests/test_provider_boundary.py`

建议做法：

- 不写死 `NEKO_API_KEY`
- 仍沿用本地 provider 语义，例如：
  - `WARNING_AGENT_LOCAL_PRIMARY_API_KEY`

这样 future local-primary model 更换时不需要再改命名。

### Task 4. Add runtime and contract tests

至少补这些测试：

1. gate ready + env complete + fake openai-compatible response
   - returns schema-valid `InvestigationResult`
2. gate ready + missing client setup
   - fail-closed path still explicit
3. gate ready + API key required but missing
   - returns `missing_env`
4. runtime path
   - `run_investigation_runtime(...)` 在真实 provider 装配下可直接走 real adapter

## 6. Minimal file change list

### 6.1 Must change

- `app/investigator/local_primary.py`
- `app/investigator/provider_boundary.py`
- `configs/provider-boundary.yaml`
- `tests/test_local_primary.py`
- `tests/test_provider_boundary.py`

### 6.2 Must add

- `app/investigator/local_primary_openai_compat.py`

### 6.3 Strongly recommended to add

- `tests/test_local_primary_openai_compat.py`
- `tests/test_investigation_runtime.py`

### 6.4 Should not need changes for the minimal path

以下文件理论上不必动：

- `app/investigator/router.py`
- `app/investigator/tools.py`
- `app/analyzer/*`
- `app/runtime_entry.py`
- `app/investigator/cloud_fallback.py`

前提是：

- 只做 `3.6 local_primary real adapter`
- 不顺手扩 scope 到 cloud fallback provider rollout

## 7. Recommended implementation order

顺序建议固定为：

1. `provider-boundary` contract 修正
2. 新增 `local_primary_openai_compat.py`
3. `local_primary.py` 自动装配 real adapter
4. 单元测试
5. runtime integration test

原因：

- 先冻结 contract，避免 adapter 写完后反复改 env 语义
- 再写 client，避免 runtime wiring 时同时处理 transport 和 contract 变化
- 最后才接运行时

## 8. Suggested technical shape

### 8.1 Input

真实 provider 不应该直接读全仓上下文。

它应该只消费：

- `request.packet`
- `request.decision`
- `request.retrieval_packet_ids`
- `request.prometheus_query_refs`
- `request.signoz_query_refs`
- `request.sample_trace_ids`
- `request.sample_log_refs`
- 少量 `request.code_search_refs`

### 8.2 Prompt shape

prompt 必须保持 bounded：

1. packet summary
2. first-pass decision summary
3. retrieval history summary
4. bounded Signoz refs
5. bounded Prometheus corroboration refs
6. output contract

不应该：

- 拼接全量 raw logs
- 拼接全量 trace trees
- 让模型自由生成无契约结果

### 8.3 Output shape

必须直接落成当前 `InvestigationResult` 结构：

- `summary`
- `hypotheses`
- `routing`
- `evidence_refs`
- `unknowns`
- `analysis_updates`

这样才能与当前 report、delivery、feedback 路径完全兼容。

## 9. Validation floor

最小验证建议：

1. `uv run pytest tests/test_provider_boundary.py tests/test_local_primary.py`
2. 新增 adapter 单测
3. `uv run pytest tests/test_investigation_runtime.py`
4. `uv run pytest`
5. `uv run ruff check app tests scripts`

如果有本地可用的 Neko endpoint，再补：

6. 一个 env-opt-in smoke proof

## 10. Parallel impact on W7

### 10.1 Safe parallel boundary

如果当前正在平行推进 W7，这个任务建议压在下面这个边界内：

- 只动 `3.6 local_primary real adapter`
- 不碰 ingress / queue / worker
- 不碰 W7 的 auth / admission / governance 主线
- 不扩到 cloud fallback live rollout

在这个边界内，它对 W7 的影响是可控的。

### 10.2 Main conflict files

与 W7 最容易冲突的文件：

- `app/investigator/local_primary.py`
- `app/investigator/provider_boundary.py`
- `configs/provider-boundary.yaml`
- `tests/test_local_primary.py`

### 10.3 Conclusion

结论：

- 这不是“大工程”
- 这是一个 **中低复杂度的 bounded adapter integration**
- 最大风险不是开发量，而是 scope 膨胀

## 11. Final answer

对照当前代码实现，最准确的技术判断是：

> `minimax-m2.7-highspeed` 接入 `3.6 Investigation` 并不是“只设置几个环境变量”；
> 但也不需要重做架构。
> 当前最小路径就是补一个 `local_primary` 的 OpenAI-compatible real adapter provider，
> 再把它接到现有 `real_adapter` gate seam 上。
