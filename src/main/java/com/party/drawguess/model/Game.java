package com.party.drawguess.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Data
@Entity
@Table(name = "games")
public class Game {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "room_id", nullable = false)
    private Long roomId;

    @Column(name = "room_code", nullable = false, length = 8)
    private String roomCode;

    @Column(name = "total_rounds", nullable = false)
    private Integer totalRounds;

    @Column(name = "completed_rounds", nullable = false)
    private Integer completedRounds;

    @Column(name = "winner_id")
    private Long winnerId;

    @Column(name = "winner_nickname", length = 50)
    private String winnerNickname;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "game_scores", joinColumns = @JoinColumn(name = "game_id"))
    @MapKeyColumn(name = "player_id")
    @Column(name = "score")
    private Map<Long, Integer> scores = new HashMap<>();

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "game_players", joinColumns = @JoinColumn(name = "game_id"))
    @MapKeyColumn(name = "player_id")
    @Column(name = "nickname")
    private Map<Long, String> playerNicknames = new HashMap<>();

    @Column(name = "started_at", nullable = false)
    private LocalDateTime startedAt;

    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    @PrePersist
    protected void onCreate() {
        startedAt = LocalDateTime.now();
        completedRounds = 0;
    }
}
