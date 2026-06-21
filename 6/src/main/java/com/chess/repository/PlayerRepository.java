package com.chess.repository;

import com.chess.entity.Player;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface PlayerRepository extends JpaRepository<Player, Long> {

    Optional<Player> findByPlayerId(String playerId);

    boolean existsByPlayerId(String playerId);

    @Query("SELECT p FROM Player p ORDER BY p.eloRating DESC, p.wins DESC")
    Page<Player> findLeaderboard(Pageable pageable);
}
