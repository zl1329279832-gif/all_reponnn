package com.chess.controller;

import com.chess.dto.ApiResponse;
import com.chess.dto.PlayerDto;
import com.chess.service.PlayerService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/players")
@RequiredArgsConstructor
public class PlayerController {

    private final PlayerService playerService;

    @GetMapping("/{playerId}")
    public ApiResponse<PlayerDto> getPlayer(@PathVariable String playerId) {
        PlayerDto dto = playerService.getPlayerDto(playerId);
        if (dto == null) {
            return ApiResponse.notFound("玩家不存在");
        }
        return ApiResponse.success(dto);
    }

    @GetMapping("/leaderboard")
    public ApiResponse<Page<PlayerDto>> getLeaderboard(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        if (page < 0) page = 0;
        if (size <= 0 || size > 100) size = 20;
        Page<PlayerDto> leaderboard = playerService.getLeaderboard(page, size);
        return ApiResponse.success(leaderboard);
    }
}
