package com.chess.service;

import com.chess.entity.Player;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class EloService {

    private static final int K_FACTOR = 32;

    private final PlayerService playerService;

    @Transactional
    public void updateRatings(String redPlayerId, String blackPlayerId, String winnerPlayerId) {
        Player red = playerService.getPlayer(redPlayerId);
        Player black = playerService.getPlayer(blackPlayerId);

        if (red == null || black == null) {
            return;
        }

        double redExpected = calculateExpected(red.getEloRating(), black.getEloRating());
        double blackExpected = calculateExpected(black.getEloRating(), red.getEloRating());

        double redActual;
        double blackActual;

        if (winnerPlayerId == null) {
            redActual = 0.5;
            blackActual = 0.5;
            red.setDraws(red.getDraws() + 1);
            black.setDraws(black.getDraws() + 1);
        } else if (winnerPlayerId.equals(redPlayerId)) {
            redActual = 1.0;
            blackActual = 0.0;
            red.setWins(red.getWins() + 1);
            black.setLosses(black.getLosses() + 1);
        } else {
            redActual = 0.0;
            blackActual = 1.0;
            red.setLosses(red.getLosses() + 1);
            black.setWins(black.getWins() + 1);
        }

        int newRedRating = (int) Math.round(red.getEloRating() + K_FACTOR * (redActual - redExpected));
        int newBlackRating = (int) Math.round(black.getEloRating() + K_FACTOR * (blackActual - blackExpected));

        red.setEloRating(newRedRating);
        black.setEloRating(newBlackRating);

        playerService.save(red);
        playerService.save(black);
    }

    private double calculateExpected(int ratingA, int ratingB) {
        return 1.0 / (1.0 + Math.pow(10.0, (ratingB - ratingA) / 400.0));
    }
}
