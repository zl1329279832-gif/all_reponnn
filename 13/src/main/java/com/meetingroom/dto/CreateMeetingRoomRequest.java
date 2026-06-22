package com.meetingroom.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class CreateMeetingRoomRequest {

    @NotBlank(message = "会议室名称不能为空")
    private String name;

    @NotNull(message = "楼层不能为空")
    private Integer floor;

    @NotNull(message = "容量不能为空")
    @Min(value = 1, message = "容量至少为1")
    private Integer capacity;

    private List<String> equipment;

    @NotEmpty(message = "可预约时段不能为空")
    private List<TimeSlotDTO> availableSlots;
}
