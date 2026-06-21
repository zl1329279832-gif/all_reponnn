package com.chess.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.time.LocalDateTime;

@Entity
@Table(name = "matches")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Match {

    public enum MatchStatus {
        IN_PROGRESS,
        RED_WIN,
        BLACK_WIN,
        DRAW
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 64)
    private String redPlayerId;

    @Column(nullable = false, length = 64)
    private String blackPlayerId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private MatchStatus status;

    @Column(nullable = false)
    private Integer currentTurn;

    @Column(nullable = false, length = 64)
    private String nextTurnPlayerId;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String boardSnapshot;

    @Version
    private Long version;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    private LocalDateTime endedAt;

    private String winnerPlayerId;

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
        if (status == null) {
            status = MatchStatus.IN_PROGRESS;
        }
        if (currentTurn == null) {
            currentTurn = 0;
        }
    }
}
