package com.lab.requisition.scheduler;

import com.lab.requisition.service.StockAlertService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class StockAlertScheduler {

    private final StockAlertService stockAlertService;

    @Scheduled(fixedRate = 60000)
    public void checkStockLevels() {
        try {
            stockAlertService.checkAndGenerateAlerts();
        } catch (Exception e) {
            log.error("Error in stock alert scheduler", e);
        }
    }
}
