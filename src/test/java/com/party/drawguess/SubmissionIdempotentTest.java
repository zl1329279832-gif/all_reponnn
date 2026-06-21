package com.party.drawguess;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class SubmissionIdempotentTest extends AbstractIntegrationTest {

    @Test
    @DisplayName("Duplicate description submission returns 409")
    void duplicateDescriptionReturns409() throws Exception {
        Long p1 = registerPlayer("idem_p1", "DescOwner");
        Long p2 = registerPlayer("idem_p2", "DescGuest");

        String roomJson = postJson("/api/rooms/create", Map.of(
                "roomName", "IdemRoom", "password", "",
                "maxPlayers", 4, "totalRounds", 3, "ownerId", p1));
        Long roomId = extractDataId(roomJson);
        String roomCode = (String) extractData(roomJson).get("roomCode");

        postJson("/api/rooms/join", Map.of("roomCode", roomCode, "password", "", "playerId", p2));
        postJson("/api/rooms/ready", Map.of("playerId", p2, "roomId", roomId));
        String startJson = postJson("/api/rooms/start", Map.of("roomId", roomId, "ownerId", p1));
        Long gameId = ((Number) extractData(startJson).get("currentGameId")).longValue();

        String desc1 = postJson("/api/games/submit-description", Map.of(
                "gameId", gameId, "roundNumber", 1, "playerId", p1,
                "targetWord", "moon", "description", "night sky object"));
        assertEquals(200, extractCode(desc1));

        String desc2 = postJson("/api/games/submit-description", Map.of(
                "gameId", gameId, "roundNumber", 1, "playerId", p1,
                "targetWord", "moon", "description", "night sky object again"));
        assertEquals(409, extractCode(desc2));
    }

    @Test
    @DisplayName("Duplicate guess submission returns 409")
    void duplicateGuessReturns409() throws Exception {
        Long p1 = registerPlayer("idem_g_p1", "GuessOwner");
        Long p2 = registerPlayer("idem_g_p2", "GuessGuest");

        String roomJson = postJson("/api/rooms/create", Map.of(
                "roomName", "IdemGuessRoom", "password", "",
                "maxPlayers", 4, "totalRounds", 3, "ownerId", p1));
        Long roomId = extractDataId(roomJson);
        String roomCode = (String) extractData(roomJson).get("roomCode");

        postJson("/api/rooms/join", Map.of("roomCode", roomCode, "password", "", "playerId", p2));
        postJson("/api/rooms/ready", Map.of("playerId", p2, "roomId", roomId));
        String startJson = postJson("/api/rooms/start", Map.of("roomId", roomId, "ownerId", p1));
        Long gameId = ((Number) extractData(startJson).get("currentGameId")).longValue();

        postJson("/api/games/submit-description", Map.of(
                "gameId", gameId, "roundNumber", 1, "playerId", p1,
                "targetWord", "star", "description", "twinkles at night"));

        String guess1 = postJson("/api/games/submit-guess", Map.of(
                "gameId", gameId, "roundNumber", 1, "playerId", p2, "guess", "star"));
        assertEquals(200, extractCode(guess1));

        String guess2 = postJson("/api/games/submit-guess", Map.of(
                "gameId", gameId, "roundNumber", 1, "playerId", p2, "guess", "star"));
        assertEquals(409, extractCode(guess2));
    }

    @Test
    @DisplayName("Wrong guess does not score, but submits successfully (200)")
    void wrongGuessSubmitsButNoScore() throws Exception {
        Long p1 = registerPlayer("wrong_p1", "WrongOwner");
        Long p2 = registerPlayer("wrong_p2", "WrongGuest");

        String roomJson = postJson("/api/rooms/create", Map.of(
                "roomName", "WrongRoom", "password", "",
                "maxPlayers", 4, "totalRounds", 3, "ownerId", p1));
        Long roomId = extractDataId(roomJson);
        String roomCode = (String) extractData(roomJson).get("roomCode");

        postJson("/api/rooms/join", Map.of("roomCode", roomCode, "password", "", "playerId", p2));
        postJson("/api/rooms/ready", Map.of("playerId", p2, "roomId", roomId));
        String startJson = postJson("/api/rooms/start", Map.of("roomId", roomId, "ownerId", p1));
        Long gameId = ((Number) extractData(startJson).get("currentGameId")).longValue();

        postJson("/api/games/submit-description", Map.of(
                "gameId", gameId, "roundNumber", 1, "playerId", p1,
                "targetWord", "elephant", "description", "big animal trunk"));

        String guessResp = postJson("/api/games/submit-guess", Map.of(
                "gameId", gameId, "roundNumber", 1, "playerId", p2, "guess", "mouse"));
        assertEquals(200, extractCode(guessResp));

        Map<String, Object> data = extractData(guessResp);
        Map<String, Object> scores = (Map<String, Object>) data.get("currentScores");
        int p2Score = ((Number) scores.get(p2.toString())).intValue();
        assertEquals(0, p2Score, "Wrong guess should earn 0 points");
    }
}
