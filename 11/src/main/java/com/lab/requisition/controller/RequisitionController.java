package com.lab.requisition.controller;

import com.lab.requisition.dto.ApprovalRequest;
import com.lab.requisition.dto.RequisitionCreateRequest;
import com.lab.requisition.entity.AuditLog;
import com.lab.requisition.entity.Requisition;
import com.lab.requisition.service.AuditService;
import com.lab.requisition.service.RequisitionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/requisitions")
@RequiredArgsConstructor
public class RequisitionController {

    private final RequisitionService requisitionService;
    private final AuditService auditService;

    @GetMapping
    public ResponseEntity<Page<Requisition>> list(
            @RequestParam(required = false) Requisition.Status status,
            @RequestParam(required = false) String researcher,
            @RequestParam(required = false) Long skuId,
            @PageableDefault(size = 20) Pageable pageable) {
        return ResponseEntity.ok(requisitionService.list(status, researcher, skuId, pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Requisition> getById(@PathVariable Long id) {
        return ResponseEntity.ok(requisitionService.getById(id));
    }

    @GetMapping("/{id}/audit-logs")
    public ResponseEntity<List<AuditLog>> getAuditLogs(@PathVariable Long id) {
        return ResponseEntity.ok(auditService.getByRequisitionId(id));
    }

    @PostMapping
    public ResponseEntity<Requisition> create(
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @Valid @RequestBody RequisitionCreateRequest request) {
        Requisition existing = requisitionService
                .findByIdempotencyKey(idempotencyKey)
                .orElse(null);

        if (existing != null) {
            return ResponseEntity.status(HttpStatus.OK).body(existing);
        }

        Requisition created = requisitionService.create(request, idempotencyKey);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @PostMapping("/{id}/approve")
    public ResponseEntity<Requisition> approve(
            @PathVariable Long id,
            @Valid @RequestBody ApprovalRequest request) {
        return ResponseEntity.ok(requisitionService.approve(id, request));
    }

    @PostMapping("/{id}/reject")
    public ResponseEntity<Requisition> reject(
            @PathVariable Long id,
            @Valid @RequestBody ApprovalRequest request) {
        return ResponseEntity.ok(requisitionService.reject(id, request));
    }
}
