package com.meetingroom.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class MeetingRoomResponse {

    private Long id;
    private String name;
    private Integer floor;
    private Integer capacity;
    private List<String> equipment;
    private List<TimeSlotDTO> availableSlots;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
