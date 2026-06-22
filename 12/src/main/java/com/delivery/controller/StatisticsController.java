package com.delivery.controller;

import com.delivery.common.Result;
import com.delivery.dto.RiderWorkloadDTO;
import com.delivery.service.StatisticsService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/statistics")
@RequiredArgsConstructor
public class StatisticsController {

    private final StatisticsService statisticsService;

    @GetMapping("/overview")
    public Result<Map<String, Object>> getOverview() {
        Map<String, Object> stats = statisticsService.getOverallStatistics();
        return Result.success(stats);
    }

    @GetMapping("/riders/workload")
    public Result<List<RiderWorkloadDTO>> getRiderWorkload() {
        List<RiderWorkloadDTO> workloadList = statisticsService.getRiderWorkloadList();
        return Result.success(workloadList);
    }

    @GetMapping("/grids")
    public Result<Map<String, Map<String, Object>>> getGridStatistics() {
        Map<String, Map<String, Object>> gridStats = statisticsService.getGridStatistics();
        return Result.success(gridStats);
    }
}
