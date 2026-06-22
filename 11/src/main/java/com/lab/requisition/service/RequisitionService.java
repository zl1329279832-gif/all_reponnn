package com.lab.requisition.service;

import com.lab.requisition.dto.ApprovalRequest;
import com.lab.requisition.dto.RequisitionCreateRequest;
import com.lab.requisition.entity.AuditLog;
import com.lab.requisition.entity.Requisition;
import com.lab.requisition.entity.Sku;
import com.lab.requisition.repository.RequisitionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class RequisitionService {

    private final RequisitionRepository requisitionRepository;
    private final InventoryService inventoryService;
    private final SkuService skuService;
    private final AuditService auditService;

    @Transactional(readOnly = true)
    public Page<Requisition> list(Requisition.Status status, String researcher, Long skuId, Pageable pageable) {
        if (status != null) {
            return requisitionRepository.findByStatus(status, pageable);
        }
        if (researcher != null) {
            return requisitionRepository.findByResearcher(researcher, pageable);
        }
        if (skuId != null) {
            return requisitionRepository.findBySkuId(skuId, pageable);
        }
        return requisitionRepository.findAll(pageable);
    }

    @Transactional(readOnly = true)
    public Requisition getById(Long id) {
        return requisitionRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Requisition not found: " + id));
    }

    @Transactional(readOnly = true)
    public Optional<Requisition> findByIdempotencyKey(String idempotencyKey) {
        return requisitionRepository.findByIdempotencyKey(idempotencyKey);
    }

    @Transactional
    public Requisition create(RequisitionCreateRequest request, String idempotencyKey) {
        if (idempotencyKey != null) {
            Optional<Requisition> existing = requisitionRepository.findByIdempotencyKey(idempotencyKey);
            if (existing.isPresent()) {
                return existing.get();
            }
        }

        Sku sku = skuService.getById(request.getSkuId());

        Integer totalStock = inventoryService.getTotalStock(request.getSkuId());
        if (totalStock < request.getQuantity()) {
            throw new RuntimeException("Insufficient stock. Available: "
                    + totalStock + ", requested: " + request.getQuantity());
        }

        inventoryService.deductStockFromAnyLocation(request.getSkuId(), request.getQuantity());

        Requisition requisition = new Requisition();
        requisition.setIdempotencyKey(idempotencyKey);
        requisition.setSkuId(request.getSkuId());
        requisition.setQuantity(request.getQuantity());
        requisition.setResearcher(request.getResearcher());
        requisition.setPurpose(request.getPurpose());
        requisition.setStatus(Requisition.Status.PENDING);

        Requisition saved = requisitionRepository.save(requisition);

        auditService.log(
                AuditLog.Action.REQUISITION_CREATED,
                saved.getId(),
                request.getResearcher(),
                "Created requisition for SKU " + sku.getSkuCode()
                        + " (" + sku.getName() + "), quantity: " + request.getQuantity()
        );

        auditService.log(
                AuditLog.Action.STOCK_DEDUCTED,
                saved.getId(),
                "system",
                "Deducted " + request.getQuantity() + " units from stock for SKU " + sku.getSkuCode()
        );

        return saved;
    }

    @Transactional
    public Requisition approve(Long id, ApprovalRequest request) {
        Requisition req = getById(id);
        if (req.getStatus() != Requisition.Status.PENDING) {
            throw new RuntimeException("Requisition is not pending. Current status: " + req.getStatus());
        }

        req.setStatus(Requisition.Status.APPROVED);
        req.setApprover(request.getApprover());
        req.setApprovalRemark(request.getRemark());
        req.setApprovedAt(LocalDateTime.now());

        Requisition saved = requisitionRepository.save(req);

        Sku sku = skuService.getById(req.getSkuId());
        auditService.log(
                AuditLog.Action.REQUISITION_APPROVED,
                saved.getId(),
                request.getApprover(),
                "Approved requisition for SKU " + sku.getSkuCode()
                        + ", quantity: " + req.getQuantity()
                        + (request.getRemark() != null ? ". Remark: " + request.getRemark() : "")
        );

        return saved;
    }

    @Transactional
    public Requisition reject(Long id, ApprovalRequest request) {
        Requisition req = getById(id);
        if (req.getStatus() != Requisition.Status.PENDING) {
            throw new RuntimeException("Requisition is not pending. Current status: " + req.getStatus());
        }

        req.setStatus(Requisition.Status.REJECTED);
        req.setApprover(request.getApprover());
        req.setApprovalRemark(request.getRemark());
        req.setApprovedAt(LocalDateTime.now());

        inventoryService.restoreStockToFirstLocation(req.getSkuId(), req.getQuantity());

        Requisition saved = requisitionRepository.save(req);

        Sku sku = skuService.getById(req.getSkuId());
        auditService.log(
                AuditLog.Action.REQUISITION_REJECTED,
                saved.getId(),
                request.getApprover(),
                "Rejected requisition for SKU " + sku.getSkuCode()
                        + ", quantity: " + req.getQuantity()
                        + (request.getRemark() != null ? ". Reason: " + request.getRemark() : "")
        );

        auditService.log(
                AuditLog.Action.STOCK_RESTORED,
                saved.getId(),
                "system",
                "Restored " + req.getQuantity() + " units to stock for SKU " + sku.getSkuCode()
        );

        return saved;
    }
}
