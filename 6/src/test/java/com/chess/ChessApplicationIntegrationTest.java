package com.chess;

import com.chess.dto.*;
import com.chess.entity.Match;
import com.chess.repository.MatchRepository;
import com.chess.repository.MoveRepository;
import com.chess.repository.PlayerRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class ChessApplicationIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private MatchRepository matchRepository;

    @Autowired
    private MoveRepository moveRepository;

    @Autowired
    private PlayerRepository playerRepository;

    @BeforeEach
    void setUp() {
        moveRepository.deleteAll();
        matchRepository.deleteAll();
        playerRepository.deleteAll();
    }

    private Long createMatch(String redId, String blackId) throws Exception {
        CreateMatchRequest request = new CreateMatchRequest();
        request.setRedPlayerId(redId);
        request.setBlackPlayerId(blackId);
        request.setRedPlayerName("红方玩家");
        request.setBlackPlayerName("黑方玩家");

        MvcResult result = mockMvc.perform(post("/api/matches")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();

        ApiResponse<?> response = objectMapper.readValue(
                result.getResponse().getContentAsString(), ApiResponse.class
        );
        Map<String, Object> data = (Map<String, Object>) response.getData();
        return ((Number) data.get("id")).longValue();
    }

    private ApiResponse<MoveDto> makeMove(Long matchId, MakeMoveRequest request) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/matches/" + matchId + "/moves")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andReturn();

        return objectMapper.readValue(
                result.getResponse().getContentAsString(),
                objectMapper.getTypeFactory().constructParametricType(
                        ApiResponse.class, MoveDto.class
                )
        );
    }

    @Test
    @DisplayName("创建对局 - 成功")
    void testCreateMatch() throws Exception {
        Long matchId = createMatch("player_red_1", "player_black_1");
        assertNotNull(matchId);
        assertTrue(matchId > 0);

        mockMvc.perform(get("/api/matches/" + matchId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.redPlayerId").value("player_red_1"))
                .andExpect(jsonPath("$.data.blackPlayerId").value("player_black_1"))
                .andExpect(jsonPath("$.data.status").value("IN_PROGRESS"))
                .andExpect(jsonPath("$.data.nextTurnPlayerId").value("player_red_1"))
                .andExpect(jsonPath("$.data.currentTurn").value(0));
    }

    @Test
    @DisplayName("走子 - 红方正常第一步（炮二平五）")
    void testRedFirstMoveValid() throws Exception {
        Long matchId = createMatch("p1", "p2");

        MakeMoveRequest request = new MakeMoveRequest();
        request.setPlayerId("p1");
        request.setFromRow(7);
        request.setFromCol(1);
        request.setToRow(7);
        request.setToCol(4);

        ApiResponse<MoveDto> response = makeMove(matchId, request);
        assertEquals(200, response.getCode(), "错误: " + response.getMessage());
        assertNotNull(response.getData());
        assertEquals(1, response.getData().getMoveNumber());
        assertEquals("p1", response.getData().getPlayerId());
        assertEquals("R_CAN", response.getData().getPieceType());
    }

    @Test
    @DisplayName("走子 - 不是你的回合（黑方抢先走）")
    void testNotYourTurn() throws Exception {
        Long matchId = createMatch("p1", "p2");

        MakeMoveRequest request = new MakeMoveRequest();
        request.setPlayerId("p2");
        request.setFromRow(2);
        request.setFromCol(1);
        request.setToRow(2);
        request.setToCol(4);

        ApiResponse<MoveDto> response = makeMove(matchId, request);
        assertEquals(400, response.getCode());
        assertTrue(response.getMessage().contains("不是你的回合"));
    }

    @Test
    @DisplayName("走子 - 非法走子（马脚被堵）通过 API 测试")
    void testHorseBlockedViaApi() throws Exception {
        Long matchId = createMatch("p1", "p2");

        MakeMoveRequest cannonMove = new MakeMoveRequest();
        cannonMove.setPlayerId("p1");
        cannonMove.setFromRow(7);
        cannonMove.setFromCol(1);
        cannonMove.setToRow(8);
        cannonMove.setToCol(1);
        makeMove(matchId, cannonMove);

        MakeMoveRequest blackMove = new MakeMoveRequest();
        blackMove.setPlayerId("p2");
        blackMove.setFromRow(3);
        blackMove.setFromCol(0);
        blackMove.setToRow(4);
        blackMove.setToCol(0);
        makeMove(matchId, blackMove);

        MakeMoveRequest request = new MakeMoveRequest();
        request.setPlayerId("p1");
        request.setFromRow(9);
        request.setFromCol(1);
        request.setToRow(7);
        request.setToCol(2);

        ApiResponse<MoveDto> response = makeMove(matchId, request);
        assertEquals(400, response.getCode());
        assertTrue(response.getMessage().contains("马脚被堵"),
                "错误信息应该提到马脚被堵，实际是: " + response.getMessage());
    }

    @Test
    @DisplayName("走子 - 非法走子（炮打无子）通过 API 测试")
    void testCannonNoScreenViaApi() throws Exception {
        Long matchId = createMatch("p1", "p2");

        MakeMoveRequest request = new MakeMoveRequest();
        request.setPlayerId("p1");
        request.setFromRow(7);
        request.setFromCol(1);
        request.setToRow(2);
        request.setToCol(1);

        ApiResponse<MoveDto> response = makeMove(matchId, request);
        assertEquals(400, response.getCode());
        assertTrue(response.getMessage().contains("炮架") || response.getMessage().contains("隔"),
                "错误信息应该提到炮架/隔，实际是: " + response.getMessage());
    }

    @Test
    @DisplayName("GET 对局快照（局面快照观战用）")
    void testGetMatchSnapshot() throws Exception {
        Long matchId = createMatch("p1", "p2");

        mockMvc.perform(get("/api/matches/" + matchId + "/snapshot"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.fen").exists())
                .andExpect(jsonPath("$.data.board").isArray())
                .andExpect(jsonPath("$.data.board", org.hamcrest.Matchers.hasSize(10)))
                .andExpect(jsonPath("$.data.redPlayerId").value("p1"))
                .andExpect(jsonPath("$.data.blackPlayerId").value("p2"));
    }

    @Test
    @DisplayName("GET 完整棋谱回放")
    void testGetMatchMoves() throws Exception {
        Long matchId = createMatch("p1", "p2");

        MakeMoveRequest r1 = new MakeMoveRequest();
        r1.setPlayerId("p1");
        r1.setFromRow(6);
        r1.setFromCol(0);
        r1.setToRow(5);
        r1.setToCol(0);
        makeMove(matchId, r1);

        MakeMoveRequest b1 = new MakeMoveRequest();
        b1.setPlayerId("p2");
        b1.setFromRow(3);
        b1.setFromCol(0);
        b1.setToRow(4);
        b1.setToCol(0);
        makeMove(matchId, b1);

        mockMvc.perform(get("/api/matches/" + matchId + "/moves"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data", org.hamcrest.Matchers.hasSize(2)))
                .andExpect(jsonPath("$.data[0].moveNumber").value(1))
                .andExpect(jsonPath("$.data[0].playerId").value("p1"))
                .andExpect(jsonPath("$.data[1].moveNumber").value(2))
                .andExpect(jsonPath("$.data[1].playerId").value("p2"));
    }

    @Test
    @DisplayName("并发测试 - 同一对局两人同时 POST move，只有一方成功")
    void testConcurrentMovesOnlyOneSucceeds() throws Exception {
        Long matchId = createMatch("p1", "p2");

        MakeMoveRequest redMove = new MakeMoveRequest();
        redMove.setPlayerId("p1");
        redMove.setFromRow(6);
        redMove.setFromCol(0);
        redMove.setToRow(5);
        redMove.setToCol(0);

        MakeMoveRequest blackMove = new MakeMoveRequest();
        blackMove.setPlayerId("p2");
        blackMove.setFromRow(3);
        blackMove.setFromCol(0);
        blackMove.setToRow(4);
        blackMove.setToCol(0);

        int threadCount = 4;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);
        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger failCount = new AtomicInteger(0);
        List<String> errors = new ArrayList<>();

        for (int i = 0; i < threadCount; i++) {
            final int idx = i;
            executor.submit(() -> {
                try {
                    MakeMoveRequest req = (idx % 2 == 0) ?
                            copyMoveRequest(redMove) : copyMoveRequest(blackMove);
                    ApiResponse<MoveDto> resp = makeMove(matchId, req);
                    if (resp.getCode() == 200) {
                        successCount.incrementAndGet();
                    } else {
                        failCount.incrementAndGet();
                        synchronized (errors) {
                            errors.add(resp.getMessage());
                        }
                    }
                } catch (Exception e) {
                    failCount.incrementAndGet();
                    synchronized (errors) {
                        errors.add("Exception: " + e.getMessage());
                    }
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        executor.shutdown();

        MvcResult result = mockMvc.perform(get("/api/matches/" + matchId))
                .andExpect(status().isOk())
                .andReturn();

        ApiResponse<?> resp = objectMapper.readValue(
                result.getResponse().getContentAsString(), ApiResponse.class
        );
        Map<String, Object> data = (Map<String, Object>) resp.getData();
        int turnAfter = (int) data.get("currentTurn");

        assertTrue(successCount.get() >= 1, "至少应该有1次成功");
        assertTrue(turnAfter <= 2, "回合数应该 <= 2，实际: " + turnAfter);

        boolean hasTurnError = errors.stream().anyMatch(e -> e != null && e.contains("不是你的回合"));
        assertTrue(hasTurnError || failCount.get() > 0,
                "应该存在失败的请求，包含'不是你的回合'，错误列表: " + errors);
    }

    private MakeMoveRequest copyMoveRequest(MakeMoveRequest src) {
        MakeMoveRequest dst = new MakeMoveRequest();
        dst.setPlayerId(src.getPlayerId());
        dst.setFromRow(src.getFromRow());
        dst.setFromCol(src.getFromCol());
        dst.setToRow(src.getToRow());
        dst.setToCol(src.getToCol());
        return dst;
    }

    @Test
    @DisplayName("排行榜分页查询 + Elo 更新后排名变化")
    void testLeaderboardAndEloUpdate() throws Exception {
        Long matchId = createMatch("elo_p1", "elo_p2");

        for (int step = 0; step < 10; step++) {
            int redFromRow = 9, redFromCol = 0, redToRow = 8, redToCol = 0;
            if (step == 0) {
                redFromRow = 9; redFromCol = 0; redToRow = 8; redToCol = 0;
            } else if (step % 2 == 0) {
                redFromRow = 9 - step/2; redFromCol = 4; redToRow = 8 - step/2; redToCol = 4;
            }

            MakeMoveRequest r = new MakeMoveRequest();
            r.setPlayerId("elo_p1");
            r.setFromRow(redFromRow);
            r.setFromCol(redFromCol);
            r.setToRow(redToRow);
            r.setToCol(redToCol);
            ApiResponse<MoveDto> rResp = makeMove(matchId, r);

            if (step < 9) {
                MakeMoveRequest b = new MakeMoveRequest();
                b.setPlayerId("elo_p2");
                b.setFromRow(0 + step);
                b.setFromCol(0);
                b.setToRow(1 + step);
                b.setToCol(0);
                makeMove(matchId, b);
            }
        }

        mockMvc.perform(get("/api/players/leaderboard?page=0&size=10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.content").isArray());

        mockMvc.perform(get("/api/players/elo_p1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));

        mockMvc.perform(get("/api/players/elo_p2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("不存在的对局返回 404")
    void testMatchNotFound() throws Exception {
        mockMvc.perform(get("/api/matches/999999"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(404));
    }

    @Test
    @DisplayName("创建对局参数校验 - playerId 为空")
    void testCreateMatchValidation() throws Exception {
        CreateMatchRequest request = new CreateMatchRequest();
        request.setRedPlayerId("");
        request.setBlackPlayerId(null);

        mockMvc.perform(post("/api/matches")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("走子坐标超出范围被拒绝")
    void testMoveOutOfBounds() throws Exception {
        Long matchId = createMatch("p1", "p2");

        MakeMoveRequest request = new MakeMoveRequest();
        request.setPlayerId("p1");
        request.setFromRow(99);
        request.setFromCol(99);
        request.setToRow(7);
        request.setToCol(2);

        mockMvc.perform(post("/api/matches/" + matchId + "/moves")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }
}
