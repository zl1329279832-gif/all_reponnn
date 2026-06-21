package com.party.drawguess.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class StartGameRequest {
    @NotNull(message = "房间 ID 不能为空")
    private Long roomId;

    @NotNull(message = "房主 ID 不能为空")
    private Long ownerId;
}
