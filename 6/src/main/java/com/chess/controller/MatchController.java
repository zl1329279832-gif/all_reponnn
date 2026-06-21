package com.chess.controller;

import com.chess.dto.*;
import com.chess.service.MatchService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/matches")
@RequiredArgsConstructor
public class MatchController {

    private final MatchService matchService;

    @PostMapping
    public ApiResponse<MatchDto> createMatch(@Valid @RequestBody CreateMatchRequest request) {
        return matchService.createMatch(request);
    }

    @PostMapping("/{matchId}/moves")
    public ApiResponse<MoveDto> makeMove(
            @PathVariable Long matchId,
            @Valid @RequestBody MakeMoveRequest request
    ) {
        return matchService.makeMove(matchId, request);
    }

    @GetMapping("/{matchId}")
    public ApiResponse<MatchDto> getMatch(@PathVariable Long matchId) {
        return matchService.getMatch(matchId);
    }

    @GetMapping("/{matchId}/moves")
    public ApiResponse<List<MoveDto>> getMatchMoves(@PathVariable Long matchId) {
        return matchService.getMatchMoves(matchId);
    }

    @GetMapping("/{matchId}/snapshot")
    public ApiResponse<Map<String, Object>> getMatchSnapshot(@PathVariable Long matchId) {
        return matchService.getMatchSnapshot(matchId);
    }

    @GetMapping("/{matchId}/fen")
    public ApiResponse<Map<String, Object>> getMatchFen(@PathVariable Long matchId) {
        return matchService.getMatchSnapshot(matchId);
    }
}
