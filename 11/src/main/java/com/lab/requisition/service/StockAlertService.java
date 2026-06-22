package com.lab.requisition.service;

import com.lab.requisition.entity.Sku;
import com.lab.requisition.entity.StockAlert;
import com.lab.requisition.repository.StockAlertRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class StockAlertService {

    private final StockAlertRepository stockAlertRepository;
    private final SkuService skuService;
    private final InventoryService inventoryService;

    @Transactional(readOnly = true)
    public Page<StockAlert> list(String lab, String category, StockAlert.AlertStatus status, Pageable pageable) {
        return stockAlertRepository.findByFilters(lab, category, status, pageable);
    }

    @Transactional(readOnly = true)
    public StockAlert getById(Long id) {
        return stockAlertRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Stock alert not found: " + id));
    }

    @Transactional
    public void checkAndGenerateAlerts() {
        List<Sku> skus = skuService.findAllWithSafetyStock();

        for (Sku sku : skus) {
            if (sku.getSafetyStock() == null || sku.getSafetyStock() <= 0) {
                continue;
            }

            Integer totalStock = inventoryService.getTotalStock(sku.getId());
            if (totalStock == null) {
                totalStock = 0;
            }

            if (totalStock < sku.getSafetyStock()) {
                Optional<StockAlert> existingActive = stockAlertRepository.findLatestActiveBySkuId(sku.getId());
                if (existingActive.isPresent()) {
                    continue;
                }

                StockAlert alert = new StockAlert();
                alert.setSkuId(sku.getId());
                alert.setSkuCode(sku.getSkuCode());
                alert.setSkuName(sku.getName());
                alert.setCategory(sku.getCategory());
                alert.setLab(sku.getLab());
                alert.setCurrentStock(totalStock);
                alert.setSafetyStock(sku.getSafetyStock());

                double ratio = (double) totalStock / sku.getSafetyStock();
                if (ratio <= 0.3) {
                    alert.setAlertLevel(StockAlert.AlertLevel.CRITICAL);
                } else {
                    alert.setAlertLevel(StockAlert.AlertLevel.WARNING);
                }

                alert.setStatus(StockAlert.AlertStatus.ACTIVE);
                stockAlertRepository.save(alert);
            } else {
                Optional<StockAlert> existingActive = stockAlertRepository.findLatestActiveBySkuId(sku.getId());
                if (existingActive.isPresent()) {
                    StockAlert alert = existingActive.get();
                    alert.setStatus(StockAlert.AlertStatus.RESOLVED);
                    alert.setResolvedAt(LocalDateTime.now());
                    stockAlertRepository.save(alert);
                }
            }
        }
    }

    @Transactional
    public StockAlert resolve(Long id) {
        StockAlert alert = getById(id);
        alert.setStatus(StockAlert.AlertStatus.RESOLVED);
        alert.setResolvedAt(LocalDateTime.now());
        return stockAlertRepository.save(alert);
    }
}
