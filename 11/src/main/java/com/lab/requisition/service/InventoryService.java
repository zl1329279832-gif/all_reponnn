package com.lab.requisition.service;

import com.lab.requisition.dto.InventoryCreateRequest;
import com.lab.requisition.entity.Inventory;
import com.lab.requisition.repository.InventoryRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
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
    public Integer getAvailableStock(Long skuId) {
        return inventoryRepository.sumQuantityBySkuId(skuId);
    }

    @Transactional(readOnly = true)
    public Integer getReservedStock(Long skuId) {
        return inventoryRepository.sumReservedQuantityBySkuId(skuId);
    }

    @Transactional(readOnly = true)
    public Integer getTotalStock(Long skuId) {
        return getAvailableStock(skuId) + getReservedStock(skuId);
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
        inv.setReservedQuantity(0);
        return inventoryRepository.save(inv);
    }

    @Transactional
    public Inventory update(Long id, Integer quantity) {
        Inventory inv = getById(id);
        inv.setQuantity(quantity);
        return inventoryRepository.save(inv);
    }

    @Transactional
    public void reserveStock(Long skuId, int quantity) {
        List<Inventory> inventories = inventoryRepository.findBySkuId(skuId);
        int remaining = quantity;

        for (Inventory inv : inventories) {
            if (remaining <= 0) break;
            int reserve = Math.min(inv.getQuantity(), remaining);
            if (reserve > 0) {
                inv.setQuantity(inv.getQuantity() - reserve);
                inv.setReservedQuantity(inv.getReservedQuantity() + reserve);
                inventoryRepository.save(inv);
                remaining -= reserve;
            }
        }

        if (remaining > 0) {
            throw new RuntimeException("Insufficient available stock for SKU "
                    + skuId + ". Available: " + (quantity - remaining) + ", requested: " + quantity);
        }
    }

    @Transactional
    public void releaseReservedStock(Long skuId, int quantity) {
        List<Inventory> inventories = inventoryRepository.findBySkuId(skuId);
        int remaining = quantity;

        for (Inventory inv : inventories) {
            if (remaining <= 0) break;
            int release = Math.min(inv.getReservedQuantity(), remaining);
            if (release > 0) {
                inv.setReservedQuantity(inv.getReservedQuantity() - release);
                inv.setQuantity(inv.getQuantity() + release);
                inventoryRepository.save(inv);
                remaining -= release;
            }
        }

        if (remaining > 0) {
            throw new RuntimeException("Insufficient reserved stock for SKU "
                    + skuId + ". Reserved: " + (quantity - remaining) + ", trying to release: " + quantity);
        }
    }

    @Transactional
    public void issueStock(Long skuId, int quantity) {
        List<Inventory> inventories = inventoryRepository.findBySkuId(skuId);
        int remaining = quantity;

        for (Inventory inv : inventories) {
            if (remaining <= 0) break;
            int issue = Math.min(inv.getReservedQuantity(), remaining);
            if (issue > 0) {
                inv.setReservedQuantity(inv.getReservedQuantity() - issue);
                inventoryRepository.save(inv);
                remaining -= issue;
            }
        }

        if (remaining > 0) {
            throw new RuntimeException("Insufficient reserved stock for SKU "
                    + skuId + ". Reserved: " + (quantity - remaining) + ", trying to issue: " + quantity);
        }
    }

    @Transactional
    public void returnStock(Long skuId, int quantity) {
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
