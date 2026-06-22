package com.meetingroom.controller;

import com.meetingroom.dto.ApiResponse;
import com.meetingroom.dto.CreateMeetingRoomRequest;
import com.meetingroom.dto.MeetingRoomResponse;
import com.meetingroom.dto.UpdateMeetingRoomRequest;
import com.meetingroom.service.MeetingRoomService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/meeting-rooms")
@RequiredArgsConstructor
public class MeetingRoomController {

    private final MeetingRoomService meetingRoomService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<MeetingRoomResponse>>> getAll(
            @RequestParam(required = false) Integer floor,
            @RequestParam(required = false) Integer minCapacity) {
        List<MeetingRoomResponse> rooms = meetingRoomService.findByFilters(floor, minCapacity);
        return ResponseEntity.ok(ApiResponse.success(rooms));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<MeetingRoomResponse>> getById(@PathVariable Long id) {
        MeetingRoomResponse room = meetingRoomService.findById(id);
        return ResponseEntity.ok(ApiResponse.success(room));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<MeetingRoomResponse>> create(
            @Valid @RequestBody CreateMeetingRoomRequest request) {
        MeetingRoomResponse room = meetingRoomService.create(request);
        return ResponseEntity.ok(ApiResponse.success(room));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<MeetingRoomResponse>> update(
            @PathVariable Long id,
            @Valid @RequestBody UpdateMeetingRoomRequest request) {
        MeetingRoomResponse room = meetingRoomService.update(id, request);
        return ResponseEntity.ok(ApiResponse.success(room));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long id) {
        meetingRoomService.delete(id);
        return ResponseEntity.ok(ApiResponse.success());
    }
}
