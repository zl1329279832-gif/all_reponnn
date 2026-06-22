package com.meetingroom.service;

import com.meetingroom.dto.CreateReservationRequest;
import com.meetingroom.dto.MeetingRoomResponse;
import com.meetingroom.dto.ReservationResponse;
import com.meetingroom.entity.MeetingRoom;
import com.meetingroom.entity.Reservation;
import com.meetingroom.entity.TimeSlot;
import com.meetingroom.exception.BusinessException;
import com.meetingroom.repository.ReservationRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.TypedQuery;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReservationService {

    private static final int BUFFER_MINUTES = 15;
    private static final int MAX_DURATION_HOURS = 4;
    private static final int RECURRING_WEEKS = 8;

    private final ReservationRepository reservationRepository;
    private final MeetingRoomService meetingRoomService;

    @PersistenceContext
    private EntityManager entityManager;

    @Transactional(readOnly = true)
    public List<ReservationResponse> findByFilters(Long roomId, Integer floor, Integer minCapacity,
                                                   LocalDate startDate, LocalDate endDate) {
        try {
            StringBuilder jpql = new StringBuilder("SELECT r FROM Reservation r WHERE r.cancelled = false");
            if (roomId != null) {
                jpql.append(" AND r.roomId = :roomId");
            }
            if (startDate != null) {
                jpql.append(" AND r.startTime >= :startDateTime");
            }
            if (endDate != null) {
                jpql.append(" AND r.endTime <= :endDateTime");
            }
            jpql.append(" ORDER BY r.startTime ASC");

            TypedQuery<Reservation> query = entityManager.createQuery(jpql.toString(), Reservation.class);
            if (roomId != null) {
                query.setParameter("roomId", roomId);
            }
            if (startDate != null) {
                query.setParameter("startDateTime", startDate.atStartOfDay());
            }
            if (endDate != null) {
                query.setParameter("endDateTime", endDate.atTime(23, 59, 59));
            }

            List<Reservation> reservations = query.getResultList();

            Map<Long, MeetingRoomResponse> roomInfoMap = meetingRoomService.findAll().stream()
                    .collect(Collectors.toMap(r -> r.getId(), r -> r, (a, b) -> a));

            List<ReservationResponse> responses = reservations.stream()
                    .map(r -> {
                        MeetingRoomResponse room = roomInfoMap.get(r.getRoomId());
                        String roomName = room != null ? room.getName() : "未知会议室";
                        return toResponse(r, roomName);
                    })
                    .collect(Collectors.toList());

            if (floor != null || minCapacity != null) {
                responses = responses.stream()
                        .filter(r -> {
                            MeetingRoomResponse room = roomInfoMap.get(r.getRoomId());
                            if (room == null) return false;
                            if (floor != null && !room.getFloor().equals(floor)) return false;
                            if (minCapacity != null && room.getCapacity() < minCapacity) return false;
                            return true;
                        })
                        .collect(Collectors.toList());
            }

            return responses;
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("查询预定失败", e);
            throw BusinessException.badRequest("查询预定失败: " + e.getMessage());
        }
    }

    @Transactional(readOnly = true)
    public ReservationResponse findById(Long id) {
        try {
            Reservation reservation = reservationRepository.findById(id)
                    .orElseThrow(() -> BusinessException.notFound("预定不存在，ID: " + id));

            String roomName = meetingRoomService.findById(reservation.getRoomId()).getName();
            return toResponse(reservation, roomName);
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("查询预定失败 id={}", id, e);
            throw BusinessException.badRequest("查询预定失败: " + e.getMessage());
        }
    }

    @Transactional(readOnly = true)
    public List<ReservationResponse> findBySeriesId(String seriesId) {
        try {
            List<Reservation> reservations = entityManager.createQuery(
                            "SELECT r FROM Reservation r WHERE r.seriesId = :seriesId AND r.cancelled = false ORDER BY r.startTime ASC",
                            Reservation.class)
                    .setParameter("seriesId", seriesId)
                    .getResultList();
            if (reservations.isEmpty()) {
                throw BusinessException.notFound("周期预定系列不存在，Series ID: " + seriesId);
            }

            Map<Long, String> roomNames = meetingRoomService.findAll().stream()
                    .collect(Collectors.toMap(r -> r.getId(), r -> r.getName()));

            return reservations.stream()
                    .map(r -> toResponse(r, roomNames.getOrDefault(r.getRoomId(), "未知会议室")))
                    .collect(Collectors.toList());
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("查询周期系列失败 seriesId={}", seriesId, e);
            throw BusinessException.badRequest("查询周期系列失败: " + e.getMessage());
        }
    }

    @Transactional
    public List<ReservationResponse> create(CreateReservationRequest request) {
        MeetingRoom room = meetingRoomService.getRoomEntity(request.getRoomId());
        validateBusinessRules(request, room);

        if (request.isRecurring()) {
            return createRecurringReservations(request, room);
        } else {
            return createSingleReservation(request, room);
        }
    }

    @Transactional
    public void cancelSingle(Long id) {
        try {
            Reservation reservation = reservationRepository.findById(id)
                    .orElseThrow(() -> BusinessException.notFound("预定不存在，ID: " + id));

            if (reservation.getCancelled()) {
                throw BusinessException.conflict("该预定已被取消");
            }

            reservation.setCancelled(true);
            reservationRepository.save(reservation);
            log.info("已取消单天预定 ID: {}, 系列 ID: {}", id, reservation.getSeriesId());
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("取消预定失败 id={}", id, e);
            throw BusinessException.badRequest("取消预定失败: " + e.getMessage());
        }
    }

    @Transactional
    public void cancelSeries(String seriesId) {
        try {
            List<Reservation> reservations = entityManager.createQuery(
                            "SELECT r FROM Reservation r WHERE r.seriesId = :seriesId AND r.cancelled = false",
                            Reservation.class)
                    .setParameter("seriesId", seriesId)
                    .getResultList();
            if (reservations.isEmpty()) {
                throw BusinessException.notFound("周期预定系列不存在，Series ID: " + seriesId);
            }

            for (Reservation reservation : reservations) {
                reservation.setCancelled(true);
                reservationRepository.save(reservation);
            }
            log.info("已取消整个周期预定系列，Series ID: {}, 共 {} 个实例", seriesId, reservations.size());
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("取消周期系列失败 seriesId={}", seriesId, e);
            throw BusinessException.badRequest("取消周期系列失败: " + e.getMessage());
        }
    }

    private List<ReservationResponse> createSingleReservation(CreateReservationRequest request, MeetingRoom room) {
        try {
            checkConflict(request.getRoomId(), request.getStartTime(), request.getEndTime(), null);

            Reservation reservation = buildReservation(request, null, request.getStartTime(), request.getEndTime());
            Reservation saved = reservationRepository.save(reservation);

            log.info("创建单次预定成功，ID: {}, 会议室: {}, 时间: {} - {}",
                    saved.getId(), room.getName(), saved.getStartTime(), saved.getEndTime());

            return List.of(toResponse(saved, room.getName()));
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("创建单次预定失败", e);
            throw BusinessException.badRequest("创建预定失败: " + e.getMessage());
        }
    }

    private List<ReservationResponse> createRecurringReservations(CreateReservationRequest request, MeetingRoom room) {
        String seriesId = UUID.randomUUID().toString();
        String recurringType = request.getRecurringType() != null ? request.getRecurringType() : "WEEKLY";

        List<Reservation> createdReservations = new ArrayList<>();
        List<String> conflicts = new ArrayList<>();

        for (int week = 0; week < RECURRING_WEEKS; week++) {
            LocalDateTime newStart = request.getStartTime().plusWeeks(week);
            LocalDateTime newEnd = request.getEndTime().plusWeeks(week);

            CreateReservationRequest weeklyRequest = new CreateReservationRequest();
            weeklyRequest.setStartTime(newStart);
            weeklyRequest.setEndTime(newEnd);

            try {
                validateBusinessRules(weeklyRequest, room);
                checkConflict(request.getRoomId(), newStart, newEnd, null);

                Reservation reservation = buildReservation(request, seriesId, newStart, newEnd);
                reservation.setRecurringType(recurringType);
                createdReservations.add(reservation);
            } catch (BusinessException e) {
                conflicts.add(String.format("第 %d 周 (%s - %s): %s",
                        week + 1, newStart.toLocalDate(), newEnd.toLocalDate(), e.getMessage()));
            }
        }

        if (createdReservations.isEmpty()) {
            throw BusinessException.conflict("无法创建周期预定，所有日期都存在冲突或不符合规则: " + String.join("; ", conflicts));
        }

        try {
            List<Reservation> saved = reservationRepository.saveAll(createdReservations);

            log.info("创建周期预定成功，Series ID: {}, 成功创建 {} 个实例，跳过 {} 个（{}）",
                    seriesId, saved.size(), conflicts.size(),
                    conflicts.isEmpty() ? "无冲突" : String.join("; ", conflicts));

            return saved.stream()
                    .map(r -> toResponse(r, room.getName()))
                    .collect(Collectors.toList());
        } catch (DataAccessException e) {
            log.error("批量保存周期预定失败 seriesId={}", seriesId, e);
            throw BusinessException.badRequest("创建周期预定失败: " + e.getMessage());
        }
    }

    private void validateBusinessRules(CreateReservationRequest request, MeetingRoom room) {
        LocalDateTime startTime = request.getStartTime();
        LocalDateTime endTime = request.getEndTime();

        if (startTime.isAfter(endTime) || startTime.isEqual(endTime)) {
            throw BusinessException.badRequest("开始时间必须早于结束时间");
        }

        if (startTime.isBefore(LocalDateTime.now())) {
            throw BusinessException.badRequest("预定时间不能早于当前时间");
        }

        Duration duration = Duration.between(startTime, endTime);
        long minutes = duration.toMinutes();
        if (minutes > MAX_DURATION_HOURS * 60L) {
            throw BusinessException.badRequest(
                    String.format("单次预定最长不超过 %d 小时，当前时长: %.1f 小时",
                            MAX_DURATION_HOURS, minutes / 60.0));
        }

        if (!startTime.toLocalDate().isEqual(endTime.toLocalDate())) {
            throw BusinessException.badRequest("不允许跨午夜的预定，请确保开始和结束在同一天");
        }

        if (room.getAvailableSlots() != null && !room.getAvailableSlots().isEmpty()) {
            if (!isWithinAvailableSlots(startTime.toLocalTime(), endTime.toLocalTime(), room.getAvailableSlots())) {
                String slotsStr = room.getAvailableSlots().stream()
                        .map(s -> s.getStart() + "-" + s.getEnd())
                        .collect(Collectors.joining(", "));
                throw BusinessException.badRequest(
                        String.format("预定时间不在会议室可预约时段内，当前会议室可预约时段: %s", slotsStr));
            }
        }
    }

    private boolean isWithinAvailableSlots(LocalTime startTime, LocalTime endTime, List<TimeSlot> availableSlots) {
        for (TimeSlot slot : availableSlots) {
            LocalTime slotStart = LocalTime.parse(slot.getStart(), DateTimeFormatter.ofPattern("HH:mm"));
            LocalTime slotEnd = LocalTime.parse(slot.getEnd(), DateTimeFormatter.ofPattern("HH:mm"));

            if (!startTime.isBefore(slotStart) && !endTime.isAfter(slotEnd)) {
                return true;
            }
        }
        return false;
    }

    private void checkConflict(Long roomId, LocalDateTime startTime, LocalDateTime endTime, Long excludeId) {
        try {
            LocalDateTime bufferedStart = startTime.minusMinutes(BUFFER_MINUTES);
            LocalDateTime bufferedEnd = endTime.plusMinutes(BUFFER_MINUTES);

            String jpql;
            if (excludeId != null) {
                jpql = "SELECT r FROM Reservation r WHERE r.id <> :excludeId AND r.roomId = :roomId " +
                        "AND r.cancelled = false AND r.startTime < :endTime AND r.endTime > :startTime";
            } else {
                jpql = "SELECT r FROM Reservation r WHERE r.roomId = :roomId " +
                        "AND r.cancelled = false AND r.startTime < :endTime AND r.endTime > :startTime";
            }

            TypedQuery<Reservation> query = entityManager.createQuery(jpql, Reservation.class)
                    .setParameter("roomId", roomId)
                    .setParameter("startTime", bufferedStart)
                    .setParameter("endTime", bufferedEnd);
            if (excludeId != null) {
                query.setParameter("excludeId", excludeId);
            }

            List<Reservation> conflicting = query.getResultList();

            if (!conflicting.isEmpty()) {
                String conflictDetails = conflicting.stream()
                        .map(r -> String.format("%s (%s - %s, 前后各 %d 分钟缓冲)",
                                r.getTitle(),
                                r.getStartTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")),
                                r.getEndTime().format(DateTimeFormatter.ofPattern("HH:mm")),
                                BUFFER_MINUTES))
                        .collect(Collectors.joining("; "));

                throw BusinessException.conflict(
                        String.format("预定时段存在冲突（含前后各 %d 分钟缓冲）。冲突的预定: %s",
                                BUFFER_MINUTES, conflictDetails));
            }
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("冲突检测失败 roomId={}, start={}, end={}", roomId, startTime, endTime, e);
            throw BusinessException.badRequest("冲突检测失败: " + e.getMessage());
        }
    }

    private Reservation buildReservation(CreateReservationRequest request, String seriesId,
                                         LocalDateTime startTime, LocalDateTime endTime) {
        Reservation reservation = new Reservation();
        reservation.setRoomId(request.getRoomId());
        reservation.setEmployeeId(request.getEmployeeId());
        reservation.setEmployeeName(request.getEmployeeName());
        reservation.setTitle(request.getTitle());
        reservation.setStartTime(startTime);
        reservation.setEndTime(endTime);
        reservation.setSeriesId(seriesId);
        reservation.setRecurringType(seriesId != null ?
                (request.getRecurringType() != null ? request.getRecurringType() : "WEEKLY") : "NONE");
        reservation.setCancelled(false);
        return reservation;
    }

    private ReservationResponse toResponse(Reservation reservation, String roomName) {
        return new ReservationResponse(
                reservation.getId(),
                reservation.getRoomId(),
                roomName != null ? roomName : "未知会议室",
                reservation.getEmployeeId(),
                reservation.getEmployeeName(),
                reservation.getTitle(),
                reservation.getStartTime(),
                reservation.getEndTime(),
                reservation.getSeriesId(),
                reservation.getRecurringType(),
                reservation.getCancelled(),
                reservation.getCreatedAt(),
                reservation.getUpdatedAt()
        );
    }
}
