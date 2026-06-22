package com.lab.requisition.controller;

import com.lab.requisition.entity.StockAlert;
import com.lab.requisition.service.StockAlertService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/stock-alerts")
@RequiredArgsConstructor
public class StockAlertController {

    private final StockAlertService stockAlertService;

    @GetMapping
    public ResponseEntity<Page<StockAlert>> list(
            @RequestParam(required = false) String lab,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) StockAlert.AlertStatus status,
            @PageableDefault(size = 20) Pageable pageable) {
        return ResponseEntity.ok(stockAlertService.list(lab, category, status, pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<StockAlert> getById(@PathVariable Long id) {
        return ResponseEntity.ok(stockAlertService.getById(id));
    }

    @PostMapping("/{id}/resolve")
    public ResponseEntity<StockAlert> resolve(@PathVariable Long id) {
        return ResponseEntity.ok(stockAlertService.resolve(id));
    }

    @PostMapping("/scan")
    public ResponseEntity<Void> triggerScan() {
        stockAlertService.checkAndGenerateAlerts();
        return ResponseEntity.noContent().build();
    }
}
