package com.party.drawguess.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class SubmitDescriptionRequest {
    @NotNull(message = "游戏 ID 不能为空")
    private Long gameId;

    @NotNull(message = "轮次号不能为空")
    private Integer roundNumber;

    @NotNull(message = "玩家 ID 不能为空")
    private Long playerId;

    @NotBlank(message = "目标词不能为空")
    @Size(max = 100, message = "目标词长度不能超过 100")
    private String targetWord;

    @NotBlank(message = "描述不能为空")
    @Size(max = 500, message = "描述长度不能超过 500")
    private String description;
}
