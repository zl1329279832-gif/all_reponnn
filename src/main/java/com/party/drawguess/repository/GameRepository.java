package com.party.drawguess.repository;

import com.party.drawguess.model.Game;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface GameRepository extends JpaRepository<Game, Long> {
    List<Game> findByRoomIdOrderByStartedAtDesc(Long roomId);
    Optional<Game> findByIdAndRoomId(Long id, Long roomId);

    @Query("SELECT g FROM Game g JOIN g.playerNicknames p WHERE KEY(p) = :playerId ORDER BY g.startedAt DESC")
    Page<Game> findByPlayerId(@Param("playerId") Long playerId, Pageable pageable);
}
