package com.meetingroom.repository;

import com.meetingroom.entity.Reservation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface ReservationRepository extends JpaRepository<Reservation, Long> {

    List<Reservation> findByRoomIdAndCancelledFalse(Long roomId);

    List<Reservation> findBySeriesIdAndCancelledFalse(String seriesId);

    @Query("SELECT r FROM Reservation r WHERE r.roomId = :roomId " +
           "AND r.cancelled = false " +
           "AND r.startTime < :endTime " +
           "AND r.endTime > :startTime")
    List<Reservation> findConflictingReservations(
            @Param("roomId") Long roomId,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime);

    @Query("SELECT r FROM Reservation r WHERE r.id <> :excludeId " +
           "AND r.roomId = :roomId " +
           "AND r.cancelled = false " +
           "AND r.startTime < :endTime " +
           "AND r.endTime > :startTime")
    List<Reservation> findConflictingReservationsExcluding(
            @Param("excludeId") Long excludeId,
            @Param("roomId") Long roomId,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime);

    @Query("SELECT r FROM Reservation r WHERE r.cancelled = false " +
           "AND r.startTime >= :startOfDay " +
           "AND r.startTime < :endOfDay")
    List<Reservation> findByDateRange(
            @Param("startOfDay") LocalDateTime startOfDay,
            @Param("endOfDay") LocalDateTime endOfDay);

    @Query("SELECT r FROM Reservation r WHERE r.cancelled = false " +
           "AND r.startTime >= :startDateTime " +
           "AND r.endTime <= :endDateTime")
    List<Reservation> findByDateTimeRange(
            @Param("startDateTime") LocalDateTime startDateTime,
            @Param("endDateTime") LocalDateTime endDateTime);

    @Query("SELECT r FROM Reservation r WHERE r.roomId = :roomId " +
           "AND r.cancelled = false " +
           "AND r.startTime >= :startDateTime " +
           "AND r.endTime <= :endDateTime")
    List<Reservation> findByRoomIdAndDateTimeRange(
            @Param("roomId") Long roomId,
            @Param("startDateTime") LocalDateTime startDateTime,
            @Param("endDateTime") LocalDateTime endDateTime);
}
