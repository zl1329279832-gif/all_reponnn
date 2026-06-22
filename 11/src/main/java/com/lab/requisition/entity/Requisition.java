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
@Table(name = "requisitions")
public class Requisition {

    public enum Status {
        PENDING,
        APPROVED,
        PARTIALLY_ISSUED,
        FULFILLED,
        REJECTED,
        CLOSED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true)
    private String idempotencyKey;

    @Column(name = "sku_id", nullable = false)
    private Long skuId;

    @Column(nullable = false)
    private Integer quantity;

    @Column(nullable = false)
    private Integer issuedQuantity = 0;

    @Column(nullable = false)
    private Integer returnedQuantity = 0;

    @Column(nullable = false)
    private String researcher;

    private String purpose;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private Status status;

    private String approver;

    private String approvalRemark;

    private LocalDateTime approvedAt;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @Column(nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
        if (status == null) {
            status = Status.PENDING;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
