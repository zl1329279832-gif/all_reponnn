package com.lab.requisition.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "stock_alerts")
public class StockAlert {

    public enum AlertLevel {
        WARNING,
        CRITICAL
    }

    public enum AlertStatus {
        ACTIVE,
        RESOLVED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sku_id", nullable = false)
    private Long skuId;

    private String skuCode;

    private String skuName;

    private String category;

    private String lab;

    private Integer currentStock;

    private Integer safetyStock;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private AlertLevel alertLevel;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private AlertStatus status;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    private LocalDateTime resolvedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        if (status == null) {
            status = AlertStatus.ACTIVE;
        }
    }
}
