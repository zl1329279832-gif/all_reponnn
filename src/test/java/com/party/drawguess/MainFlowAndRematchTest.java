package com.party.drawguess;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class MainFlowAndRematchTest extends AbstractIntegrationTest {

    @Test
    @DisplayName("Full game flow: register -> create -> join -> ready -> start -> 2 rounds -> FINISHED -> rematch -> play again")
    void fullGameFlowWithRematch() throws Exception {
        Long p1 = registerPlayer("flow_p1", "Alice");
        Long p2 = registerPlayer("flow_p2", "Bob");

        String roomJson = postJson("/api/rooms/create", Map.of(
                "roomName", "TestRoom", "password", "",
                "maxPlayers", 4, "totalRounds", 2, "ownerId", p1));
        Map<String, Object> roomData = extractData(roomJson);
        Long roomId = ((Number) roomData.get("roomId")).longValue();
        String roomCode = (String) roomData.get("roomCode");

        postJson("/api/rooms/join", Map.of(
                "roomCode", roomCode, "password", "", "playerId", p2));

        postJson("/api/rooms/ready", Map.of("playerId", p2, "roomId", roomId));

        String startJson = postJson("/api/rooms/start", Map.of("roomId", roomId, "ownerId", p1));
        Map<String, Object> startData = extractData(startJson);
        Long gameId1 = ((Number) startData.get("currentGameId")).longValue();

        postJson("/api/games/submit-description", Map.of(
                "gameId", gameId1, "roundNumber", 1, "playerId", p1,
                "targetWord", "apple", "description", "red fruit"));
        String g1r1 = postJson("/api/games/submit-guess", Map.of(
                "gameId", gameId1, "roundNumber", 1, "playerId", p2, "guess", "apple"));
        Map<String, Object> g1r1Data = extractData(g1r1);
        Map<String, Object> scores1 = (Map<String, Object>) g1r1Data.get("currentScores");
        assert ((Number) scores1.get(p1.toString())).intValue() == 5;
        assert ((Number) scores1.get(p2.toString())).intValue() == 10;

        postJson("/api/games/submit-description", Map.of(
                "gameId", gameId1, "roundNumber", 2, "playerId", p2,
                "targetWord", "banana", "description", "yellow fruit"));
        String g1r2 = postJson("/api/games/submit-guess", Map.of(
                "gameId", gameId1, "roundNumber", 2, "playerId", p1, "guess", "banana"));

        Map<String, Object> g1r2Data = extractData(g1r2);
        assert "FINISHED".equals(g1r2Data.get("status"));

        String badRematch = postJson("/api/rooms/rematch", Map.of("roomId", roomId, "ownerId", p2));
        assert extractCode(badRematch) == 403;

        String rematchJson = postJson("/api/rooms/rematch", Map.of("roomId", roomId, "ownerId", p1));
        Map<String, Object> rematchData = extractData(rematchJson);
        Long gameId2 = ((Number) rematchData.get("currentGameId")).longValue();
        assert !gameId1.equals(gameId2) : "rematch should create new game";
        assert "PLAYING".equals(rematchData.get("status"));

        Map<String, Object> scores2 = (Map<String, Object>) rematchData.get("currentScores");
        assert ((Number) scores2.get(p1.toString())).intValue() == 0;
        assert ((Number) scores2.get(p2.toString())).intValue() == 0;

        postJson("/api/games/submit-description", Map.of(
                "gameId", gameId2, "roundNumber", 1, "playerId", p1,
                "targetWord", "cat", "description", "meows"));
        String g2r1 = postJson("/api/games/submit-guess", Map.of(
                "gameId", gameId2, "roundNumber", 1, "playerId", p2, "guess", "cat"));
        Map<String, Object> g2r1Data = extractData(g2r1);
        Map<String, Object> scores3 = (Map<String, Object>) g2r1Data.get("currentScores");
        assert ((Number) scores3.get(p1.toString())).intValue() == 5;
        assert ((Number) scores3.get(p2.toString())).intValue() == 10;

        mockMvc().perform(get("/api/games/my?playerId=" + p1 + "&page=0&size=10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.totalElements").value(greaterThanOrEqualTo(2)));
    }

    @Test
    @DisplayName("Rematch during PLAYING should be rejected")
    void rematchDuringPlayingRejected() throws Exception {
        Long p1 = registerPlayer("rematch_rej_p1", "OwnerX");
        Long p2 = registerPlayer("rematch_rej_p2", "GuestX");

        String roomJson = postJson("/api/rooms/create", Map.of(
                "roomName", "RejRoom", "password", "",
                "maxPlayers", 4, "totalRounds", 2, "ownerId", p1));
        Long roomId = extractDataId(roomJson);
        String roomCode = (String) extractData(roomJson).get("roomCode");

        postJson("/api/rooms/join", Map.of("roomCode", roomCode, "password", "", "playerId", p2));
        postJson("/api/rooms/ready", Map.of("playerId", p2, "roomId", roomId));
        postJson("/api/rooms/start", Map.of("roomId", roomId, "ownerId", p1));

        String result = postJson("/api/rooms/rematch", Map.of("roomId", roomId, "ownerId", p1));
        assert extractCode(result) != 200 : "Rematch during PLAYING should fail";
    }

    @Test
    @DisplayName("Room snapshot reflects FINISHED state with scores")
    void snapshotShowsFinishedState() throws Exception {
        Long p1 = registerPlayer("snap_p1", "SnapOwner");
        Long p2 = registerPlayer("snap_p2", "SnapGuest");

        String roomJson = postJson("/api/rooms/create", Map.of(
                "roomName", "SnapRoom", "password", "",
                "maxPlayers", 4, "totalRounds", 1, "ownerId", p1));
        Long roomId = extractDataId(roomJson);
        String roomCode = (String) extractData(roomJson).get("roomCode");

        postJson("/api/rooms/join", Map.of("roomCode", roomCode, "password", "", "playerId", p2));
        postJson("/api/rooms/ready", Map.of("playerId", p2, "roomId", roomId));
        String startJson = postJson("/api/rooms/start", Map.of("roomId", roomId, "ownerId", p1));
        Long gameId = ((Number) extractData(startJson).get("currentGameId")).longValue();

        postJson("/api/games/submit-description", Map.of(
                "gameId", gameId, "roundNumber", 1, "playerId", p1,
                "targetWord", "sun", "description", "bright sky"));
        postJson("/api/games/submit-guess", Map.of(
                "gameId", gameId, "roundNumber", 1, "playerId", p2, "guess", "sun"));

        mockMvc().perform(get("/api/rooms/" + roomId + "/snapshot"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("FINISHED"))
                .andExpect(jsonPath("$.data.players.length()").value(2))
                .andExpect(jsonPath("$.data.currentScores").isMap());
    }
}
