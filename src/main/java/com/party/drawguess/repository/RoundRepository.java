package com.party.drawguess.repository;

import com.party.drawguess.model.Round;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RoundRepository extends JpaRepository<Round, Long> {
    List<Round> findByGameIdOrderByRoundNumberAsc(Long gameId);
    Optional<Round> findByGameIdAndRoundNumber(Long gameId, Integer roundNumber);
    Optional<Round> findByGameIdAndCompletedFalse(Long gameId);
}
