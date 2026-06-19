# alert-hub

运维告警汇聚 API：统一接入 Prometheus webhook 与自定义 JSON 脚本告警，去重合并后匹配值班组分发，全链路审计日志。

## 启动

```bash
go run .
```

服务启动在 `:8080`，首次启动会在当前目录生成 `alert-hub.db`（SQLite）。

健康检查：

```bash
curl http://localhost:8080/healthz
```

---

## 路由总览

| Method | Path                            | 说明                             |
|--------|---------------------------------|----------------------------------|
| GET    | `/healthz`                      | 健康检查                         |
| POST   | `/api/v1/alerts/custom`         | 接入自定义 JSON 脚本告警         |
| POST   | `/api/v1/alerts/prometheus`     | 接入 Prometheus Alertmanager webhook |
| GET    | `/api/v1/alerts`                | 分页查询告警（支持筛选）         |
| GET    | `/api/v1/alerts/{id}`           | 查询单条告警                     |
| GET    | `/api/v1/policies`              | 列出所有路由策略                 |
| POST   | `/api/v1/policies`              | 创建路由策略                     |
| GET    | `/api/v1/policies/{id}`         | 查询单条策略                     |
| PUT    | `/api/v1/policies/{id}`         | 更新策略                         |
| DELETE | `/api/v1/policies/{id}`         | 删除策略                         |

---

## 去重规则

- **5 分钟窗口**：`last_seen_at` 在 5 分钟内、且 `fingerprint` 相同的告警会合并。
- **合并行为**：
  - `dedupe_count` 累加 1
  - 取**更高**的 severity（critical > warning > info）
  - 更新 `last_seen_at` 为当前时间
  - 合并 description 与 labels（新值覆盖旧值）
- 超过 5 分钟的相同 fingerprint 会作为新告警入库。

`fingerprint` 计算：对 `summary + service + env + labels` 排序后做 SHA256，取前 16 位。

---

## 路由与分发

- 按 `service` / `env` / `severity` / 自定义 labels 匹配 `Policy`，命中则分发给对应 team。
- 未命中任何 Policy 时走 `default` 组。
- 每次 ingest 会写入 3 条 audit log：`ingested`(或 `deduped`)、`dispatched`。

---

## curl 示例

### 1. 创建路由策略（先建好再发告警，否则命中 default）

```bash
# 生产环境 payment 服务的 critical 告警 → oncall-payments 组
curl -X POST http://localhost:8080/api/v1/policies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "payments-critical-prod",
    "match_labels": {
      "service": "payment",
      "env": "prod",
      "severity": "critical"
    },
    "team": "oncall-payments",
    "priority": 100
  }'

# 所有 staging 环境 → sre-staging 组
curl -X POST http://localhost:8080/api/v1/policies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "all-staging",
    "match_labels": { "env": "staging" },
    "team": "sre-staging",
    "priority": 50
  }'
```

查看策略：

```bash
curl http://localhost:8080/api/v1/policies
```

### 2. 自定义 JSON 脚本告警接入

发第一条：

```bash
curl -X POST http://localhost:8080/api/v1/alerts/custom \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "支付超时",
    "description": "payment-svc 在 30s 内超时 15 次",
    "severity": "warning",
    "service": "payment",
    "env": "prod",
    "labels": { "region": "cn-north", "instance": "pay-01" }
  }'
```

返回中 `is_dedupe=false, dedupe_count=1`，`assigned_team` 为空（因为 severity 是 warning，不匹配上面的 critical 策略），所以会是 `default`。

### 3. dedupe 测试：相同 body 重复 POST 三次

```bash
# 第二次（会合并）
curl -X POST http://localhost:8080/api/v1/alerts/custom \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "支付超时",
    "description": "payment-svc 在 30s 内超时 15 次",
    "severity": "warning",
    "service": "payment",
    "env": "prod",
    "labels": { "region": "cn-north", "instance": "pay-01" }
  }'

# 第三次（升级为 critical，依然合并，severity 会提升）
curl -X POST http://localhost:8080/api/v1/alerts/custom \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "支付超时",
    "description": "payment-svc 在 30s 内超时 50 次",
    "severity": "critical",
    "service": "payment",
    "env": "prod",
    "labels": { "region": "cn-north", "instance": "pay-01" }
  }'
```

查看最终结果，**应当只有 1 条告警**（不会出现未合并的重复记录），`dedupe_count=3`，`severity=critical`，`assigned_team=oncall-payments`：

```bash
curl "http://localhost:8080/api/v1/alerts?service=payment&env=prod"
```

### 4. Prometheus Alertmanager webhook 接入

```bash
curl -X POST http://localhost:8080/api/v1/alerts/prometheus \
  -H "Content-Type: application/json" \
  -d '{
    "version": "4",
    "groupKey": "{}:{alertname=\"HighErrorRate\", service=\"order\"}",
    "status": "firing",
    "receiver": "alert-hub",
    "groupLabels": { "alertname": "HighErrorRate", "service": "order" },
    "commonLabels": {
      "alertname": "HighErrorRate",
      "service": "order",
      "env": "staging",
      "severity": "warning"
    },
    "commonAnnotations": {
      "summary": "order 服务错误率过高",
      "description": "错误率 > 5%"
    },
    "externalURL": "http://alertmanager:9093",
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "HighErrorRate",
          "service": "order",
          "env": "staging",
          "severity": "warning",
          "instance": "order-02"
        },
        "annotations": {
          "summary": "order 服务错误率过高",
          "description": "错误率 > 5%"
        },
        "startsAt": "2026-06-19T08:00:00Z",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "http://prom:9090/..."
      }
    ]
  }'
```

查询（按 team 筛选，应当分到 sre-staging）：

```bash
curl "http://localhost:8080/api/v1/alerts?team=sre-staging"
```

### 5. 分页查询

```bash
# 第 1 页，每页 5 条
curl "http://localhost:8080/api/v1/alerts?page=1&size=5"

# 按 severity 过滤
curl "http://localhost:8080/api/v1/alerts?severity=critical"
```
