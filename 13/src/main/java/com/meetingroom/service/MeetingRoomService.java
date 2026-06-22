package com.meetingroom.service;

import com.meetingroom.dto.CreateMeetingRoomRequest;
import com.meetingroom.dto.MeetingRoomResponse;
import com.meetingroom.dto.TimeSlotDTO;
import com.meetingroom.dto.UpdateMeetingRoomRequest;
import com.meetingroom.entity.MeetingRoom;
import com.meetingroom.entity.TimeSlot;
import com.meetingroom.exception.BusinessException;
import com.meetingroom.repository.MeetingRoomRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class MeetingRoomService {

    private final MeetingRoomRepository meetingRoomRepository;

    @Transactional(readOnly = true)
    public List<MeetingRoomResponse> findAll() {
        return meetingRoomRepository.findAll().stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<MeetingRoomResponse> findByFilters(Integer floor, Integer minCapacity) {
        List<MeetingRoom> rooms;
        if (floor != null && minCapacity != null) {
            rooms = meetingRoomRepository.findByFloorAndCapacity(floor, minCapacity);
        } else if (floor != null) {
            rooms = meetingRoomRepository.findByFloor(floor);
        } else if (minCapacity != null) {
            rooms = meetingRoomRepository.findByCapacityGreaterThanEqual(minCapacity);
        } else {
            rooms = meetingRoomRepository.findAll();
        }
        return rooms.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public MeetingRoomResponse findById(Long id) {
        MeetingRoom room = meetingRoomRepository.findById(id)
                .orElseThrow(() -> BusinessException.notFound("会议室不存在，ID: " + id));
        return toResponse(room);
    }

    @Transactional(readOnly = true)
    public MeetingRoom getRoomEntity(Long id) {
        return meetingRoomRepository.findById(id)
                .orElseThrow(() -> BusinessException.notFound("会议室不存在，ID: " + id));
    }

    @Transactional
    public MeetingRoomResponse create(CreateMeetingRoomRequest request) {
        if (meetingRoomRepository.findAll().stream()
                .anyMatch(r -> r.getName().equals(request.getName()))) {
            throw BusinessException.conflict("会议室名称已存在: " + request.getName());
        }
        validateTimeSlots(request.getAvailableSlots());

        MeetingRoom room = new MeetingRoom();
        room.setName(request.getName());
        room.setFloor(request.getFloor());
        room.setCapacity(request.getCapacity());
        room.setEquipment(request.getEquipment() != null ? request.getEquipment() : List.of());
        room.setAvailableSlots(request.getAvailableSlots().stream()
                .map(slot -> new TimeSlot(slot.getStart(), slot.getEnd()))
                .collect(Collectors.toList()));

        MeetingRoom saved = meetingRoomRepository.save(room);
        return toResponse(saved);
    }

    @Transactional
    public MeetingRoomResponse update(Long id, UpdateMeetingRoomRequest request) {
        MeetingRoom room = meetingRoomRepository.findById(id)
                .orElseThrow(() -> BusinessException.notFound("会议室不存在，ID: " + id));

        if (request.getName() != null && !request.getName().equals(room.getName())) {
            if (meetingRoomRepository.findAll().stream()
                    .anyMatch(r -> r.getName().equals(request.getName()) && !r.getId().equals(id))) {
                throw BusinessException.conflict("会议室名称已存在: " + request.getName());
            }
            room.setName(request.getName());
        }

        if (request.getFloor() != null) {
            room.setFloor(request.getFloor());
        }
        if (request.getCapacity() != null) {
            room.setCapacity(request.getCapacity());
        }
        if (request.getEquipment() != null) {
            room.setEquipment(request.getEquipment());
        }
        if (request.getAvailableSlots() != null && !request.getAvailableSlots().isEmpty()) {
            validateTimeSlots(request.getAvailableSlots());
            room.setAvailableSlots(request.getAvailableSlots().stream()
                    .map(slot -> new TimeSlot(slot.getStart(), slot.getEnd()))
                    .collect(Collectors.toList()));
        }

        MeetingRoom saved = meetingRoomRepository.save(room);
        return toResponse(saved);
    }

    @Transactional
    public void delete(Long id) {
        if (!meetingRoomRepository.existsById(id)) {
            throw BusinessException.notFound("会议室不存在，ID: " + id);
        }
        meetingRoomRepository.deleteById(id);
    }

    private void validateTimeSlots(List<TimeSlotDTO> slots) {
        for (TimeSlotDTO slot : slots) {
            if (!isValidTimeFormat(slot.getStart()) || !isValidTimeFormat(slot.getEnd())) {
                throw BusinessException.badRequest("时间格式不正确，应为 HH:mm: " + slot.getStart() + " - " + slot.getEnd());
            }
            if (slot.getStart().compareTo(slot.getEnd()) >= 0) {
                throw BusinessException.badRequest("开始时间必须早于结束时间: " + slot.getStart() + " - " + slot.getEnd());
            }
        }
    }

    private boolean isValidTimeFormat(String time) {
        return time != null && time.matches("^([01]?[0-9]|2[0-3]):[0-5][0-9]$");
    }

    private MeetingRoomResponse toResponse(MeetingRoom room) {
        List<TimeSlotDTO> slots = room.getAvailableSlots().stream()
                .map(slot -> {
                    TimeSlotDTO dto = new TimeSlotDTO();
                    dto.setStart(slot.getStart());
                    dto.setEnd(slot.getEnd());
                    return dto;
                })
                .collect(Collectors.toList());

        return new MeetingRoomResponse(
                room.getId(),
                room.getName(),
                room.getFloor(),
                room.getCapacity(),
                room.getEquipment(),
                slots,
                room.getCreatedAt(),
                room.getUpdatedAt()
        );
    }
}
