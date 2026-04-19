# warning-agent 本地 SigNoz / Prometheus 可用性确认

- 状态: `checked`
- 检查时间: `2026-04-18`
- 目标:
  - 确认当前本机 `SigNoz` 的注册信息与可用性
  - 确认当前可直接接入的 `Prometheus`
  - 为 `warning-agent` 第一阶段实现给出环境结论

## 1. 当前本地 MCP 注册信息

通过本地 `codex mcp list` 检查，当前注册状态如下：

| 名称 | URL | 状态 |
|---|---|---|
| `bb-memory` | `http://127.0.0.1:3100/mcp` | enabled |
| `crm-control` | `http://127.0.0.1:3401/mcp` | enabled |
| `signoz` | `http://127.0.0.1:3104/mcp` | enabled |

结论：

- 本地 **已注册 `signoz` MCP**
- 本地 **未注册独立 `Prometheus MCP`**

## 2. SigNoz 当前本地可用性

### 2.1 监听状态

本地监听确认：

- `127.0.0.1:3104` 正在监听

### 2.2 实际功能验证

已通过 `signoz_list_services` 成功获取服务列表与统计结果。

这说明：

- `signoz` MCP 不只是“已注册”
- 它当前 **可实际使用**

### 2.3 对 warning-agent 的意义

这意味着 `warning-agent` 第一阶段可以直接依赖：

- `SigNoz MCP` 作为 investigator interface 的工具层

同时也意味着：

- `SigNoz` 可作为当前最可靠的 observability 深挖入口

## 3. Prometheus 当前可用性

### 3.1 用户提供的 Prometheus 入口

本次直接按用户给出的 3 个入口做了连通性和 Prometheus 识别检查：

| 名称 | URL | 结果 |
|---|---|---|
| 生产 temporal | `http://10.10.32.203:30223` | 当前不可达 |
| 服务器 | `http://192.168.33.16:9090` | 可用 |
| k8s | `http://10.10.32.206:31326` | 可用 |

### 3.2 健康检查结果

检查接口：

- `/-/healthy`
- `/api/v1/status/buildinfo`

结果如下：

#### `http://192.168.33.16:9090`

- `Prometheus Server is Healthy.`
- `buildinfo` 返回成功
- 版本: `3.1.0`

#### `http://10.10.32.206:31326`

- `Prometheus Server is Healthy.`
- `buildinfo` 返回成功
- 版本: `2.39.1`

#### `http://10.10.32.203:30223`

- 当前不可连接
- 无法通过 Prometheus 健康检查

### 3.3 查询接口验证

进一步对可达入口执行：

- `/api/v1/query?query=up`
- `/api/v1/query?query=prometheus_build_info`

结果：

#### `http://192.168.33.16:9090`

- 查询成功
- `up` 返回大量时间序列
- `prometheus_build_info` 返回成功
- 查询结果同时可见：
  - 本机自身 `prometheus`
  - `kubesphere-monitoring-system/k8s`
  - `temporal-production` 相关 targets

#### `http://10.10.32.206:31326`

- 查询成功
- `up` 返回时间序列
- `prometheus_build_info` 返回成功
- 当前可确认其是一个可用的 `prometheus-k8s` 查询入口

### 3.4 关于 temporal 监控入口的判断

虽然“生产 temporal”专用入口：

- `http://10.10.32.203:30223`

当前不可达，但通过 `k8s` Prometheus：

- `http://10.10.32.206:31326`

已经能直接查询到 `temporal-production` namespace 下的指标，包括：

- `temporal-frontend`
- `temporal-history`
- `temporal-matching`
- `temporal-worker`

这意味着：

- temporal 数据当前并不是完全不可得
- 只是“专用 temporal Prometheus 入口”不可达
- 第一阶段仍可以通过 `k8s` Prometheus 获取 temporal 相关指标

### 3.5 本机历史探测结果

在本机本地监听中，还发现：

- `127.0.0.1:19090`
- 进程名为 `g-orders`

但它对 Prometheus 常见接口返回：

- `Empty reply from server`

因此：

- 不能把这个端口当成 Prometheus collector 的正式数据源

### 3.6 结论

当前环境下，Prometheus 不应再被视为“未确认可用”。

更准确的状态是：

- **可用**
  - `http://192.168.33.16:9090`
  - `http://10.10.32.206:31326`
- **暂不可用**
  - `http://10.10.32.203:30223`

## 4. 对第一阶段实现的实际影响

### 4.1 可以立即依赖的

- `SigNoz MCP`
- Prometheus HTTP API:
  - `http://192.168.33.16:9090`
  - `http://10.10.32.206:31326`
- 本地 Python / SQLite / uv 环境
- Docker

### 4.2 不能假设已经具备的

- 本地独立 `Prometheus MCP`
- 本地 Alertmanager webhook 来源
- `http://10.10.32.203:30223` 这个 temporal 专用入口

### 4.3 最稳妥的第一阶段策略

第一阶段建议按下面的现实边界实现：

1. `warning-agent` 设计上直接支持多 Prometheus endpoint
2. 默认 Prometheus collector 接入：
   - `http://192.168.33.16:9090`
   - `http://10.10.32.206:31326`
3. `http://10.10.32.203:30223` 标记为 optional / disabled by default
4. `SigNoz MCP` 作为 investigator 层固定深挖入口
5. Alertmanager webhook 入口仍需后续单独确认

## 5. 当前可执行判断

如果今天就启动 `warning-agent` 的实现，关于 observability 入口的可信判断是：

- `SigNoz`: **可用**
- `Prometheus`: **部分可用**
  - 两个入口已确认可查询
  - 一个入口当前不可达

因此当前最现实的策略是：

> 直接按完整链路实现 `Prometheus + SigNoz` 支持；
> 其中 Prometheus 默认接入两个已确认可用的 HTTP API，
> temporal 专用入口先保留为可配置可禁用 source，
> `SigNoz MCP` 则作为 investigator 层的深挖工具。

## 6. 最终结论

当前环境对 `warning-agent` 的直接支持情况如下：

| 能力 | 状态 | 结论 |
|---|---|---|
| `SigNoz MCP` 注册 | yes | 可用 |
| `SigNoz MCP` 实测调用 | yes | 可用 |
| 独立 `Prometheus MCP` 注册 | no | 不可用 |
| `http://192.168.33.16:9090` | yes | Prometheus 3.1.0，可查询 |
| `http://10.10.32.206:31326` | yes | Prometheus 2.39.1，可查询 |
| `http://10.10.32.203:30223` | no | 当前不可达 |
| 本地 `127.0.0.1:19090` 监听 | yes | 不能确认为 Prometheus |

最终可以非常明确地说：

> `warning-agent` 第一阶段可以放心依赖本地 `SigNoz MCP`，
> 也可以直接接入两个已确认可用的 Prometheus HTTP API；
> 仅 temporal 专用入口 `10.10.32.203:30223` 当前不可达，需要作为后续补充 source 处理。 
