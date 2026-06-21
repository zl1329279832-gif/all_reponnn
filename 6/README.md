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
  "blackPlayerName": "李四"
}
```

返回: `MatchDto` (包含 matchId、初始 FEN、棋盘显示等)

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
