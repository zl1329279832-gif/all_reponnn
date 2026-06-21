package com.chess.dto;

import com.chess.entity.Match;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MatchDto {
    private Long id;
    private String redPlayerId;
    private String redPlayerName;
    private String blackPlayerId;
    private String blackPlayerName;
    private Match.MatchStatus status;
    private Integer currentTurn;
    private String nextTurnPlayerId;
    private LocalDateTime createdAt;
    private LocalDateTime endedAt;
    private String winnerPlayerId;
    private String fen;
    private List<String> boardDisplay;
    private Integer baseSeconds;
    private Integer redTimeLeft;
    private Integer blackTimeLeft;
}
