package com.party.drawguess.repository;

import com.party.drawguess.model.Player;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface PlayerRepository extends JpaRepository<Player, Long> {
    Optional<Player> findByOpenId(String openId);
    boolean existsByOpenId(String openId);
}
