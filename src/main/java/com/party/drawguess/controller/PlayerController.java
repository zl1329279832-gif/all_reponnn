package com.party.drawguess.controller;

import com.party.drawguess.dto.ApiResponse;
import com.party.drawguess.dto.PlayerResponse;
import com.party.drawguess.dto.RegisterRequest;
import com.party.drawguess.service.PlayerService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/players")
@RequiredArgsConstructor
public class PlayerController {
    private final PlayerService playerService;

    @PostMapping("/register")
    public ApiResponse<PlayerResponse> register(@Valid @RequestBody RegisterRequest request) {
        return ApiResponse.success(playerService.register(request));
    }
}
