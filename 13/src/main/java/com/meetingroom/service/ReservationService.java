package com.meetingroom.service;

import com.meetingroom.dto.CreateReservationRequest;
import com.meetingroom.dto.ReservationResponse;
import com.meetingroom.entity.MeetingRoom;
import com.meetingroom.entity.Reservation;
import com.meetingroom.entity.TimeSlot;
import com.meetingroom.exception.BusinessException;
import com.meetingroom.repository.ReservationRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
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

    @Transactional(readOnly = true)
    public List<ReservationResponse> findByFilters(Long roomId, Integer floor, Integer minCapacity,
                                                   LocalDate startDate, LocalDate endDate) {
        List<Reservation> reservations;
        LocalDateTime startDateTime = startDate != null ? startDate.atStartOfDay() : null;
        LocalDateTime endDateTime = endDate != null ? endDate.atTime(23, 59, 59) : null;

        if (roomId != null && startDateTime != null && endDateTime != null) {
            reservations = reservationRepository.findByRoomIdAndDateTimeRange(roomId, startDateTime, endDateTime);
        } else if (startDateTime != null && endDateTime != null) {
            reservations = reservationRepository.findByDateTimeRange(startDateTime, endDateTime);
        } else if (roomId != null) {
            reservations = reservationRepository.findByRoomIdAndCancelledFalse(roomId);
        } else {
            reservations = reservationRepository.findAll().stream()
                    .filter(r -> !r.getCancelled())
                    .collect(Collectors.toList());
        }

        Map<Long, String> roomNames = meetingRoomService.findAll().stream()
                .collect(Collectors.toMap(r -> r.getId(), r -> r.getName()));

        List<ReservationResponse> responses = reservations.stream()
                .map(r -> toResponse(r, roomNames.get(r.getRoomId())))
                .collect(Collectors.toList());

        if (floor != null || minCapacity != null) {
            Map<Long, MeetingRoom> roomMap = meetingRoomService.findAll().stream()
                    .collect(Collectors.toMap(r -> r.getId(), r -> {
                        MeetingRoom room = new MeetingRoom();
                        room.setId(r.getId());
                        room.setName(r.getName());
                        room.setFloor(r.getFloor());
                        room.setCapacity(r.getCapacity());
                        return room;
                    }));

            responses = responses.stream()
                    .filter(r -> {
                        MeetingRoom room = roomMap.get(r.getRoomId());
                        if (room == null) return false;
                        if (floor != null && !room.getFloor().equals(floor)) return false;
                        if (minCapacity != null && room.getCapacity() < minCapacity) return false;
                        return true;
                    })
                    .collect(Collectors.toList());
        }

        return responses;
    }

    @Transactional(readOnly = true)
    public ReservationResponse findById(Long id) {
        Reservation reservation = reservationRepository.findById(id)
                .orElseThrow(() -> BusinessException.notFound("预定不存在，ID: " + id));

        String roomName = meetingRoomService.findById(reservation.getRoomId()).getName();
        return toResponse(reservation, roomName);
    }

    @Transactional(readOnly = true)
    public List<ReservationResponse> findBySeriesId(String seriesId) {
        List<Reservation> reservations = reservationRepository.findBySeriesIdAndCancelledFalse(seriesId);
        if (reservations.isEmpty()) {
            throw BusinessException.notFound("周期预定系列不存在，Series ID: " + seriesId);
        }

        Map<Long, String> roomNames = meetingRoomService.findAll().stream()
                .collect(Collectors.toMap(r -> r.getId(), r -> r.getName()));

        return reservations.stream()
                .map(r -> toResponse(r, roomNames.get(r.getRoomId())))
                .collect(Collectors.toList());
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
        Reservation reservation = reservationRepository.findById(id)
                .orElseThrow(() -> BusinessException.notFound("预定不存在，ID: " + id));

        if (reservation.getCancelled()) {
            throw BusinessException.conflict("该预定已被取消");
        }

        reservation.setCancelled(true);
        reservationRepository.save(reservation);
        log.info("已取消单天预定 ID: {}, 系列 ID: {}", id, reservation.getSeriesId());
    }

    @Transactional
    public void cancelSeries(String seriesId) {
        List<Reservation> reservations = reservationRepository.findBySeriesIdAndCancelledFalse(seriesId);
        if (reservations.isEmpty()) {
            throw BusinessException.notFound("周期预定系列不存在，Series ID: " + seriesId);
        }

        for (Reservation reservation : reservations) {
            reservation.setCancelled(true);
            reservationRepository.save(reservation);
        }
        log.info("已取消整个周期预定系列，Series ID: {}, 共 {} 个实例", seriesId, reservations.size());
    }

    private List<ReservationResponse> createSingleReservation(CreateReservationRequest request, MeetingRoom room) {
        checkConflict(request.getRoomId(), request.getStartTime(), request.getEndTime(), null);

        Reservation reservation = buildReservation(request, null, request.getStartTime(), request.getEndTime());
        Reservation saved = reservationRepository.save(reservation);

        log.info("创建单次预定成功，ID: {}, 会议室: {}, 时间: {} - {}",
                saved.getId(), room.getName(), saved.getStartTime(), saved.getEndTime());

        return List.of(toResponse(saved, room.getName()));
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

        List<Reservation> saved = reservationRepository.saveAll(createdReservations);

        log.info("创建周期预定成功，Series ID: {}, 成功创建 {} 个实例，跳过 {} 个（{}）",
                seriesId, saved.size(), conflicts.size(),
                conflicts.isEmpty() ? "无冲突" : String.join("; ", conflicts));

        return saved.stream()
                .map(r -> toResponse(r, room.getName()))
                .collect(Collectors.toList());
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
        if (duration.toHours() > MAX_DURATION_HOURS ||
            (duration.toHours() == MAX_DURATION_HOURS && duration.toMinutesPart() > 0)) {
            throw BusinessException.badRequest(
                String.format("单次预定最长不超过 %d 小时，当前时长: %.1f 小时",
                    MAX_DURATION_HOURS, duration.toMinutes() / 60.0));
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
        LocalDateTime bufferedStart = startTime.minusMinutes(BUFFER_MINUTES);
        LocalDateTime bufferedEnd = endTime.plusMinutes(BUFFER_MINUTES);

        List<Reservation> conflicting;
        if (excludeId != null) {
            conflicting = reservationRepository.findConflictingReservationsExcluding(
                    excludeId, roomId, bufferedStart, bufferedEnd);
        } else {
            conflicting = reservationRepository.findConflictingReservations(
                    roomId, bufferedStart, bufferedEnd);
        }

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
