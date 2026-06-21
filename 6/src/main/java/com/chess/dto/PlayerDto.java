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
public class PlayerDto {
    private Long id;
    private String playerId;
    private String name;
    private Integer eloRating;
    private Integer wins;
    private Integer losses;
    private Integer draws;
    private Integer rank;
    private LocalDateTime createdAt;
}
