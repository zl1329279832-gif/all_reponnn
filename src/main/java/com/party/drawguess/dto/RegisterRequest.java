package com.party.drawguess.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class RegisterRequest {
    @NotBlank(message = "openId 不能为空")
    @Size(max = 50, message = "openId 长度不能超过 50")
    private String openId;

    @NotBlank(message = "昵称不能为空")
    @Size(max = 50, message = "昵称长度不能超过 50")
    private String nickname;
}
