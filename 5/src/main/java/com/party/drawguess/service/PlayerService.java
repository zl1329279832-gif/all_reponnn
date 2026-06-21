package com.party.drawguess.service;

import com.party.drawguess.dto.PlayerResponse;
import com.party.drawguess.dto.RegisterRequest;
import com.party.drawguess.exception.GameException;
import com.party.drawguess.model.Player;
import com.party.drawguess.repository.PlayerRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PlayerService {
    private final PlayerRepository playerRepository;

    @Transactional
    public PlayerResponse register(RegisterRequest request) {
        if (playerRepository.existsByOpenId(request.getOpenId())) {
            Player existing = playerRepository.findByOpenId(request.getOpenId()).orElseThrow();
            if (!existing.getNickname().equals(request.getNickname())) {
                existing.setNickname(request.getNickname());
                playerRepository.save(existing);
            }
            return toResponse(existing);
        }

        Player player = new Player();
        player.setOpenId(request.getOpenId());
        player.setNickname(request.getNickname());
        player = playerRepository.save(player);
        return toResponse(player);
    }

    @Transactional(readOnly = true)
    public Player getById(Long id) {
        return playerRepository.findById(id)
                .orElseThrow(() -> new GameException(404, "玩家不存在: " + id));
    }

    @Transactional(readOnly = true)
    public Player getByOpenId(String openId) {
        return playerRepository.findByOpenId(openId)
                .orElseThrow(() -> new GameException(404, "玩家不存在: " + openId));
    }

    private PlayerResponse toResponse(Player player) {
        return new PlayerResponse(player.getId(), player.getOpenId(), player.getNickname());
    }
}
