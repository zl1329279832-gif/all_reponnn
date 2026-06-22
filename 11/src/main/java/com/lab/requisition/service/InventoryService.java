package com.lab.requisition.service;

import com.lab.requisition.dto.InventoryCreateRequest;
import com.lab.requisition.entity.Inventory;
import com.lab.requisition.repository.InventoryRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class InventoryService {

    private final InventoryRepository inventoryRepository;

    @Transactional(readOnly = true)
    public Page<Inventory> list(Pageable pageable) {
        return inventoryRepository.findAll(pageable);
    }

    @Transactional(readOnly = true)
    public Inventory getById(Long id) {
        return inventoryRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Inventory not found: " + id));
    }

    @Transactional(readOnly = true)
    public List<Inventory> getBySkuId(Long skuId) {
        return inventoryRepository.findBySkuId(skuId);
    }

    @Transactional(readOnly = true)
    public Integer getTotalStock(Long skuId) {
        return inventoryRepository.sumQuantityBySkuId(skuId);
    }

    @Transactional
    public Inventory create(InventoryCreateRequest request) {
        if (inventoryRepository.findBySkuIdAndLocation(
                request.getSkuId(), request.getLocation()).isPresent()) {
            throw new RuntimeException("Inventory already exists for SKU "
                    + request.getSkuId() + " at location " + request.getLocation());
        }
        Inventory inv = new Inventory();
        inv.setSkuId(request.getSkuId());
        inv.setLocation(request.getLocation());
        inv.setQuantity(request.getQuantity());
        return inventoryRepository.save(inv);
    }

    @Transactional
    public Inventory update(Long id, Integer quantity) {
        Inventory inv = getById(id);
        inv.setQuantity(quantity);
        return inventoryRepository.save(inv);
    }

    @Transactional
    public void deductStock(Long skuId, int quantity, String location) {
        Inventory inv = inventoryRepository.findBySkuIdAndLocation(skuId, location)
                .orElseThrow(() -> new RuntimeException(
                        "Inventory not found for SKU " + skuId + " at " + location));

        if (inv.getQuantity() < quantity) {
            throw new RuntimeException("Insufficient stock. Available: "
                    + inv.getQuantity() + ", requested: " + quantity);
        }

        inv.setQuantity(inv.getQuantity() - quantity);
        inventoryRepository.save(inv);
    }

    @Transactional
    public void deductStockFromAnyLocation(Long skuId, int quantity) {
        List<Inventory> inventories = inventoryRepository.findBySkuId(skuId);
        int remaining = quantity;

        for (Inventory inv : inventories) {
            if (remaining <= 0) break;
            int deduct = Math.min(inv.getQuantity(), remaining);
            if (deduct > 0) {
                inv.setQuantity(inv.getQuantity() - deduct);
                inventoryRepository.save(inv);
                remaining -= deduct;
            }
        }

        if (remaining > 0) {
            throw new RuntimeException("Insufficient total stock for SKU "
                    + skuId + ". Short by " + remaining);
        }
    }

    @Transactional
    public void restoreStock(Long skuId, int quantity, String location) {
        Inventory inv = inventoryRepository.findBySkuIdAndLocation(skuId, location)
                .orElseThrow(() -> new RuntimeException(
                        "Inventory not found for SKU " + skuId + " at " + location));
        inv.setQuantity(inv.getQuantity() + quantity);
        inventoryRepository.save(inv);
    }

    @Transactional
    public void restoreStockToFirstLocation(Long skuId, int quantity) {
        List<Inventory> inventories = inventoryRepository.findBySkuId(skuId);
        if (inventories.isEmpty()) {
            throw new RuntimeException("No inventory found for SKU: " + skuId);
        }
        Inventory inv = inventories.get(0);
        inv.setQuantity(inv.getQuantity() + quantity);
        inventoryRepository.save(inv);
    }

    @Transactional
    public void delete(Long id) {
        if (!inventoryRepository.existsById(id)) {
            throw new RuntimeException("Inventory not found: " + id);
        }
        inventoryRepository.deleteById(id);
    }
}
