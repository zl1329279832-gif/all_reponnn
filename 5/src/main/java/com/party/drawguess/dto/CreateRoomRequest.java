package com.party.drawguess.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class CreateRoomRequest {
    @NotBlank(message = "房间名不能为空")
    @Size(max = 100, message = "房间名长度不能超过 100")
    private String roomName;

    @Size(max = 50, message = "密码长度不能超过 50")
    private String password;

    @Min(value = 2, message = "最少 2 人")
    @Max(value = 8, message = "最多 8 人")
    private Integer maxPlayers = 4;

    @Min(value = 1, message = "最少 1 轮")
    @Max(value = 20, message = "最多 20 轮")
    private Integer totalRounds = 5;

    private Long ownerId;
}
