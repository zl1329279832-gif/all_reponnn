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
@Table(name = "audit_logs")
public class AuditLog {

    public enum Action {
        REQUISITION_CREATED,
        REQUISITION_APPROVED,
        REQUISITION_REJECTED,
        STOCK_DEDUCTED,
        STOCK_RESTORED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "requisition_id")
    private Long requisitionId;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private Action action;

    private String operator;

    @Column(length = 1000)
    private String detail;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
