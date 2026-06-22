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

        Integer availableStock = inventoryService.getAvailableStock(request.getSkuId());
        if (availableStock < request.getQuantity()) {
            throw new RuntimeException("Insufficient available stock. Available: "
                    + availableStock + ", requested: " + request.getQuantity());
        }

        inventoryService.reserveStock(request.getSkuId(), request.getQuantity());

        Requisition requisition = new Requisition();
        requisition.setIdempotencyKey(idempotencyKey);
        requisition.setSkuId(request.getSkuId());
        requisition.setQuantity(request.getQuantity());
        requisition.setIssuedQuantity(0);
        requisition.setReturnedQuantity(0);
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
                AuditLog.Action.STOCK_RESERVED,
                saved.getId(),
                "system",
                "Reserved " + request.getQuantity() + " units for SKU " + sku.getSkuCode()
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

        inventoryService.releaseReservedStock(req.getSkuId(), req.getQuantity());

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
                AuditLog.Action.STOCK_RELEASED,
                saved.getId(),
                "system",
                "Released " + req.getQuantity() + " reserved units for SKU " + sku.getSkuCode()
        );

        return saved;
    }

    @Transactional
    public Requisition issue(Long id, int quantity, String operator) {
        Requisition req = getById(id);
        if (req.getStatus() != Requisition.Status.APPROVED
                && req.getStatus() != Requisition.Status.PARTIALLY_ISSUED) {
            throw new RuntimeException("Requisition is not eligible for issue. Current status: " + req.getStatus());
        }

        int remainingToIssue = req.getQuantity() - req.getIssuedQuantity();
        if (quantity > remainingToIssue) {
            throw new RuntimeException("Cannot issue more than remaining quantity. "
                    + "Remaining: " + remainingToIssue + ", requested: " + quantity);
        }

        inventoryService.issueStock(req.getSkuId(), quantity);

        int newIssued = req.getIssuedQuantity() + quantity;
        req.setIssuedQuantity(newIssued);

        if (newIssued >= req.getQuantity()) {
            req.setStatus(Requisition.Status.FULFILLED);
        } else {
            req.setStatus(Requisition.Status.PARTIALLY_ISSUED);
        }

        Requisition saved = requisitionRepository.save(req);

        Sku sku = skuService.getById(req.getSkuId());
        auditService.log(
                AuditLog.Action.STOCK_ISSUED,
                saved.getId(),
                operator,
                "Issued " + quantity + " units for SKU " + sku.getSkuCode()
                        + ". Total issued: " + newIssued + "/" + req.getQuantity()
        );

        return saved;
    }

    @Transactional
    public Requisition returnStock(Long id, int quantity, String operator) {
        Requisition req = getById(id);

        if (req.getStatus() != Requisition.Status.PARTIALLY_ISSUED
                && req.getStatus() != Requisition.Status.FULFILLED) {
            throw new RuntimeException("Requisition is not eligible for return. Current status: " + req.getStatus());
        }

        int issuedNet = req.getIssuedQuantity() - req.getReturnedQuantity();
        if (quantity > issuedNet) {
            throw new RuntimeException("Cannot return more than net issued quantity. "
                    + "Net issued: " + issuedNet + ", returning: " + quantity);
        }

        LocalDateTime firstIssueTime = req.getApprovedAt();
        if (firstIssueTime == null) {
            firstIssueTime = req.getCreatedAt();
        }
        if (LocalDateTime.now().isAfter(firstIssueTime.plusDays(7))) {
            throw new RuntimeException("Return window expired. Returns must be made within 7 days of approval.");
        }

        inventoryService.returnStock(req.getSkuId(), quantity);

        int newReturned = req.getReturnedQuantity() + quantity;
        req.setReturnedQuantity(newReturned);

        if (req.getStatus() == Requisition.Status.FULFILLED
                && newReturned < req.getQuantity()) {
            req.setStatus(Requisition.Status.PARTIALLY_ISSUED);
        }

        Requisition saved = requisitionRepository.save(req);

        Sku sku = skuService.getById(req.getSkuId());
        auditService.log(
                AuditLog.Action.STOCK_RETURNED,
                saved.getId(),
                operator,
                "Returned " + quantity + " units for SKU " + sku.getSkuCode()
                        + ". Total returned: " + newReturned + ", net issued: "
                        + (req.getIssuedQuantity() - newReturned)
        );

        return saved;
    }

    @Transactional
    public Requisition close(Long id, String operator) {
        Requisition req = getById(id);
        if (req.getStatus() == Requisition.Status.CLOSED
                || req.getStatus() == Requisition.Status.REJECTED
                || req.getStatus() == Requisition.Status.FULFILLED) {
            throw new RuntimeException("Requisition cannot be closed. Current status: " + req.getStatus());
        }

        int remainingReserved = req.getQuantity() - req.getIssuedQuantity();
        if (remainingReserved > 0) {
            inventoryService.releaseReservedStock(req.getSkuId(), remainingReserved);
        }

        req.setStatus(Requisition.Status.CLOSED);
        Requisition saved = requisitionRepository.save(req);

        Sku sku = skuService.getById(req.getSkuId());
        auditService.log(
                AuditLog.Action.REQUISITION_CLOSED,
                saved.getId(),
                operator,
                "Closed requisition for SKU " + sku.getSkuCode()
                        + ". Released " + remainingReserved + " unissued reserved units."
        );

        if (remainingReserved > 0) {
            auditService.log(
                    AuditLog.Action.STOCK_RELEASED,
                    saved.getId(),
                    "system",
                    "Released " + remainingReserved + " reserved units for SKU " + sku.getSkuCode()
                            + " due to requisition closure"
            );
        }

        return saved;
    }
}
