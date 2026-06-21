package com.party.drawguess.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class JoinRoomRequest {
    @NotBlank(message = "房间码不能为空")
    private String roomCode;

    private String password;

    @NotNull(message = "玩家 ID 不能为空")
    private Long playerId;
}
