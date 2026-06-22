# 同城即时配送后台系统

基于 Spring Boot 3.2 + JPA 的同城即时配送后台接口系统，支持商家下单、智能派单、骑手接单、状态流转、轨迹记录等完整配送流程。

## 技术栈

- **Java 17**
- **Spring Boot 3.2.5**
- **Spring Data JPA**
- **H2 Database** (默认，文件模式)
- **PostgreSQL** (可切换)
- **Lombok**

## 项目结构

```
src/main/java/com/delivery/
├── InstantDeliveryApplication.java   # 启动类
├── common/                           # 通用类
│   └── Result.java                   # 统一响应结果
├── controller/                       # 控制层
│   ├── AdminController.java          # 管理员接口（改派、强制取消）
│   ├── GlobalExceptionHandler.java   # 全局异常处理
│   ├── OrderController.java          # 运单接口
│   ├── RiderController.java          # 骑手接口
│   └── StatisticsController.java     # 统计接口
├── dto/                              # 数据传输对象
│   ├── CreateOrderRequest.java
│   ├── CreateRiderRequest.java
│   ├── OrderCallbackRequest.java
│   ├── ReassignRequest.java
│   └── RiderWorkloadDTO.java
├── entity/                           # 实体类
│   ├── DeliveryOrder.java            # 运单
│   ├── IdempotentRecord.java         # 幂等记录
│   ├── Rider.java                    # 骑手
│   └── TrackEvent.java               # 轨迹事件
├── enums/                            # 枚举
│   ├── OrderStatus.java              # 运单状态
│   ├── RiderStatus.java              # 骑手状态
│   └── TrackEventType.java           # 轨迹事件类型
├── exception/                        # 异常
│   ├── BusinessException.java
│   └── StatusTransitionException.java
├── repository/                       # 数据访问层
│   ├── DeliveryOrderRepository.java
│   ├── IdempotentRecordRepository.java
│   ├── RiderRepository.java
│   └── TrackEventRepository.java
├── service/                          # 业务逻辑层
│   ├── DispatchService.java          # 派单服务
│   ├── IdempotentService.java        # 幂等服务
│   ├── OrderService.java             # 运单服务
│   ├── OrderStateMachine.java        # 状态机
│   ├── RiderService.java             # 骑手服务
│   ├── StatisticsService.java        # 统计服务
│   └── TrackEventService.java        # 轨迹服务
└── util/
    └── GridUtils.java                # 网格工具类
```

## 核心功能

### 1. 运单状态机

状态流转路径：
```
待揽收(PENDING_PICKUP) → 已揽收(PICKED_UP) → 配送中(IN_TRANSIT) → 已签收(DELIVERED)
                              ↓                        ↓
                          已取消(CANCELLED)        已取消(CANCELLED)
```

- 状态流转逻辑封装在 `OrderStateMachine` 中，Controller 不直接操作状态
- 终态（已签收、已取消）不可再流转

### 2. 智能派单策略

- **同网格优先**：优先匹配收件地址所在网格的空闲骑手
- **单量最少优先**：同网格内选择当前单量最少的骑手
- **距离兜底**：同网格无空闲骑手时，按距离由近及远选择

### 3. 幂等性保障

- 同一运单号 + 同一事件类型 的重复回调只推进一次状态
- 支持自定义 requestId 作为幂等键
- 乱序回调会被状态机拒收

### 4. 取消回滚

- 已揽收后取消运单，自动回滚扣款标记（deducted = false）
- 记录 CANCELLED_ROLLBACK 轨迹事件

### 5. 轨迹时间线

- 每个关键节点自动记录轨迹事件
- 支持按运单号查询完整轨迹时间线

## 快速开始

### 环境要求

- JDK 17+
- Maven 3.6+

### 构建与运行（Windows）

```powershell
# 打包
mvn clean package -DskipTests

# 运行（默认 H2 文件模式）
java -jar target/instant-delivery-1.0.0.jar

# 或者使用 Maven 直接运行
mvn spring-boot:run
```

服务启动后访问：http://localhost:8080

H2 控制台：http://localhost:8080/h2-console

### 切换到 PostgreSQL

修改 `application.yml` 中的 active profile：

```yaml
spring:
  profiles:
    active: pg
```

或启动时指定：

```bash
java -jar target/instant-delivery-1.0.0.jar --spring.profiles.active=pg
```

## API 接口

### 运单接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/orders` | 商家下单 |
| GET | `/api/orders/{orderNo}` | 查询运单详情 |
| GET | `/api/orders` | 运单列表（支持状态筛选） |
| POST | `/api/orders/{orderNo}/accept` | 骑手接单 |
| POST | `/api/orders/{orderNo}/callback` | 状态回调 |
| POST | `/api/orders/{orderNo}/cancel` | 取消运单 |
| GET | `/api/orders/{orderNo}/timeline` | 轨迹时间线 |
| GET | `/api/orders/rider/{riderId}` | 骑手运单列表 |

### 骑手接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/riders` | 创建骑手 |
| GET | `/api/riders/{id}` | 查询骑手详情 |
| GET | `/api/riders/no/{riderNo}` | 按编号查询 |
| GET | `/api/riders` | 骑手列表 |
| PUT | `/api/riders/{id}/status` | 更新骑手状态 |
| PUT | `/api/riders/{id}/location` | 更新骑手位置 |
| GET | `/api/riders/{id}/workload` | 骑手负载 |

### 统计接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/statistics/overview` | 总览统计 |
| GET | `/api/statistics/riders/workload` | 骑手负载排行 |
| GET | `/api/statistics/grids` | 网格维度统计 |

### 管理员接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/admin/orders/reassign` | 运单改派 |
| POST | `/api/admin/orders/{orderNo}/cancel` | 管理员取消 |

## 回调事件类型

支持的事件类型（`TrackEventType`）：

- `ORDER_CREATED` - 运单创建
- `ORDER_ASSIGNED` - 骑手接单
- `PICKUP_ARRIVED` - 到达取货点
- `PICKED_UP` - 已取货（推进状态：已揽收）
- `DELIVERY_TRANSIT` - 配送途中（推进状态：配送中）
- `DELIVERY_ARRIVED` - 到达收货点
- `DELIVERED` - 已签收（推进状态：已签收）
- `REASSIGNED` - 运单改派
- `CANCELLED` - 运单取消
- `CANCELLED_ROLLBACK` - 取消回滚

## 测试

运行集成测试：

```powershell
mvn test
```

测试覆盖范围：
- 运单创建与查询
- 状态机流转（正常路径 + 异常路径）
- 幂等性（重复回调只推进一次）
- 乱序回调拒绝
- 取消回滚（已揽收后取消）
- 运单改派
- 轨迹时间线排序
- 骑手负载统计
- 派单策略（同网格优先）

## 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `delivery.grid-size` | 0.01 | 网格大小（度） |
| `delivery.max-orders-per-rider` | 10 | 骑手最大同时接单量 |

## 数据库表说明

### delivery_order - 运单表
### rider - 骑手表
### track_event - 轨迹事件表
### idempotent_record - 幂等记录表

详细字段请参考实体类定义。

## License

MIT
