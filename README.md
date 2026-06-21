# Draw & Guess Party Game Backend

基于 Java 17 + Spring Boot 3 + SQLite 的「你画我猜」类休闲派对游戏后端 API。

## 技术栈

- Java 17
- Spring Boot 3.2.5
- Spring Data JPA
- SQLite (单文件数据库)
- Lombok
- Hibernate Community Dialects (SQLite 支持)

## 快速开始

### 环境要求
- JDK 17+
- Maven 3.8+

### 启动服务

```bash
mvn spring-boot:run
```

服务默认启动在 `http://localhost:8080`，数据库文件 `game.db` 会自动创建在项目根目录。

## 数据库表结构

- `players` - 玩家表（id, open_id, nickname, created_at）
- `rooms` - 房间表（id, room_code, room_name, password, max_players, total_rounds, status, owner_id, ...）
- `room_players` - 房间玩家关联表
- `room_ready_players` - 房间已准备玩家表
- `games` - 对局表（id, room_id, room_code, total_rounds, completed_rounds, winner_id, ...）
- `game_scores` - 对局得分表
- `game_players` - 对局玩家表
- `rounds` - 轮次表（id, game_id, round_number, drawer_id, target_word, description, ...）
- `round_guessers` - 轮次猜词者表
- `round_submissions` - 提交记录表（id, round_id, player_id, submission_type, content, is_correct, score_earned, ...）

## Room Code 生成规则

Room Code 是 6 位大写字符，字符集为 `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`（去掉易混淆的 I/O/0/1）。

生成逻辑在 [RoomService.java](file:///c:/Users/13292/Desktop/solocode/all_reponnn/5/src/main/java/com/party/drawguess/service/RoomService.java#L237-L253) 的 `generateRoomCode()` 方法：
1. 使用 `SecureRandom` 从 32 个字符中随机选取 6 位
2. 生成后检查数据库是否已存在，若冲突则重新生成
3. 最多重试 100 次，失败则抛出异常

## REST API 接口

### 1. 玩家注册

```bash
curl -X POST http://localhost:8080/api/players/register \
  -H "Content-Type: application/json" \
  -d '{
    "openId": "player_001",
    "nickname": "小明"
  }'
```

响应：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "openId": "player_001",
    "nickname": "小明"
  }
}
```

---

### 2. 创建房间

```bash
curl -X POST http://localhost:8080/api/rooms/create \
  -H "Content-Type: application/json" \
  -d '{
    "roomName": "欢乐画画房",
    "password": "1234",
    "maxPlayers": 4,
    "totalRounds": 3,
    "ownerId": 1
  }'
```

参数说明：
- `password` 可选，不传则为公开房间
- `maxPlayers` 默认 4，范围 2-8
- `totalRounds` 默认 5，范围 1-20

---

### 3. 加入房间

```bash
# 注册玩家2
curl -X POST http://localhost:8080/api/players/register \
  -H "Content-Type: application/json" \
  -d '{"openId": "player_002", "nickname": "小红"}'

# 加入房间（带密码）
curl -X POST http://localhost:8080/api/rooms/join \
  -H "Content-Type: application/json" \
  -d '{
    "roomCode": "ABC123",
    "password": "1234",
    "playerId": 2
  }'
```

> 注意：`roomCode` 大小写不敏感，服务端自动转大写。

---

### 4. 准备游戏

```bash
# 玩家1准备（房主默认已准备）
curl -X POST http://localhost:8080/api/rooms/ready \
  -H "Content-Type: application/json" \
  -d '{
    "playerId": 1,
    "roomId": 1
  }'

# 玩家2准备
curl -X POST http://localhost:8080/api/rooms/ready \
  -H "Content-Type: application/json" \
  -d '{
    "playerId": 2,
    "roomId": 1
  }'
```

---

### 5. 房主开始游戏

```bash
curl -X POST http://localhost:8080/api/rooms/start \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 1,
    "ownerId": 1
  }'
```

> 必须所有玩家都准备后才能开始，且只有房主可以开始。

---

### 6. 提交本轮画作描述（出题者）

游戏开始后，系统自动指定本轮出题者（第1轮是房主，之后轮流）。

```bash
curl -X POST http://localhost:8080/api/games/submit-description \
  -H "Content-Type: application/json" \
  -d '{
    "gameId": 1,
    "roundNumber": 1,
    "playerId": 1,
    "targetWord": "苹果",
    "description": "一种红色的水果，圆形，口感脆甜"
  }'
```

**幂等性**：同一玩家同一轮重复提交会返回 `409 Conflict`，明确报错「本轮描述已提交，请勿重复提交」。

---

### 7. 提交猜词结果（猜词者）

```bash
# 玩家2猜词
curl -X POST http://localhost:8080/api/games/submit-guess \
  -H "Content-Type: application/json" \
  -d '{
    "gameId": 1,
    "roundNumber": 1,
    "playerId": 2,
    "guess": "苹果"
  }'
```

**幂等性**：同一玩家同一轮重复猜词会返回 `409 Conflict`，明确报错「你已提交过本轮猜词，请勿重复提交」。

**得分规则**：
- 猜词者猜对得 10 分
- 第一个猜对的人猜对时，出题者额外得 5 分
- 所有猜词者都提交后自动进入下一轮

---

### 8. 查询当前房间快照

```bash
curl http://localhost:8080/api/rooms/1/snapshot
```

返回房间完整状态，包括：
- 房间基本信息（状态、人数、当前轮次等）
- 玩家列表（是否房主、是否准备）
- 当前得分
- 当前轮次详情（出题者、描述、所有提交内容）

---

### 9. 分页查我的对局记录

```bash
curl "http://localhost:8080/api/games/my?playerId=1&page=0&size=10"
```

返回指定玩家参与过的所有对局，按开始时间倒序分页。包含每轮详细数据和每笔提交记录。

---

### 10. 查询单局详情

```bash
curl http://localhost:8080/api/games/1
```

---

### 11. 再来一局（Rematch）

对局结束后（状态 = FINISHED），房主可以发起「再来一局」，玩家列表保持不变，无需重新 join，分数清零，按原 `totalRounds` 重开：

```bash
curl -X POST http://localhost:8080/api/rooms/rematch \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": 1,
    "ownerId": 1
  }'
```

**约束**：
- 只有房主可以发起
- 房间状态必须为 `FINISHED`（等待中 / 进行中不能 rematch）
- 玩家数 ≥ 2
- 原有玩家列表、maxPlayers、roomCode 全部保留
- 新生成独立的 `Game` 记录，分数从零开始，历史对局不受影响

**历史查询**：
- 同房间下会有多条 `Game` 记录，可按 `startedAt` 倒序查看
- `GET /api/games/my?playerId=1` 分页查我的对局不受影响，新旧对局都在列表中

---

## 并发控制

- **房间加入并发控制**：使用 `ConcurrentHashMap` 按 roomCode 加锁，确保同一房间并发 join 不会超员（[RoomService.java](file:///c:/Users/13292/Desktop/solocode/all_reponnn/5/src/main/java/com/party/drawguess/service/RoomService.java#L52-L89)）
- **提交幂等控制**：数据库层对 `(round_id, player_id, submission_type)` 加唯一约束；应用层使用 `ConcurrentHashMap` 按提交维度加锁，双重保证
- **重复加入拒绝**：同一 open_id 已在房间中时返回 `409 Conflict`

## 房间状态流转

```
WAITING (等待中)
    ↓ 房主点击开始，所有人已准备
PLAYING (进行中)
    ↓ 所有轮次完成
FINISHED (已结束)
    ↓ 房主发起 rematch
PLAYING (再来一局)
```

## 项目结构

```
src/main/java/com/party/drawguess/
├── DrawGuessGameApplication.java    # 启动类
├── config/
│   └── WebConfig.java              # CORS、序列化配置
├── controller/
│   ├── PlayerController.java       # 玩家注册
│   ├── RoomController.java         # 房间管理
│   └── GameController.java         # 游戏交互
├── dto/                            # 请求/响应对象
├── exception/
│   ├── GameException.java          # 业务异常
│   └── GlobalExceptionHandler.java # 全局异常处理
├── model/                          # JPA 实体
├── repository/                     # JPA Repository
└── service/
    ├── PlayerService.java
    ├── RoomService.java            # 房间逻辑（含并发锁）
    └── GameService.java            # 游戏逻辑（含幂等处理）
```
