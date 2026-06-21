package com.chess.repository;

import com.chess.entity.Match;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface MatchRepository extends JpaRepository<Match, Long> {

    List<Match> findByRedPlayerIdOrBlackPlayerId(String redPlayerId, String blackPlayerId);

    List<Match> findByStatus(Match.MatchStatus status);
}
