package com.delivery.controller;

import com.delivery.common.Result;
import com.delivery.dto.CreateRiderRequest;
import com.delivery.entity.Rider;
import com.delivery.enums.RiderStatus;
import com.delivery.exception.BusinessException;
import com.delivery.service.RiderService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/riders")
@RequiredArgsConstructor
public class RiderController {

    private final RiderService riderService;

    @PostMapping
    public Result<Rider> createRider(@Valid @RequestBody CreateRiderRequest request) {
        Rider rider = riderService.createRider(request);
        return Result.success(rider);
    }

    @GetMapping("/{id}")
    public Result<Rider> getRider(@PathVariable Long id) {
        return riderService.getRider(id)
                .map(Result::success)
                .orElseThrow(() -> new BusinessException("骑手不存在"));
    }

    @GetMapping("/no/{riderNo}")
    public Result<Rider> getRiderByNo(@PathVariable String riderNo) {
        return riderService.getRiderByNo(riderNo)
                .map(Result::success)
                .orElseThrow(() -> new BusinessException("骑手不存在"));
    }

    @GetMapping
    public Result<Page<Rider>> listRiders(
            @RequestParam(required = false) RiderStatus status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.ASC, "id"));
        Page<Rider> riders;
        if (status != null) {
            riders = riderService.listRidersByStatus(status, pageable);
        } else {
            riders = riderService.listRiders(pageable);
        }
        return Result.success(riders);
    }

    @PutMapping("/{id}/status")
    public Result<Rider> updateStatus(
            @PathVariable Long id,
            @RequestParam RiderStatus status) {
        Rider rider = riderService.updateRiderStatus(id, status);
        return Result.success(rider);
    }

    @PutMapping("/{id}/location")
    public Result<Rider> updateLocation(
            @PathVariable Long id,
            @RequestParam Double latitude,
            @RequestParam Double longitude) {
        Rider rider = riderService.updateRiderLocation(id, latitude, longitude);
        return Result.success(rider);
    }

    @GetMapping("/{id}/workload")
    public Result<Long> getWorkload(@PathVariable Long id) {
        long workload = riderService.getRiderWorkload(id);
        return Result.success(workload);
    }
}
