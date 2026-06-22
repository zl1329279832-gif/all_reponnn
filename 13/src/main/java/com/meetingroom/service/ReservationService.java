package com.meetingroom.service;

import com.meetingroom.dto.CreateReservationRequest;
import com.meetingroom.dto.MeetingRoomResponse;
import com.meetingroom.dto.ReservationAuditResponse;
import com.meetingroom.dto.ReservationResponse;
import com.meetingroom.entity.MeetingRoom;
import com.meetingroom.entity.Reservation;
import com.meetingroom.entity.ReservationAudit;
import com.meetingroom.entity.TimeSlot;
import com.meetingroom.exception.BusinessException;
import com.meetingroom.repository.ReservationAuditRepository;
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
    private static final int CHECKIN_WINDOW_MINUTES = 15;

    public static final String ACTION_CHECK_IN = "CHECK_IN";
    public static final String ACTION_RELEASE_TIMEOUT = "RELEASE_TIMEOUT";
    public static final String ACTION_CANCEL = "CANCEL";

    private final ReservationRepository reservationRepository;
    private final ReservationAuditRepository auditRepository;
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

    @Transactional(readOnly = true)
    public List<ReservationAuditResponse> findAuditsByReservationId(Long reservationId) {
        try {
            List<ReservationAudit> audits = entityManager.createQuery(
                            "SELECT a FROM ReservationAudit a WHERE a.reservationId = :reservationId ORDER BY a.createdAt ASC",
                            ReservationAudit.class)
                    .setParameter("reservationId", reservationId)
                    .getResultList();
            return audits.stream().map(this::toAuditResponse).collect(Collectors.toList());
        } catch (DataAccessException e) {
            log.error("查询审计记录失败 reservationId={}", reservationId, e);
            throw BusinessException.badRequest("查询审计记录失败: " + e.getMessage());
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
    public ReservationResponse checkIn(Long id, String operator) {
        try {
            Reservation reservation = reservationRepository.findById(id)
                    .orElseThrow(() -> BusinessException.notFound("预定不存在，ID: " + id));

            if (reservation.getCancelled()) {
                throw BusinessException.conflict("该预定已被取消，无法签到");
            }
            if (Reservation.STATUS_RELEASED.equals(reservation.getStatus())) {
                throw BusinessException.conflict("该预定已因超时未签到被释放，无法签到");
            }
            if (Reservation.STATUS_CHECKED_IN.equals(reservation.getStatus())) {
                throw BusinessException.conflict("该预定已签到，请勿重复签到");
            }

            LocalDateTime now = LocalDateTime.now();
            LocalDateTime windowStart = reservation.getStartTime();
            LocalDateTime windowEnd = reservation.getStartTime().plusMinutes(CHECKIN_WINDOW_MINUTES);

            if (now.isBefore(windowStart)) {
                throw BusinessException.badRequest(
                        String.format("签到窗口未开启，请在 %s 之后签到",
                                windowStart.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))));
            }
            if (now.isAfter(windowEnd)) {
                throw BusinessException.conflict(
                        String.format("已超过签到截止时间（开始后 %d 分钟），预定已释放或即将释放，请重新预约",
                                CHECKIN_WINDOW_MINUTES));
            }

            reservation.setStatus(Reservation.STATUS_CHECKED_IN);
            reservation.setCheckInTime(now);
            Reservation saved = reservationRepository.save(reservation);

            createAudit(saved.getId(), ACTION_CHECK_IN, operator,
                    String.format("签到时间 %s", now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))));

            log.info("签到成功 reservationId={}, operator={}, time={}", id, operator, now);

            String roomName = meetingRoomService.findById(saved.getRoomId()).getName();
            return toResponse(saved, roomName);
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("签到失败 id={}", id, e);
            throw BusinessException.badRequest("签到失败: " + e.getMessage());
        }
    }

    @Transactional
    public int releaseTimedOutReservations() {
        try {
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime cutoff = now.minusMinutes(CHECKIN_WINDOW_MINUTES);

            List<Reservation> timedOut = entityManager.createQuery(
                            "SELECT r FROM Reservation r WHERE r.status = :status " +
                                    "AND r.cancelled = false " +
                                    "AND r.startTime < :cutoff",
                            Reservation.class)
                    .setParameter("status", Reservation.STATUS_NORMAL)
                    .setParameter("cutoff", cutoff)
                    .getResultList();

            for (Reservation r : timedOut) {
                r.setStatus(Reservation.STATUS_RELEASED);
                reservationRepository.save(r);
                createAudit(r.getId(), ACTION_RELEASE_TIMEOUT, "SYSTEM",
                        String.format("开始时间 %s 超过 %d 分钟未签到，自动释放时段",
                                r.getStartTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")),
                                CHECKIN_WINDOW_MINUTES));
                log.info("自动释放超时未签到预定 reservationId={}, startTime={}", r.getId(), r.getStartTime());
            }

            return timedOut.size();
        } catch (DataAccessException e) {
            log.error("自动释放超时预定失败", e);
            return 0;
        }
    }

    @Transactional
    public void cancelSingle(Long id, String operator) {
        try {
            Reservation reservation = reservationRepository.findById(id)
                    .orElseThrow(() -> BusinessException.notFound("预定不存在，ID: " + id));

            if (reservation.getCancelled()) {
                throw BusinessException.conflict("该预定已被取消");
            }

            reservation.setCancelled(true);
            reservationRepository.save(reservation);

            createAudit(reservation.getId(), ACTION_CANCEL, operator, "取消单天预定");

            log.info("已取消单天预定 ID: {}, 系列 ID: {}", id, reservation.getSeriesId());
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("取消预定失败 id={}", id, e);
            throw BusinessException.badRequest("取消预定失败: " + e.getMessage());
        }
    }

    @Transactional
    public void cancelSeries(String seriesId, String operator) {
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
                createAudit(reservation.getId(), ACTION_CANCEL, operator, "取消整个周期系列中的一天");
            }
            log.info("已取消整个周期预定系列，Series ID: {}, 共 {} 个实例", seriesId, reservations.size());
        } catch (BusinessException e) {
            throw e;
        } catch (DataAccessException e) {
            log.error("取消周期系列失败 seriesId={}", seriesId, e);
            throw BusinessException.badRequest("取消周期系列失败: " + e.getMessage());
        }
    }

    private void createAudit(Long reservationId, String action, String operator, String remark) {
        try {
            ReservationAudit audit = new ReservationAudit();
            audit.setReservationId(reservationId);
            audit.setAction(action);
            audit.setOperator(operator == null || operator.isBlank() ? "UNKNOWN" : operator);
            audit.setRemark(remark);
            auditRepository.save(audit);
        } catch (DataAccessException e) {
            log.error("写入审计记录失败 reservationId={}, action={}", reservationId, action, e);
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
                        "AND r.cancelled = false AND r.status <> :released " +
                        "AND r.startTime < :endTime AND r.endTime > :startTime";
            } else {
                jpql = "SELECT r FROM Reservation r WHERE r.roomId = :roomId " +
                        "AND r.cancelled = false AND r.status <> :released " +
                        "AND r.startTime < :endTime AND r.endTime > :startTime";
            }

            TypedQuery<Reservation> query = entityManager.createQuery(jpql, Reservation.class)
                    .setParameter("roomId", roomId)
                    .setParameter("startTime", bufferedStart)
                    .setParameter("endTime", bufferedEnd)
                    .setParameter("released", Reservation.STATUS_RELEASED);
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
        reservation.setStatus(Reservation.STATUS_NORMAL);
        reservation.setCheckInTime(null);
        return reservation;
    }

    private ReservationResponse toResponse(Reservation reservation, String roomName) {
        ReservationResponse response = new ReservationResponse();
        response.setId(reservation.getId());
        response.setRoomId(reservation.getRoomId());
        response.setRoomName(roomName != null ? roomName : "未知会议室");
        response.setEmployeeId(reservation.getEmployeeId());
        response.setEmployeeName(reservation.getEmployeeName());
        response.setTitle(reservation.getTitle());
        response.setStartTime(reservation.getStartTime());
        response.setEndTime(reservation.getEndTime());
        response.setSeriesId(reservation.getSeriesId());
        response.setRecurringType(reservation.getRecurringType());
        response.setCancelled(reservation.getCancelled());
        response.setStatus(reservation.getStatus());
        response.setCheckedIn(Reservation.STATUS_CHECKED_IN.equals(reservation.getStatus()));
        response.setReleased(Reservation.STATUS_RELEASED.equals(reservation.getStatus()));
        response.setCheckInTime(reservation.getCheckInTime());
        response.setCreatedAt(reservation.getCreatedAt());
        response.setUpdatedAt(reservation.getUpdatedAt());
        return response;
    }

    private ReservationAuditResponse toAuditResponse(ReservationAudit audit) {
        return new ReservationAuditResponse(
                audit.getId(),
                audit.getReservationId(),
                audit.getAction(),
                audit.getOperator(),
                audit.getRemark(),
                audit.getCreatedAt()
        );
    }
}
