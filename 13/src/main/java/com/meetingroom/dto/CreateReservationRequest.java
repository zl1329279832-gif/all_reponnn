package com.meetingroom.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class CreateReservationRequest {

    @NotNull(message = "会议室ID不能为空")
    private Long roomId;

    @NotBlank(message = "员工ID不能为空")
    private String employeeId;

    @NotBlank(message = "员工姓名不能为空")
    private String employeeName;

    @NotBlank(message = "会议主题不能为空")
    private String title;

    @NotNull(message = "开始时间不能为空")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime startTime;

    @NotNull(message = "结束时间不能为空")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime endTime;

    private boolean recurring = false;

    private String recurringType = "WEEKLY";
}
