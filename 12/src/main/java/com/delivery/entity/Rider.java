package com.delivery.entity;

import com.delivery.enums.RiderStatus;
import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "rider", indexes = {
        @Index(name = "idx_rider_rider_no", columnList = "riderNo", unique = true),
        @Index(name = "idx_rider_status", columnList = "status"),
        @Index(name = "idx_rider_grid_code", columnList = "gridCode")
})
public class Rider {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 32)
    private String riderNo;

    @Column(nullable = false, length = 32)
    private String name;

    @Column(length = 16)
    private String phone;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private RiderStatus status;

    private Double latitude;

    private Double longitude;

    @Column(length = 16)
    private String gridCode;

    private Integer currentOrderCount = 0;

    private Integer totalOrderCount = 0;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createTime;

    @UpdateTimestamp
    @Column(nullable = false)
    private LocalDateTime updateTime;
}
