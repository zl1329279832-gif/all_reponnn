package com.meetingroom.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "reservations")
public class Reservation {

    public static final String STATUS_NORMAL = "NORMAL";
    public static final String STATUS_CHECKED_IN = "CHECKED_IN";
    public static final String STATUS_RELEASED = "RELEASED";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "room_id", nullable = false)
    private Long roomId;

    @Column(name = "employee_id", nullable = false)
    private String employeeId;

    @Column(name = "employee_name", nullable = false)
    private String employeeName;

    @Column(nullable = false)
    private String title;

    @Column(name = "start_time", nullable = false)
    @Convert(converter = LocalDateTimeConverter.class)
    private LocalDateTime startTime;

    @Column(name = "end_time", nullable = false)
    @Convert(converter = LocalDateTimeConverter.class)
    private LocalDateTime endTime;

    @Column(name = "series_id")
    private String seriesId;

    @Column(name = "recurring_type", nullable = false)
    private String recurringType = "NONE";

    @Column(nullable = false)
    private Boolean cancelled = false;

    @Column(name = "status", nullable = false)
    private String status = STATUS_NORMAL;

    @Column(name = "check_in_time")
    @Convert(converter = LocalDateTimeConverter.class)
    private LocalDateTime checkInTime;

    @Column(name = "created_at", updatable = false)
    @Convert(converter = LocalDateTimeConverter.class)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    @Convert(converter = LocalDateTimeConverter.class)
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        LocalDateTime now = LocalDateTime.now();
        this.createdAt = now;
        this.updatedAt = now;
        if (this.status == null) {
            this.status = STATUS_NORMAL;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}
