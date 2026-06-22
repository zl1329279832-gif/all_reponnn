package com.delivery.entity;

import com.delivery.enums.OrderStatus;
import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "delivery_order", indexes = {
        @Index(name = "idx_order_no", columnList = "orderNo", unique = true),
        @Index(name = "idx_rider_id", columnList = "riderId"),
        @Index(name = "idx_status", columnList = "status"),
        @Index(name = "idx_grid_code", columnList = "gridCode")
})
public class DeliveryOrder {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 32)
    private String orderNo;

    @Column(nullable = false, length = 64)
    private String merchantName;

    @Column(nullable = false, length = 128)
    private String pickupAddress;

    private Double pickupLatitude;

    private Double pickupLongitude;

    @Column(nullable = false, length = 128)
    private String deliveryAddress;

    private Double deliveryLatitude;

    private Double deliveryLongitude;

    @Column(length = 16)
    private String gridCode;

    @Column(length = 32)
    private String receiverName;

    @Column(length = 16)
    private String receiverPhone;

    @Column(precision = 10, scale = 2)
    private BigDecimal orderAmount;

    @Column(precision = 10, scale = 2)
    private BigDecimal deliveryFee;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private OrderStatus status;

    private Long riderId;

    @Column(length = 32)
    private String riderName;

    @Column(length = 16)
    private String riderPhone;

    private Boolean deducted = false;

    @Column(length = 256)
    private String remark;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createTime;

    @UpdateTimestamp
    @Column(nullable = false)
    private LocalDateTime updateTime;

    private LocalDateTime pickupTime;

    private LocalDateTime deliveryTime;

    private LocalDateTime cancelTime;

    @Version
    private Long version;
}
