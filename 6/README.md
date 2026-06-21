# 简化中国象棋后端 (Simplified Chinese Chess Backend)

基于 **Spring Boot 3 + H2 内存数据库** 开发的回合制简化中国象棋后端。

## 技术栈
- Java 17+
- Spring Boot 3.2.0
- Spring Data JPA
- H2 内存数据库 (默认) / SQLite (可选，见下文切换方法)
- Hibernate Validator
- Lombok
- Jackson (JSON 序列化)

## 规则说明 (简化版)
棋盘: 10 行 × 9 列，含楚河汉界 + 九宫格。
棋子类型:
- **帅/将**: 仅在九宫格内走一步直线，双方将帅不能照面
- **车**: 任意直线任意步数
- **马**: 走日字，马脚被堵时不能走
- **炮**: 空走同车；吃子必须且仅隔一个炮架
- **兵/卒**: 过河前只能前进；过河后可横走或前进，不能后退

不含: **士、相、象**。

## 快速开始

### 环境要求
- JDK 17 或更高
- Maven 3.8+
- Windows / macOS / Linux

### 编译与运行

```bash
# 进入项目目录
cd <项目根目录>

# 编译 (跳过测试可选)
mvn clean compile

# 运行全部测试 (包含马脚被堵、炮打隔子、将帅照面等场景)
mvn test

# 启动服务 (默认端口 8080)
mvn spring-boot:run
```

服务启动后:
- API 根路径: `http://localhost:8080/api/`
- H2 控制台: `http://localhost:8080/h2-console`
  - JDBC URL: `jdbc:h2:mem:chessdb`
  - 用户: `sa`
  - 密码: (空)

---

## REST API 接口

### 1. 创建对局
**POST** `/api/matches`

请求体:
```json
{
  "redPlayerId": "player_red_001",
  "blackPlayerId": "player_black_001",
  "redPlayerName": "张三",
  "blackPlayerName": "李四",
  "baseSeconds": 600
}
```

字段说明:
- `redPlayerId` / `blackPlayerId` (必填): 红方/黑方玩家 ID
- `redPlayerName` / `blackPlayerName` (可选): 显示名称
- `baseSeconds` (可选, 正整数): **每方可用总秒数**。不传则不启用计时, 行为与无计时版本完全一致。

返回: `MatchDto` (包含 matchId、初始 FEN、棋盘显示, 启用计时时还含 `baseSeconds` / `redTimeLeft` / `blackTimeLeft`)

---

## 计时功能 (可选)

创建对局时传入 `baseSeconds` 即可启用每方独立倒计时。

### 行为规则
- **不传 `baseSeconds`**: 完全向后兼容, 不做任何计时相关操作, 快照里也不会出现时间字段。
- **启用计时后**:
  - 双方初始剩余时间均为 `baseSeconds`
  - 从第一手开始, 每次轮到某方行棋时, 以「对局创建时间」(首手) 或「上一步成功落子时间」(后续手) 为起点累计占用时间
  - **走子校验通过后**才从该方剩余时间里扣除已用秒数
  - 任意一方时间归零时, 该方直接判负, 对局结束, Elo 照常更新, 之后所有 POST move 返回 400 `对局已结束`
- GET 对局快照 (`/api/matches/{id}/snapshot`) 在启用计时时额外返回 `timerEnabled`、`baseSeconds`、`redTimeLeft`、`blackTimeLeft`

### 如何手工测试超时判负 (PowerShell)

服务冷启动后 (`mvn spring-boot:run`), 连续执行以下命令。建议把 `baseSeconds` 设得很小 (例如 3 秒), 以便快速观察超时:

```powershell
# 1. 创建一个每方只有 3 秒的对局
$body = @{ redPlayerId="alice"; blackPlayerId="bob"; baseSeconds=3 } | ConvertTo-Json
$m = Invoke-RestMethod http://localhost:8080/api/matches -Method Post -Body $body -ContentType application/json
$mid = $m.data.id
Write-Host "Created match $mid, redTimeLeft=$($m.data.redTimeLeft), blackTimeLeft=$($m.data.blackTimeLeft)"

# 2. 查局面快照, 确认 timerEnabled=true, 双方都是 3 秒
$s = Invoke-RestMethod "http://localhost:8080/api/matches/$mid/snapshot"
Write-Host "timerEnabled=$($s.data.timerEnabled), nextTurn=$($s.data.nextTurnPlayerId)"
Write-Host "red=$($s.data.redTimeLeft)s, black=$($s.data.blackTimeLeft)s"

# 3. 红方不立刻走, 等待 5 秒让红方超时 (3 秒用掉 + 2 秒富余)
Start-Sleep -Seconds 5

# 4. 红方再尝试随便走一步, 应返回 400 且 message 含「时间耗尽」
$move = @{ playerId="alice"; fromRow=7; fromCol=1; toRow=7; toCol=4 } | ConvertTo-Json
$r = Invoke-RestMethod "http://localhost:8080/api/matches/$mid/moves" -Method Post -Body $move -ContentType application/json
Write-Host "code=$($r.code), msg=$($r.message)"

# 5. 查对局详情: 状态应为 BLACK_WIN, winner=bob, redTimeLeft=0
$end = Invoke-RestMethod "http://localhost:8080/api/matches/$mid"
Write-Host "status=$($end.data.status), winner=$($end.data.winnerPlayerId)"
Write-Host "redTimeLeft=$($end.data.redTimeLeft), blackTimeLeft=$($end.data.blackTimeLeft)"

# 6. 黑方再尝试走子, 应返回 400「对局已结束」
$move2 = @{ playerId="bob"; fromRow=2; fromCol=1; toRow=2; toCol=4 } | ConvertTo-Json
$r2 = Invoke-RestMethod "http://localhost:8080/api/matches/$mid/moves" -Method Post -Body $move2 -ContentType application/json
Write-Host "code=$($r2.code), msg=$($r2.message)"

# 7. 查双方 Elo: bob 胜, alice 负, 分数应有变化
$alice = Invoke-RestMethod "http://localhost:8080/api/players/alice"
$bob = Invoke-RestMethod "http://localhost:8080/api/players/bob"
Write-Host "alice elo=$($alice.data.eloRating), wins=$($alice.data.wins), losses=$($alice.data.losses)"
Write-Host "bob elo=$($bob.data.eloRating), wins=$($bob.data.wins), losses=$($bob.data.losses)"
```

预期输出要点:
- Step 1: `redTimeLeft=3, blackTimeLeft=3`
- Step 2: `timerEnabled=True, nextTurn=alice`
- Step 4: `code=400`, message 包含「时间耗尽」
- Step 5: `status=BLACK_WIN, winner=bob, redTimeLeft=0`
- Step 6: `code=400`, message 包含「对局已结束」
- Step 7: bob 的 `wins=1`、alice 的 `losses=1`, Elo 一升一降

### 2. 走一步棋
**POST** `/api/matches/{matchId}/moves`

请求体:
```json
{
  "playerId": "player_red_001",
  "fromRow": 7,
  "fromCol": 1,
  "toRow": 7,
  "toCol": 4
}
```

坐标说明:
- 行 (row): 0 (黑方底线) ~ 9 (红方底线)
- 列 (col): 0 (左) ~ 8 (右)
- 初始红方 (RED): 车(9,0)、马(9,1)、帅(9,4)、炮(7,1)/(7,7)、兵(6,0)/(6,2)/(6,4)/(6,6)/(6,8)

返回成功: MoveDto，含走子详情；失败: `code=400`，message 为可读错误 (如「马脚被堵，无法移动」「炮吃子时必须且只能隔一个棋子（炮架）」「将帅不能照面」「不是你的回合」等)

### 3. 获取对局详情
**GET** `/api/matches/{matchId}`

### 4. 获取完整棋谱 (回放用)
**GET** `/api/matches/{matchId}/moves`

返回按 moveNumber 升序的所有走子记录列表。

### 5. 获取当前局面快照 (观战用)
**GET** `/api/matches/{matchId}/snapshot`

返回:
```json
{
  "code": 200,
  "data": {
    "matchId": 1,
    "status": "IN_PROGRESS",
    "nextTurnPlayerId": "player_black_001",
    "currentTurn": 1,
    "fen": "...",
    "board": [
      "车B 马B . . 将B . . 马B 车B",
      "...",
      "车R 马R . . 帅R . . 马R 车R"
    ],
    "redPlayerId": "...",
    "redPlayerName": "...",
    "blackPlayerId": "...",
    "blackPlayerName": "..."
  }
}
```

### 6. FEN 等价接口
**GET** `/api/matches/{matchId}/fen` (同 snapshot)

### 7. 查询玩家信息
**GET** `/api/players/{playerId}`

### 8. 排行榜 (分页 + Elo 排序)
**GET** `/api/players/leaderboard?page=0&size=20`

---

## 并发控制

同一对局的走子接口使用 **ReentrantLock** (ConcurrentHashMap<matchId, Lock>) 做细粒度锁，
配合 JPA `@Version` 乐观锁双重保护，确保：
> 红黑双方几乎同时 POST 时只能一方成功，另一方返回 400 **「不是你的回合」**

并发测试位于 `ChessApplicationIntegrationTest.testConcurrentMovesOnlyOneSucceeds()`。

---

## Elo Rating 规则

初始分 1500，K=32。
胜负判定: 将帅被吃时游戏结束。
- 胜者 +，负者 -；和棋双方各半调整。
自动更新胜/负/和局数统计。

---

## 如何切换到 SQLite 文件库

### 步骤 1: 修改 `pom.xml` — 移除 H2，添加 SQLite 依赖
```xml
<!-- <dependency>
    <groupId>com.h2database</groupId>
    <artifactId>h2</artifactId>
    <scope>runtime</scope>
</dependency> -->

<dependency>
    <groupId>org.xerial</groupId>
    <artifactId>sqlite-jdbc</artifactId>
    <version>3.44.1.0</version>
</dependency>
<dependency>
    <groupId>org.hibernate.orm</groupId>
    <artifactId>hibernate-community-dialects</artifactId>
    <version>6.4.0.Final</version>
</dependency>
```

### 步骤 2: 修改 `src/main/resources/application.properties`
```properties
# --- SQLite 文件库 (持久化到本地文件 chess.db)
spring.datasource.url=jdbc:sqlite:./chess.db
spring.datasource.driver-class-name=org.sqlite.JDBC
spring.datasource.username=
spring.datasource.password=

# H2 控制台 (SQLite 不支持)
# spring.h2.console.enabled=false

spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=false
spring.jpa.properties.hibernate.dialect=org.hibernate.community.dialect.SQLiteDialect
```

### 步骤 3: 重新编译运行
```bash
mvn clean spring-boot:run
```

---

## 测试用例清单 (src/test/java)

| 测试类 | 测试方法 | 覆盖场景 |
|--------|----------|---------|
| ChessBoardTest | testHorseBlockedLeg | 马脚被堵拒绝 |
| ChessBoardTest | testCannonCaptureWithoutScreen / testCannonCaptureWithOneScreen / testCannonCaptureWithMultipleScreens | 炮打隔子 (无/有/多) |
| ChessBoardTest | testGeneralsFacingRejected | 将帅照面拒绝 |
| ChessBoardTest | 其余 10+ 用例 | 车、兵卒、九宫、序列化等 |
| ChessApplicationIntegrationTest | 多个 API 场景 | 创建对局、走子、快照、棋谱回放、排行榜 |
| ChessApplicationIntegrationTest | testConcurrentMovesOnlyOneSucceeds | 并发 POST move 控制 |
| ChessApplicationIntegrationTest | testNotYourTurn | 不是你的回合 |
| ChessApplicationIntegrationTest | 参数校验 / 404 |
| ChessApplicationIntegrationTest | testCreateMatchWithTimer | 带计时对局创建，初始时间字段 |
| ChessApplicationIntegrationTest | testCreateMatchNoTimerBackwardCompatible | 不传 baseSeconds 不启用计时，向后兼容 |
| ChessApplicationIntegrationTest | testTimeoutLosesGame | 红方时间耗尽判负，Elo 更新，对局结束后不能再走子 |
| ChessApplicationIntegrationTest | testTimerInSnapshot | GET 快照带剩余时间与当前行棋方 |

运行测试:
```bash
mvn test
```

---

## 项目结构

```
src/
├── main/
│   ├── java/com/chess/
│   │   ├── ChessApplication.java          # 启动类
│   │   ├── controller/
│   │   │   ├── MatchController.java   # 对局相关 API
│   │   │   └── PlayerController.java  # 玩家 & 排行榜
│   │   ├── dto/                          # 请求/响应 DTO
│   │   ├── engine/                       # 象棋规则引擎
│   │   │   ├── ChessBoard.java
│   │   │   ├── PieceType.java
│   │   │   ├── Position.java
│   │   │   └── MoveValidationResult.java
│   │   ├── entity/                       # JPA 实体
│   │   │   ├── Player.java
│   │   │   ├── Match.java (含 @Version 乐观锁)
│   │   │   └── Move.java
│   │   ├── exception/
│   │   │   └── GlobalExceptionHandler.java
│   │   ├── repository/
│   │   └── service/
│   │       ├── MatchService.java  (含 ConcurrentHashMap<Long, ReentrantLock> 并发锁)
│   │       ├── PlayerService.java
│   │       └── EloService.java
│   └── resources/
│       └── application.properties
└── test/java/com/chess/
    ├── engine/ChessBoardTest.java
    └── ChessApplicationIntegrationTest.java
```

## 注意事项

1. **不可修改历史局面**: 每次走子只追加 Move 新记录，Match.boardSnapshot 只更新当前快照；旧快照保留在对应 Move.boardSnapshotAfter 字段，完整棋谱可回放。
2. **端口**: 8080 (application.properties 里可改 server.port。
3. **H2 为内存库，重启后数据清空；切换 SQLite 后数据持久化。
4. **坐标**: row=0 为黑方底线 (黑将起点)，row=9 为红方底线。
