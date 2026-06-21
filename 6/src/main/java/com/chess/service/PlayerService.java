package com.chess.service;

import com.chess.dto.PlayerDto;
import com.chess.entity.Player;
import com.chess.repository.PlayerRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

@Service
@RequiredArgsConstructor
public class PlayerService {

    private final PlayerRepository playerRepository;

    @Transactional
    public Player getOrCreatePlayer(String playerId, String name) {
        Optional<Player> existing = playerRepository.findByPlayerId(playerId);
        if (existing.isPresent()) {
            Player player = existing.get();
            if (name != null && !name.isEmpty() && !name.equals(player.getName())) {
                player.setName(name);
                return playerRepository.save(player);
            }
            return player.get();
        }
        Player player = Player.builder()
                .playerId(playerId)
                .name(name != null && !name.isEmpty() ? name : playerId)
                .eloRating(1500)
                .wins(0)
                .losses(0)
                .draws(0)
                .build();
        return playerRepository.save(player);
    }

    public Player getPlayer(String playerId) {
        return playerRepository.findByPlayerId(playerId).orElse(null);
    }

    public PlayerDto getPlayerDto(String playerId) {
        Player player = getPlayer(playerId);
        if (player == null) {
            return null;
        }
        return toDto(player, null);
    }

    public Page<PlayerDto> getLeaderboard(int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        Page<Player> playerPage = playerRepository.findLeaderboard(pageable);
        final int startRank = (int) pageable.getOffset() + 1;
        return playerPage.map(p -> toDto(p, startRank + playerPage.getContent().indexOf(p)));
    }

    public PlayerDto toDto(Player player, Integer rank) {
        return PlayerDto.builder()
                .id(player.getId())
                .playerId(player.getPlayerId())
                .name(player.getName())
                .eloRating(player.getEloRating())
                .wins(player.getWins())
                .losses(player.getLosses())
                .draws(player.getDraws())
                .rank(rank)
                .createdAt(player.getCreatedAt())
                .build();
    }

    @Transactional
    public Player save(Player player) {
        return playerRepository.save(player);
    }
}
