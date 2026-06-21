package com.chess.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateMatchRequest {

    @NotBlank(message = "红方 playerId 不能为空")
    private String redPlayerId;

    @NotBlank(message = "黑方 playerId 不能为空")
    private String blackPlayerId;

    private String redPlayerName;

    private String blackPlayerName;

    @Min(value = 1, message = "baseSeconds 必须大于 0")
    private Integer baseSeconds;
}
