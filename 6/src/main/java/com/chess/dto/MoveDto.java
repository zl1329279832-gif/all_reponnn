package com.chess.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MoveDto {
    private Long id;
    private Long matchId;
    private Integer moveNumber;
    private String playerId;
    private String playerName;
    private Integer fromRow;
    private Integer fromCol;
    private Integer toRow;
    private Integer toCol;
    private String pieceType;
    private String pieceDisplayName;
    private String capturedPieceType;
    private String capturedPieceDisplayName;
    private LocalDateTime createdAt;
}
