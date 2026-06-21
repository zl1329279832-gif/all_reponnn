package com.party.drawguess.controller;

import com.party.drawguess.dto.*;
import com.party.drawguess.service.GameService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/games")
@RequiredArgsConstructor
public class GameController {
    private final GameService gameService;

    @PostMapping("/submit-description")
    public ApiResponse<RoomSnapshotResponse> submitDescription(
            @Valid @RequestBody SubmitDescriptionRequest request) {
        return ApiResponse.success(gameService.submitDescription(request));
    }

    @PostMapping("/submit-guess")
    public ApiResponse<RoomSnapshotResponse> submitGuess(
            @Valid @RequestBody SubmitGuessRequest request) {
        return ApiResponse.success(gameService.submitGuess(request));
    }

    @GetMapping("/my")
    public ApiResponse<Page<GameHistoryResponse>> getMyGames(
            @RequestParam Long playerId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return ApiResponse.success(gameService.getMyGames(playerId, page, size));
    }

    @GetMapping("/{gameId}")
    public ApiResponse<GameHistoryResponse> getGameDetail(@PathVariable Long gameId) {
        return ApiResponse.success(gameService.getGameDetail(gameId));
    }
}
