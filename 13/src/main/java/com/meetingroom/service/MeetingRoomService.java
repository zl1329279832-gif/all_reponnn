package com.meetingroom.service;

import com.meetingroom.dto.CreateMeetingRoomRequest;
import com.meetingroom.dto.MeetingRoomResponse;
import com.meetingroom.dto.TimeSlotDTO;
import com.meetingroom.dto.UpdateMeetingRoomRequest;
import com.meetingroom.entity.MeetingRoom;
import com.meetingroom.entity.TimeSlot;
import com.meetingroom.exception.BusinessException;
import com.meetingroom.repository.MeetingRoomRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.TypedQuery;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class MeetingRoomService {

    private final MeetingRoomRepository meetingRoomRepository;

    @PersistenceContext
    private EntityManager entityManager;

    @Transactional(readOnly = true)
    public List<MeetingRoomResponse> findAll() {
        try {
            List<MeetingRoom> rooms = meetingRoomRepository.findAll();
            return rooms.stream().map(this::toResponse).collect(Collectors.toList());
        } catch (DataAccessException e) {
            throw BusinessException.badRequest("查询会议室失败: " + e.getMessage());
        }
    }

    @Transactional(readOnly = true)
    public List<MeetingRoomResponse> findByFilters(Integer floor, Integer minCapacity) {
        try {
            StringBuilder jpql = new StringBuilder("SELECT r FROM MeetingRoom r WHERE 1=1");
            if (floor != null) {
                jpql.append(" AND r.floor = :floor");
            }
            if (minCapacity != null) {
                jpql.append(" AND r.capacity >= :minCapacity");
            }

            TypedQuery<MeetingRoom> query = entityManager.createQuery(jpql.toString(), MeetingRoom.class);
            if (floor != null) {
                query.setParameter("floor", floor);
            }
            if (minCapacity != null) {
                query.setParameter("minCapacity", minCapacity);
            }

            return query.getResultList().stream()
                    .map(this::toResponse)
                    .collect(Collectors.toList());
        } catch (DataAccessException e) {
            throw BusinessException.badRequest("查询会议室失败: " + e.getMessage());
        }
    }

    @Transactional(readOnly = true)
    public MeetingRoomResponse findById(Long id) {
        try {
            MeetingRoom room = meetingRoomRepository.findById(id)
                    .orElseThrow(() -> BusinessException.notFound("会议室不存在，ID: " + id));
            return toResponse(room);
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            throw BusinessException.badRequest("查询会议室失败: " + e.getMessage());
        }
    }

    @Transactional(readOnly = true)
    public MeetingRoom getRoomEntity(Long id) {
        try {
            return meetingRoomRepository.findById(id)
                    .orElseThrow(() -> BusinessException.notFound("会议室不存在，ID: " + id));
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            throw BusinessException.badRequest("查询会议室失败: " + e.getMessage());
        }
    }

    @Transactional
    public MeetingRoomResponse create(CreateMeetingRoomRequest request) {
        try {
            boolean exists = entityManager.createQuery(
                            "SELECT COUNT(r) FROM MeetingRoom r WHERE r.name = :name", Long.class)
                    .setParameter("name", request.getName())
                    .getSingleResult() > 0;
            if (exists) {
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
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            throw BusinessException.badRequest("创建会议室失败: " + e.getMessage());
        }
    }

    @Transactional
    public MeetingRoomResponse update(Long id, UpdateMeetingRoomRequest request) {
        try {
            MeetingRoom room = meetingRoomRepository.findById(id)
                    .orElseThrow(() -> BusinessException.notFound("会议室不存在，ID: " + id));

            if (request.getName() != null && !request.getName().equals(room.getName())) {
                long count = entityManager.createQuery(
                                "SELECT COUNT(r) FROM MeetingRoom r WHERE r.name = :name AND r.id <> :id", Long.class)
                        .setParameter("name", request.getName())
                        .setParameter("id", id)
                        .getSingleResult();
                if (count > 0) {
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
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            throw BusinessException.badRequest("更新会议室失败: " + e.getMessage());
        }
    }

    @Transactional
    public void delete(Long id) {
        try {
            if (!meetingRoomRepository.existsById(id)) {
                throw BusinessException.notFound("会议室不存在，ID: " + id);
            }
            meetingRoomRepository.deleteById(id);
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            throw BusinessException.badRequest("删除会议室失败: " + e.getMessage());
        }
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
