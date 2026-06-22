package com.lab.requisition.repository;

import com.lab.requisition.entity.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {

    List<AuditLog> findByRequisitionIdOrderByCreatedAtDesc(Long requisitionId);

    Page<AuditLog> findByOperator(String operator, Pageable pageable);

    Page<AuditLog> findByAction(AuditLog.Action action, Pageable pageable);
}
