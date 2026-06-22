# 实验室耗材申领后台 (Lab Requisition System)

基于 Spring Boot 3 + Java 17 + H2 的实验室耗材申领管理系统。

## 技术栈

- Java 17
- Spring Boot 3.2.5
- Spring Data JPA
- H2 内嵌数据库
- Maven
- Lombok

## 功能特性

- **耗材 SKU 管理**: 维护耗材信息、类别、所属实验室、安全库存阈值
- **库位库存管理**: 多库位库存，支持总库存查询
- **申领单管理**: 研究员提交申领，自动扣减可用库存
- **审批流程**: 主管审批通过 / 驳回，驳回自动恢复库存
- **审计记录**: 所有操作都留痕，支持按申领单查询审计日志
- **库存预警**: 每分钟扫描库存，低于安全线自动生成预警事件
- **并发控制**: JPA 乐观锁防止超卖
- **幂等性**: 相同 `Idempotency-Key` 请求头的重复 POST 返回同一张单

## 快速开始

### 环境要求

- JDK 17+
- Maven 3.9+ (或使用项目内置的 mvnw)

### 启动服务

Windows:
```bash
mvnw spring-boot:run
```

Linux/Mac:
```bash
./mvnw spring-boot:run
```

服务启动后访问: http://localhost:8080

### H2 控制台

http://localhost:8080/h2-console

- JDBC URL: `jdbc:h2:mem:labdb`
- 用户名: `sa`
- 密码: (空)

## API 接口

### 1. SKU 管理

#### 查询 SKU 列表（支持分页、筛选）
```bash
curl "http://localhost:8080/api/skus?page=0&size=10"
curl "http://localhost:8080/api/skus?category=耗材&lab=生物实验室A"
```

#### 创建 SKU
```bash
curl -X POST http://localhost:8080/api/skus \
  -H "Content-Type: application/json" \
  -d '{
    "skuCode": "SKU-TEST-001",
    "name": "测试耗材",
    "category": "耗材",
    "unit": "个",
    "lab": "生物实验室A",
    "safetyStock": 50
  }'
```

### 2. 库存管理

#### 查询库存
```bash
curl "http://localhost:8080/api/inventory"
curl "http://localhost:8080/api/inventory/sku/1"
curl "http://localhost:8080/api/inventory/sku/1/total"
```

#### 新增库存记录
```bash
curl -X POST http://localhost:8080/api/inventory \
  -H "Content-Type: application/json" \
  -d '{
    "skuId": 1,
    "location": "A-03-01",
    "quantity": 100
  }'
```

### 3. 申领单管理

#### 提交申领（带幂等键，推荐）
```bash
curl -X POST http://localhost:8080/api/requisitions \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: req-2024-001" \
  -d '{
    "skuId": 1,
    "quantity": 10,
    "researcher": "张三",
    "purpose": "细胞培养实验"
  }'
```

#### 重复提交相同幂等键（返回同一张单，不双扣）
```bash
curl -X POST http://localhost:8080/api/requisitions \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: req-2024-001" \
  -d '{
    "skuId": 1,
    "quantity": 10,
    "researcher": "张三",
    "purpose": "细胞培养实验"
  }'
```

#### 查询申领单列表
```bash
curl "http://localhost:8080/api/requisitions?status=PENDING"
curl "http://localhost:8080/api/requisitions?researcher=张三"
```

### 4. 审批管理

#### 审批通过
```bash
curl -X POST http://localhost:8080/api/requisitions/1/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approver": "李主管",
    "remark": "同意，注意节约使用"
  }'
```

#### 审批驳回（库存自动恢复）
```bash
curl -X POST http://localhost:8080/api/requisitions/1/reject \
  -H "Content-Type: application/json" \
  -d '{
    "approver": "李主管",
    "remark": "数量过多，请核实后重新提交"
  }'
```

#### 查看审计记录
```bash
curl http://localhost:8080/api/requisitions/1/audit-logs
```

### 5. 库存预警

#### 分页查询预警（支持按实验室、类别筛选）
```bash
curl "http://localhost:8080/api/stock-alerts?page=0&size=10"
curl "http://localhost:8080/api/stock-alerts?lab=生物实验室A&category=耗材"
curl "http://localhost:8080/api/stock-alerts?status=ACTIVE"
```

#### 手动触发预警扫描（调试用）
```bash
curl -X POST http://localhost:8080/api/stock-alerts/scan
```

#### 标记预警为已解决
```bash
curl -X POST http://localhost:8080/api/stock-alerts/1/resolve
```

## 项目结构

```
src/main/java/com/lab/requisition/
├── LabRequisitionApplication.java    # Spring Boot 启动类
├── controller/                       # Controller 层（REST 接口）
│   ├── SkuController.java
│   ├── InventoryController.java
│   ├── RequisitionController.java
│   └── StockAlertController.java
├── service/                          # Service 层（业务逻辑）
│   ├── SkuService.java
│   ├── InventoryService.java
│   ├── RequisitionService.java
│   ├── AuditService.java
│   └── StockAlertService.java
├── repository/                       # Repository 层（数据访问）
│   ├── SkuRepository.java
│   ├── InventoryRepository.java
│   ├── RequisitionRepository.java
│   ├── AuditLogRepository.java
│   └── StockAlertRepository.java
├── entity/                           # 实体类
│   ├── Sku.java
│   ├── Inventory.java
│   ├── Requisition.java
│   ├── AuditLog.java
│   └── StockAlert.java
├── dto/                              # 请求 DTO
│   ├── SkuCreateRequest.java
│   ├── InventoryCreateRequest.java
│   ├── RequisitionCreateRequest.java
│   └── ApprovalRequest.java
├── scheduler/                        # 定时任务
│   └── StockAlertScheduler.java
└── exception/                        # 异常处理
    └── GlobalExceptionHandler.java
```

## 核心设计说明

### 并发控制（防超卖）
使用 JPA `@Version` 乐观锁机制，库存更新时校验版本号。如果并发请求导致版本冲突，
会抛出 `ObjectOptimisticLockingFailureException`，由全局异常处理器返回 409 冲突，
前端可提示用户重试。

### 幂等性
通过请求头 `Idempotency-Key` 实现。首次请求时保存该 key 与申领单的关联，
后续相同 key 的请求直接返回已创建的申领单，不会重复扣减库存。

### 库存预警
每分钟执行一次定时任务（`@Scheduled(fixedRate = 60000)`），扫描所有设置了
安全库存的 SKU。当库存低于安全阈值时生成预警事件，库存恢复后自动标记为已解决。
预警级别：低于安全线 30% 以下为 CRITICAL，其余为 WARNING。

### 审计记录
所有关键操作（申领创建、审批通过、审批驳回、库存扣减、库存恢复）都会写入
`audit_logs` 表，支持按申领单 ID 查询完整操作轨迹。
