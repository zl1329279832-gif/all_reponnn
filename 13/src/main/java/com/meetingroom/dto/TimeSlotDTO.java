package com.meetingroom.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class TimeSlotDTO {

    @NotBlank(message = "开始时间不能为空")
    private String start;

    @NotBlank(message = "结束时间不能为空")
    private String end;
}
