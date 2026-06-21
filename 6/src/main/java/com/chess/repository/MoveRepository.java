package com.chess.repository;

import com.chess.entity.Move;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface MoveRepository extends JpaRepository<Move, Long> {

    List<Move> findByMatchIdOrderByMoveNumberAsc(Long matchId);

    boolean existsByMatchIdAndMoveNumber(Long matchId, Integer moveNumber);
}
