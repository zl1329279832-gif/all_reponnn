package com.lab.requisition.controller;

import com.lab.requisition.dto.SkuCreateRequest;
import com.lab.requisition.entity.Sku;
import com.lab.requisition.service.SkuService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/skus")
@RequiredArgsConstructor
public class SkuController {

    private final SkuService skuService;

    @GetMapping
    public ResponseEntity<Page<Sku>> list(
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String lab,
            @PageableDefault(size = 20) Pageable pageable) {
        return ResponseEntity.ok(skuService.list(category, lab, pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Sku> getById(@PathVariable Long id) {
        return ResponseEntity.ok(skuService.getById(id));
    }

    @GetMapping("/code/{skuCode}")
    public ResponseEntity<Sku> getBySkuCode(@PathVariable String skuCode) {
        return ResponseEntity.ok(skuService.getBySkuCode(skuCode));
    }

    @PostMapping
    public ResponseEntity<Sku> create(@Valid @RequestBody SkuCreateRequest request) {
        return ResponseEntity.ok(skuService.create(request));
    }

    @PutMapping("/{id}")
    public ResponseEntity<Sku> update(@PathVariable Long id,
                                       @Valid @RequestBody SkuCreateRequest request) {
        return ResponseEntity.ok(skuService.update(id, request));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        skuService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
