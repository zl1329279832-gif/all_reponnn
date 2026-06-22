# 企业会议室预定服务

基于 Java 17 + Spring Boot 3.2 的企业内部会议室预定服务。

## 技术栈

- **Java 17**
- **Spring Boot 3.2**
- **SQLite** (单文件数据库，`./data/meeting_room.db`)
- **Flyway** (数据库迁移)
- **JPA / Hibernate**
- **Lombok**

## 核心业务规则

### 会议室属性
- 容量（人数）
- 设备列表（投影仪、白板、视频会议等）
- 可预约时段模板（如 09:00-18:00）

### 预定规则
1. **冲突检测**：预定时段含前后各 **15分钟缓冲**，与已有预定的缓冲重叠即冲突
2. **时长限制**：单次预定最长 **4小时**
3. **跨午夜禁止**：不允许跨零点的预定
4. **时段校验**：必须在会议室可预约时段内
5. **过去时间禁止**：不能预定过去的时间

### 周期预定
- 自动生成未来 **8周** 的重复预定实例
- 每周同一时段自动创建
- 取消其中某一天不影响系列其他日期
- 可单独取消单天，也可取消整个系列

### 查询过滤
- 按楼层过滤
- 按最小容量过滤
- 按日期范围过滤
- 按会议室 ID 过滤

## 启动服务

```bash
# 编译
mvn clean package -DskipTests

# 运行
java -jar target/meeting-room-booking-1.0.0.jar
```

服务启动后监听 **8080** 端口，数据库文件自动创建在 `./data/meeting_room.db`。

## API 接口

### 会议室管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/meeting-rooms` | 查询会议室列表，支持 `floor` 和 `minCapacity` 参数 |
| GET | `/api/meeting-rooms/{id}` | 查询单个会议室 |
| POST | `/api/meeting-rooms` | 创建会议室 |
| PUT | `/api/meeting-rooms/{id}` | 更新会议室 |
| DELETE | `/api/meeting-rooms/{id}` | 删除会议室 |

### 预定管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/reservations` | 查询预定列表，支持 `roomId`, `floor`, `minCapacity`, `startDate`, `endDate` |
| GET | `/api/reservations/{id}` | 查询单个预定 |
| GET | `/api/reservations/series/{seriesId}` | 查询周期预定系列的所有实例 |
| POST | `/api/reservations` | 创建预定（单次或周期） |
| DELETE | `/api/reservations/{id}` | 取消单个预定（即使是周期预定的一天，不影响其他天） |
| DELETE | `/api/reservations/series/{seriesId}` | 取消整个周期预定系列 |

---

## 测试指南

### 前置准备

启动服务后，系统已预置 6 个会议室：

| ID | 名称 | 楼层 | 容量 |
|----|------|------|------|
| 1 | 凤凰厅 | 1 | 10 |
| 2 | 麒麟厅 | 1 | 6 |
| 3 | 玄武厅 | 2 | 20 |
| 4 | 青龙厅 | 2 | 4 |
| 5 | 朱雀厅 | 3 | 15 |
| 6 | 白虎厅 | 3 | 8 |

> **注意**：以下测试示例中，请将日期替换为未来的日期。
> 例如：如果今天是 2026-06-22，则使用 2026-06-23 及以后的日期。

---

### 测试 1: 基本预定功能

**测试目标**：验证可以正常创建单次预定

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 1,
    "employeeId": "E001",
    "employeeName": "张三",
    "title": "项目周会",
    "startTime": "2026-06-23 10:00:00",
    "endTime": "2026-06-23 11:00:00",
    "recurring": false
  }'
```

**预期结果**：HTTP 200，返回创建成功的预定信息。

---

### 测试 2: 冲突检测（15分钟缓冲）

**测试目标**：验证前后15分钟缓冲的冲突检测

#### 步骤 1: 创建一个基准预定

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 2,
    "employeeId": "E002",
    "employeeName": "李四",
    "title": "技术评审",
    "startTime": "2026-06-23 14:00:00",
    "endTime": "2026-06-23 15:00:00",
    "recurring": false
  }'
```

#### 步骤 2: 测试完全重叠冲突

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 2,
    "employeeId": "E003",
    "employeeName": "王五",
    "title": "产品讨论",
    "startTime": "2026-06-23 14:30:00",
    "endTime": "2026-06-23 15:30:00",
    "recurring": false
  }'
```

**预期结果**：HTTP 409，返回类似：
```json
{
  "code": 409,
  "message": "预定时段存在冲突（含前后各 15 分钟缓冲）。冲突的预定: 技术评审 (2026-06-23 14:00 - 15:00, 前后各 15 分钟缓冲)",
  "data": null
}
```

#### 步骤 3: 测试与缓冲区间重叠（仅差10分钟）

尝试预定 13:50-14:00（与 14:00 开始的预定的前15分钟缓冲重叠）:

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 2,
    "employeeId": "E003",
    "employeeName": "王五",
    "title": "紧急会议",
    "startTime": "2026-06-23 13:50:00",
    "endTime": "2026-06-23 14:00:00",
    "recurring": false
  }'
```

**预期结果**：HTTP 409，因为 13:50 与基准预定的前缓冲 13:45-14:00 重叠。

#### 步骤 4: 测试刚好在缓冲之外（成功）

尝试预定 13:45 之前结束：

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 2,
    "employeeId": "E003",
    "employeeName": "王五",
    "title": "早会",
    "startTime": "2026-06-23 13:00:00",
    "endTime": "2026-06-23 13:45:00",
    "recurring": false
  }'
```

**预期结果**：HTTP 200，创建成功。因为结束时间 13:45 刚好等于基准预定的前缓冲开始时间 13:45，不重叠。

---

### 测试 3: 最长4小时限制

**测试目标**：验证单次预定不超过4小时

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 3,
    "employeeId": "E004",
    "employeeName": "赵六",
    "title": "超长会议",
    "startTime": "2026-06-23 09:00:00",
    "endTime": "2026-06-23 14:00:00",
    "recurring": false
  }'
```

**预期结果**：HTTP 400，返回：
```json
{
  "code": 400,
  "message": "单次预定最长不超过 4 小时，当前时长: 5.0 小时",
  "data": null
}
```

**成功情况**（刚好4小时）：

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 3,
    "employeeId": "E004",
    "employeeName": "赵六",
    "title": "正常会议",
    "startTime": "2026-06-23 09:00:00",
    "endTime": "2026-06-23 13:00:00",
    "recurring": false
  }'
```

**预期结果**：HTTP 200，创建成功。

---

### 测试 4: 跨午夜禁止

**测试目标**：验证不允许跨零点的预定

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 1,
    "employeeId": "E005",
    "employeeName": "孙七",
    "title": "夜间派对",
    "startTime": "2026-06-23 22:00:00",
    "endTime": "2026-06-24 02:00:00",
    "recurring": false
  }'
```

**预期结果**：HTTP 400，返回：
```json
{
  "code": 400,
  "message": "不允许跨午夜的预定，请确保开始和结束在同一天",
  "data": null
}
```

---

### 测试 5: 周期预定（自动展开8周）

**测试目标**：验证周期预定自动生成未来8周的实例

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 1,
    "employeeId": "E006",
    "employeeName": "周八",
    "title": "每周项目例会",
    "startTime": "2026-06-24 10:00:00",
    "endTime": "2026-06-24 11:00:00",
    "recurring": true,
    "recurringType": "WEEKLY"
  }'
```

**预期结果**：HTTP 200，返回 8 个预定实例（从 2026-06-24 开始，每周三，共 8 周）。

**验证生成结果**：

```bash
# 获取返回的 seriesId，例如：550e8400-e29b-41d4-a716-446655440000
curl http://localhost:8080/api/reservations/series/{seriesId}
```

**预期结果**：返回 8 条预定记录，日期分别为：
- 2026-06-24 (第1周)
- 2026-07-01 (第2周)
- 2026-07-08 (第3周)
- ... 以此类推，共 8 周

---

### 测试 6: 取消周期预定中的单天（不影响其他天）

**测试目标**：验证取消周期预定的某一天不影响系列其他日期

#### 步骤 1: 先创建一个周期预定（参考测试 5）

假设返回的预定 ID 列表中包含：
- ID 10: 2026-06-24 10:00-11:00
- ID 11: 2026-07-01 10:00-11:00
- ID 12: 2026-07-08 10:00-11:00
- ...

#### 步骤 2: 取消其中一天（ID 11）

```bash
curl -X DELETE http://localhost:8080/api/reservations/11
```

**预期结果**：HTTP 200，取消成功。

#### 步骤 3: 验证系列其他天仍然存在

```bash
curl http://localhost:8080/api/reservations/series/{seriesId}
```

**预期结果**：只返回 7 条记录（2026-07-01 的那一条被取消了，不再显示）。

---

### 测试 7: 取消整个周期预定系列

**测试目标**：验证可以一次性取消整个周期系列

```bash
curl -X DELETE http://localhost:8080/api/reservations/series/{seriesId}
```

**预期结果**：HTTP 200，整个系列的所有未取消预定都被取消。

**验证**：
```bash
curl http://localhost:8080/api/reservations/series/{seriesId}
```

**预期结果**：HTTP 404，提示系列不存在（因为所有实例都已取消）。

---

### 测试 8: 查询过滤功能

**测试目标**：验证按楼层、容量、日期范围过滤

#### 测试 8.1: 按楼层过滤

```bash
# 查询 1 楼的所有会议室
curl "http://localhost:8080/api/meeting-rooms?floor=1"
```

**预期结果**：只返回 1 楼的会议室（凤凰厅、麒麟厅）。

#### 测试 8.2: 按最小容量过滤

```bash
# 查询容量 >= 10 人的会议室
curl "http://localhost:8080/api/meeting-rooms?minCapacity=10"
```

**预期结果**：只返回容量 >= 10 的会议室（凤凰厅10、玄武厅20、朱雀厅15）。

#### 测试 8.3: 组合过滤

```bash
# 查询 2 楼容量 >= 15 人的会议室
curl "http://localhost:8080/api/meeting-rooms?floor=2&minCapacity=15"
```

**预期结果**：只返回玄武厅（2楼，容量20）。

#### 测试 8.4: 按日期范围查询预定

```bash
# 查询 2026-06-23 到 2026-06-30 的所有预定
curl "http://localhost:8080/api/reservations?startDate=2026-06-23&endDate=2026-06-30"
```

#### 测试 8.5: 多条件组合查询预定

```bash
# 查询 1 楼、容量 >= 6人、2026-06-23 的所有预定
curl "http://localhost:8080/api/reservations?floor=1&minCapacity=6&startDate=2026-06-23&endDate=2026-06-23"
```

---

### 测试 9: 可预约时段模板校验

**测试目标**：验证预定时间必须在会议室可预约时段内

查看玄武厅（ID 3）的可预约时段是 09:00-20:00，其他会议室是 09:00-18:00。

```bash
# 尝试在 18:30-19:30 预定凤凰厅（ID 1，可预约到 18:00）
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 1,
    "employeeId": "E007",
    "employeeName": "吴九",
    "title": "加班会议",
    "startTime": "2026-06-23 18:30:00",
    "endTime": "2026-06-23 19:30:00",
    "recurring": false
  }'
```

**预期结果**：HTTP 400，返回：
```json
{
  "code": 400,
  "message": "预定时间不在会议室可预约时段内，当前会议室可预约时段: 09:00-18:00",
  "data": null
}
```

**成功情况**（使用玄武厅，可预约到 20:00）：

```bash
curl -X POST http://localhost:8080/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 3,
    "employeeId": "E007",
    "employeeName": "吴九",
    "title": "加班会议",
    "startTime": "2026-06-23 18:30:00",
    "endTime": "2026-06-23 19:30:00",
    "recurring": false
  }'
```

**预期结果**：HTTP 200，创建成功。

---

## 错误响应格式

所有业务错误返回统一格式，不会返回 500：

```json
{
  "code": 409,
  "message": "预定时段存在冲突（含前后各 15 分钟缓冲）。冲突的预定: 技术评审 (2026-06-23 14:00 - 15:00, 前后各 15 分钟缓冲)",
  "data": null
}
```

| 错误码 | 说明 |
|--------|------|
| 400 | 参数错误 / 业务规则不满足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误（仅系统异常） |

## 数据库文件

SQLite 数据库文件位于 `./data/meeting_room.db`，可直接拷贝备份。

使用 Flyway 管理数据库迁移，迁移脚本位于 `src/main/resources/db/migration/`。

## 项目结构

```
src/main/java/com/meetingroom/
├── MeetingRoomBookingApplication.java    # 启动类
├── controller/
│   ├── MeetingRoomController.java        # 会议室接口（参数校验+响应封装）
│   └── ReservationController.java        # 预定接口（参数校验+响应封装）
├── service/
│   ├── MeetingRoomService.java           # 会议室业务逻辑+SQL
│   └── ReservationService.java           # 预定业务逻辑+SQL（核心规则）
├── repository/
│   ├── MeetingRoomRepository.java
│   └── ReservationRepository.java
├── entity/
│   ├── MeetingRoom.java
│   ├── Reservation.java
│   ├── TimeSlot.java
│   ├── TimeSlotListConverter.java
│   └── EquipmentListConverter.java
├── dto/
│   ├── ApiResponse.java
│   ├── CreateMeetingRoomRequest.java
│   ├── UpdateMeetingRoomRequest.java
│   ├── MeetingRoomResponse.java
│   ├── CreateReservationRequest.java
│   ├── ReservationResponse.java
│   └── TimeSlotDTO.java
└── exception/
    ├── BusinessException.java
    └── GlobalExceptionHandler.java       # 全局异常处理，返回可读业务错误
```
