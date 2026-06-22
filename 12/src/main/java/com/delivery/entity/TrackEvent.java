package com.delivery.entity;

import com.delivery.enums.TrackEventType;
import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "track_event", indexes = {
        @Index(name = "idx_order_no", columnList = "orderNo"),
        @Index(name = "idx_event_time", columnList = "eventTime"),
        @Index(name = "idx_order_event", columnList = "orderNo,eventType", unique = true)
})
public class TrackEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 32)
    private String orderNo;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private TrackEventType eventType;

    @Column(length = 256)
    private String description;

    private Long riderId;

    private Double latitude;

    private Double longitude;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime eventTime;

    @Column(length = 64)
    private String operator;
}
