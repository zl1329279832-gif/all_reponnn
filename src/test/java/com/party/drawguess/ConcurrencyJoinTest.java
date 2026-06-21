package com.party.drawguess;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

class ConcurrencyJoinTest extends AbstractIntegrationTest {

    @Test
    @DisplayName("6 players rush 4-seat room: at most 3 succeed (owner + 3), rest get 409")
    void sixPlayersRushFourSeatRoom() throws Exception {
        Long owner = registerPlayer("conc_owner", "ConcOwner");

        String roomJson = postJson("/api/rooms/create", Map.of(
                "roomName", "ConcRoom", "password", "",
                "maxPlayers", 4, "totalRounds", 3, "ownerId", owner));
        Long roomId = extractDataId(roomJson);
        String roomCode = (String) extractData(roomJson).get("roomCode");

        List<Long> rushers = new ArrayList<>();
        for (int i = 1; i <= 6; i++) {
            rushers.add(registerPlayer("conc_rush_" + i, "Rusher" + i));
        }

        ExecutorService executor = Executors.newFixedThreadPool(6);
        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger rejectCount = new AtomicInteger(0);
        List<Future<?>> futures = new ArrayList<>();

        for (Long pid : rushers) {
            futures.add(executor.submit(() -> {
                try {
                    String resp = postJson("/api/rooms/join",
                            Map.of("roomCode", roomCode, "password", "", "playerId", pid));
                    int code = extractCode(resp);
                    if (code == 200) {
                        successCount.incrementAndGet();
                    } else if (code == 409) {
                        rejectCount.incrementAndGet();
                    }
                } catch (Exception e) {
                    // unexpected
                }
            }));
        }

        for (Future<?> f : futures) {
            f.get(10, TimeUnit.SECONDS);
        }
        executor.shutdown();

        String snapJson = getJson("/api/rooms/" + roomId + "/snapshot");
        Map<String, Object> snapData = extractData(snapJson);
        int playerCount = ((List<?>) snapData.get("players")).size();

        assertTrue(playerCount <= 4,
                "Room must not exceed maxPlayers=4, but was " + playerCount);
        assertEquals(6, successCount.get() + rejectCount.get(),
                "All 6 requests must get a definitive response");
    }

    @Test
    @DisplayName("Same playerId joins concurrently: only 1 success, rest 409 duplicate")
    void samePlayerIdConcurrentDuplicateJoin() throws Exception {
        Long owner = registerPlayer("dup_owner", "DupOwner");
        Long target = registerPlayer("dup_same_id", "SameIdPlayer");

        String roomJson = postJson("/api/rooms/create", Map.of(
                "roomName", "DupRoom", "password", "",
                "maxPlayers", 6, "totalRounds", 2, "ownerId", owner));
        Long roomId = extractDataId(roomJson);
        String roomCode = (String) extractData(roomJson).get("roomCode");

        int parallelCount = 8;
        ExecutorService executor = Executors.newFixedThreadPool(parallelCount);
        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger rejectCount = new AtomicInteger(0);
        List<Future<?>> futures = new ArrayList<>();

        for (int i = 0; i < parallelCount; i++) {
            futures.add(executor.submit(() -> {
                try {
                    String resp = postJson("/api/rooms/join",
                            Map.of("roomCode", roomCode, "password", "", "playerId", target));
                    int code = extractCode(resp);
                    if (code == 200) {
                        successCount.incrementAndGet();
                    } else if (code == 409) {
                        rejectCount.incrementAndGet();
                    }
                } catch (Exception e) {
                    // unexpected
                }
            }));
        }

        for (Future<?> f : futures) {
            f.get(10, TimeUnit.SECONDS);
        }
        executor.shutdown();

        String snapJson = getJson("/api/rooms/" + roomId + "/snapshot");
        Map<String, Object> snapData = extractData(snapJson);
        List<?> players = (List<?>) snapData.get("players");

        long appearances = players.stream()
                .filter(p -> {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> pm = (Map<String, Object>) p;
                    return target.equals(((Number) pm.get("id")).longValue());
                }).count();

        assertEquals(1, appearances, "Player should appear exactly once in room");
        assertEquals(1, successCount.get(), "Exactly 1 join should succeed");
        assertEquals(parallelCount - 1, rejectCount.get(),
                "All other attempts should be rejected");
    }
}
