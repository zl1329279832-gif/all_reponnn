# Alert Aggregator

运维告警汇聚 API，统一接收 Prometheus webhook 和自定义 JSON 脚本告警，解析后存入 SQLite。支持 5 分钟内同 fingerprint 去重合并、按标签匹配值班组、完整的 audit 日志记录。

## 启动

```bash
go mod tidy
go run main.go
```

服务启动在 `:8080`，数据库文件 `./alerts.db` 自动创建。

## API 路由

### 健康检查
```
GET /health
```

### 告警接收
```
POST /api/v1/ingest/prometheus   # Prometheus Alertmanager webhook
POST /api/v1/ingest/custom       # 自定义 JSON 告警
```

### 告警查询
```
GET /api/v1/alerts               # 分页查询，支持筛选
GET /api/v1/alerts/{id}          # 单条告警详情
```

### 策略管理
```
POST   /api/v1/policies          # 创建策略
GET    /api/v1/policies          # 策略列表
GET    /api/v1/policies/{id}     # 策略详情
PUT    /api/v1/policies/{id}     # 更新策略
DELETE /api/v1/policies/{id}     # 删除策略
```

### Audit 日志
```
GET /api/v1/audit                # 分发审计日志
```

## 去重合并规则

- 基于 `fingerprint`（由 labels 哈希计算，**severity 不参与哈希**）作为合并标识
- **5 分钟窗口**内相同 fingerprint 的推送自动合并
- 合并时按 `critical > error > warning > info > debug` 取最高 severity，不会降级
- `dedupe_count` 累加 1，`description` 和其他字段更新为最新值
- 窗口外同 fingerprint 再来会新开一条告警记录（不会撞唯一约束）
- 相同 body 重复 POST 不会产生重复记录

## 策略匹配规则

按 `service` + `env` + `severity` 三维度匹配，支持空值或 `*` 通配：
- 精确匹配优先于通配
- 未命中任何策略走 `default` 值班组

## curl 测试示例

### 1. 创建策略
```bash
curl -X POST http://localhost:8080/api/v1/policies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "payments-critical",
    "service": "payments",
    "env": "prod",
    "severity": "critical",
    "on_call_group": "payments-oncall"
  }'

curl -X POST http://localhost:8080/api/v1/policies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "all-warning",
    "service": "*",
    "env": "*",
    "severity": "warning",
    "on_call_group": "general-oncall"
  }'
```

### 2. 自定义 JSON 告警（测试 dedupe 和 severity 升级）
```bash
# 第一次推送：warning 级别（created，dedupe_count=1，severity=warning）
curl -X POST http://localhost:8080/api/v1/ingest/custom \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "warning",
    "service": "payments",
    "env": "prod",
    "summary": "Payment gateway high latency",
    "description": "p99 latency > 500ms for 2 minutes",
    "labels": {
      "region": "us-east-1",
      "instance": "pay-01"
    }
  }'

# 5 分钟内重复推送相同 body（merged，dedupe_count=2，severity 保持 warning）
curl -X POST http://localhost:8080/api/v1/ingest/custom \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "warning",
    "service": "payments",
    "env": "prod",
    "summary": "Payment gateway high latency",
    "description": "p99 latency > 500ms for 2 minutes",
    "labels": {
      "region": "us-east-1",
      "instance": "pay-01"
    }
  }'

# 第三次推送：severity 升级为 critical（merged，dedupe_count=3，severity 升级为 critical）
curl -X POST http://localhost:8080/api/v1/ingest/custom \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "critical",
    "service": "payments",
    "env": "prod",
    "summary": "Payment gateway high latency",
    "description": "p99 latency > 1000ms for 10 minutes",
    "labels": {
      "region": "us-east-1",
      "instance": "pay-01"
    }
  }'

# 第四次推送：severity 降回 warning（merged，dedupe_count=4，severity 保持 critical 不降级）
curl -X POST http://localhost:8080/api/v1/ingest/custom \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "warning",
    "service": "payments",
    "env": "prod",
    "summary": "Payment gateway high latency",
    "description": "p99 latency < 300ms, recovering",
    "labels": {
      "region": "us-east-1",
      "instance": "pay-01"
    }
  }'
```

### 2b. 测试 5 分钟窗口过期（可选，需等待）
```bash
# 等待 5 分钟后，推送同 fingerprint 告警
# 应该新开一条记录（created，dedupe_count=1），而不是合并到旧记录
curl -X POST http://localhost:8080/api/v1/ingest/custom \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "warning",
    "service": "payments",
    "env": "prod",
    "summary": "Payment gateway high latency",
    "description": "latency spike again",
    "labels": {
      "region": "us-east-1",
      "instance": "pay-01"
    }
  }'

# 此时查询告警应该有 2 条不同 ID 的记录，fingerprint 相同
curl "http://localhost:8080/api/v1/alerts?service=payments"
```

### 3. Prometheus webhook 告警
```bash
curl -X POST http://localhost:8080/api/v1/ingest/prometheus \
  -H "Content-Type: application/json" \
  -d '{
    "version": "4",
    "groupKey": "{}:{alertname=\"HighErrorRate\", severity=\"warning\"}",
    "status": "firing",
    "receiver": "webhook",
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "HighErrorRate",
          "severity": "warning",
          "service": "order",
          "env": "prod",
          "instance": "order-02"
        },
        "annotations": {
          "summary": "High error rate detected",
          "description": "Error rate > 5% for 2 minutes"
        },
        "startsAt": "2024-01-15T10:00:00Z",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "http://prometheus:9090/graph?g0.expr=..."
      }
    ]
  }'
```

### 4. 查询告警（带筛选和分页）
```bash
# 查询所有告警
curl "http://localhost:8080/api/v1/alerts"

# 按 service 筛选
curl "http://localhost:8080/api/v1/alerts?service=payments"

# 按 severity 筛选
curl "http://localhost:8080/api/v1/alerts?severity=critical"

# 组合筛选 + 分页
curl "http://localhost:8080/api/v1/alerts?service=payments&env=prod&page=1&page_size=10"

# 单条告警详情
curl "http://localhost:8080/api/v1/alerts/1"
```

### 5. 查看策略
```bash
curl "http://localhost:8080/api/v1/policies"
```

### 6. 查看 audit 日志
```bash
curl "http://localhost:8080/api/v1/audit?limit=10"
```

### 7. 验证去重结果
```bash
# 查看告警列表，验证：
# - 相同 fingerprint 只有 1 条记录
# - dedupe_count=4（1次 created + 3次 merged）
# - severity 保持 critical（升级后不降级）
curl "http://localhost:8080/api/v1/alerts?service=payments" | python3 -m json.tool

# 查看 audit 日志，验证有 1 次 created + 3 次 merged 记录
curl "http://localhost:8080/api/v1/audit" | python3 -m json.tool

# 验证 fingerprint 一致性：虽然 severity 变了，但 fingerprint 相同
# 对比第1次和第3次推送返回的 fingerprint 字段
```

## 数据模型

### Alert
- `fingerprint`: 告警唯一标识（labels 哈希）
- `dedupe_count`: 合并次数
- `on_call_group`: 匹配到的值班组

### Policy
- `service`/`env`/`severity`: 匹配维度，空或 `*` 表示通配
- `on_call_group`: 命中后分派的值班组

### AuditLog
- `action`: `created` 或 `merged`
- 记录每次告警处理的分派结果
