package com.party.drawguess.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class GameHistoryResponse {
    private Long gameId;
    private String roomCode;
    private String roomName;
    private Integer totalRounds;
    private Integer completedRounds;
    private Long winnerId;
    private String winnerNickname;
    private Map<Long, Integer> scores;
    private Map<Long, String> playerNicknames;
    private LocalDateTime startedAt;
    private LocalDateTime endedAt;
    private List<RoundDetailResponse> rounds;
}
