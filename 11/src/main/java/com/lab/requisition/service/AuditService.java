package com.lab.requisition.service;

import com.lab.requisition.entity.AuditLog;
import com.lab.requisition.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AuditService {

    private final AuditLogRepository auditLogRepository;

    @Transactional
    public AuditLog log(AuditLog.Action action, Long requisitionId, String operator, String detail) {
        AuditLog log = new AuditLog();
        log.setAction(action);
        log.setRequisitionId(requisitionId);
        log.setOperator(operator);
        log.setDetail(detail);
        return auditLogRepository.save(log);
    }

    @Transactional(readOnly = true)
    public List<AuditLog> getByRequisitionId(Long requisitionId) {
        return auditLogRepository.findByRequisitionIdOrderByCreatedAtDesc(requisitionId);
    }

    @Transactional(readOnly = true)
    public Page<AuditLog> list(Pageable pageable) {
        return auditLogRepository.findAll(pageable);
    }

    @Transactional(readOnly = true)
    public Page<AuditLog> listByOperator(String operator, Pageable pageable) {
        return auditLogRepository.findByOperator(operator, pageable);
    }
}
