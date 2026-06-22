package com.meetingroom.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CheckInRequest {

    @NotBlank(message = "操作人不能为空")
    private String operator;
}
