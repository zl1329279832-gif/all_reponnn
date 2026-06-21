package com.chess.dto;

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
}
