package com.lab.requisition.controller;

import com.lab.requisition.dto.InventoryCreateRequest;
import com.lab.requisition.entity.Inventory;
import com.lab.requisition.service.InventoryService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/inventory")
@RequiredArgsConstructor
public class InventoryController {

    private final InventoryService inventoryService;

    @GetMapping
    public ResponseEntity<Page<Inventory>> list(
            @PageableDefault(size = 20) Pageable pageable) {
        return ResponseEntity.ok(inventoryService.list(pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Inventory> getById(@PathVariable Long id) {
        return ResponseEntity.ok(inventoryService.getById(id));
    }

    @GetMapping("/sku/{skuId}")
    public ResponseEntity<List<Inventory>> getBySkuId(@PathVariable Long skuId) {
        return ResponseEntity.ok(inventoryService.getBySkuId(skuId));
    }

    @GetMapping("/sku/{skuId}/total")
    public ResponseEntity<Map<String, Integer>> getTotalStock(@PathVariable Long skuId) {
        Integer available = inventoryService.getAvailableStock(skuId);
        Integer reserved = inventoryService.getReservedStock(skuId);
        Integer total = inventoryService.getTotalStock(skuId);
        return ResponseEntity.ok(Map.of(
                "availableStock", available,
                "reservedStock", reserved,
                "totalStock", total
        ));
    }

    @PostMapping
    public ResponseEntity<Inventory> create(@Valid @RequestBody InventoryCreateRequest request) {
        return ResponseEntity.ok(inventoryService.create(request));
    }

    @PutMapping("/{id}")
    public ResponseEntity<Inventory> update(@PathVariable Long id,
                                            @RequestBody Map<String, Integer> body) {
        Integer quantity = body.get("quantity");
        if (quantity == null) {
            throw new RuntimeException("quantity is required");
        }
        return ResponseEntity.ok(inventoryService.update(id, quantity));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        inventoryService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
