package com.party.drawguess.controller;

import com.party.drawguess.dto.*;
import com.party.drawguess.service.RoomService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/rooms")
@RequiredArgsConstructor
public class RoomController {
    private final RoomService roomService;

    @PostMapping("/create")
    public ApiResponse<RoomSnapshotResponse> createRoom(@Valid @RequestBody CreateRoomRequest request) {
        return ApiResponse.success(roomService.createRoom(request));
    }

    @PostMapping("/join")
    public ApiResponse<RoomSnapshotResponse> joinRoom(@Valid @RequestBody JoinRoomRequest request) {
        return ApiResponse.success(roomService.joinRoom(request));
    }

    @PostMapping("/ready")
    public ApiResponse<RoomSnapshotResponse> ready(@Valid @RequestBody ReadyRequest request) {
        return ApiResponse.success(roomService.ready(request));
    }

    @PostMapping("/start")
    public ApiResponse<RoomSnapshotResponse> startGame(@Valid @RequestBody StartGameRequest request) {
        return ApiResponse.success(roomService.startGame(request));
    }

    @GetMapping("/{roomId}/snapshot")
    public ApiResponse<RoomSnapshotResponse> getRoomSnapshot(@PathVariable Long roomId) {
        return ApiResponse.success(roomService.getRoomSnapshot(roomId));
    }
}
