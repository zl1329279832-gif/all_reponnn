package com.party.drawguess.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ReadyRequest {
    @NotNull(message = "玩家 ID 不能为空")
    private Long playerId;

    @NotNull(message = "房间 ID 不能为空")
    private Long roomId;
}
