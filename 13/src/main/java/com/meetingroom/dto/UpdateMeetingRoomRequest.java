package com.meetingroom.dto;

import jakarta.validation.constraints.Min;
import lombok.Data;

import java.util.List;

@Data
public class UpdateMeetingRoomRequest {

    private String name;

    private Integer floor;

    @Min(value = 1, message = "容量至少为1")
    private Integer capacity;

    private List<String> equipment;

    private List<TimeSlotDTO> availableSlots;
}
