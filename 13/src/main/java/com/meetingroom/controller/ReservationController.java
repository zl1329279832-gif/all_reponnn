package com.meetingroom.controller;

import com.meetingroom.dto.ApiResponse;
import com.meetingroom.dto.CreateReservationRequest;
import com.meetingroom.dto.ReservationResponse;
import com.meetingroom.service.ReservationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/reservations")
@RequiredArgsConstructor
public class ReservationController {

    private final ReservationService reservationService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<ReservationResponse>>> getAll(
            @RequestParam(required = false) Long roomId,
            @RequestParam(required = false) Integer floor,
            @RequestParam(required = false) Integer minCapacity,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        List<ReservationResponse> reservations = reservationService.findByFilters(
                roomId, floor, minCapacity, startDate, endDate);
        return ResponseEntity.ok(ApiResponse.success(reservations));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<ReservationResponse>> getById(@PathVariable Long id) {
        ReservationResponse reservation = reservationService.findById(id);
        return ResponseEntity.ok(ApiResponse.success(reservation));
    }

    @GetMapping("/series/{seriesId}")
    public ResponseEntity<ApiResponse<List<ReservationResponse>>> getBySeriesId(
            @PathVariable String seriesId) {
        List<ReservationResponse> reservations = reservationService.findBySeriesId(seriesId);
        return ResponseEntity.ok(ApiResponse.success(reservations));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<List<ReservationResponse>>> create(
            @Valid @RequestBody CreateReservationRequest request) {
        List<ReservationResponse> reservations = reservationService.create(request);
        return ResponseEntity.ok(ApiResponse.success(reservations));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> cancelSingle(@PathVariable Long id) {
        reservationService.cancelSingle(id);
        return ResponseEntity.ok(ApiResponse.success());
    }

    @DeleteMapping("/series/{seriesId}")
    public ResponseEntity<ApiResponse<Void>> cancelSeries(@PathVariable String seriesId) {
        reservationService.cancelSeries(seriesId);
        return ResponseEntity.ok(ApiResponse.success());
    }
}
