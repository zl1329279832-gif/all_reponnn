package com.chess.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.time.LocalDateTime;

@Entity
@Table(name = "players")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Player {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false, length = 64)
    private String playerId;

    @Column(nullable = false, length = 64)
    private String name;

    @Column(nullable = false)
    private Integer eloRating;

    @Column(nullable = false)
    private Integer wins;

    @Column(nullable = false)
    private Integer losses;

    @Column(nullable = false)
    private Integer draws;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
        if (eloRating == null) {
            eloRating = 1500;
        }
        if (wins == null) {
            wins = 0;
        }
        if (losses == null) {
            losses = 0;
        }
        if (draws == null) {
            draws = 0;
        }
    }
}
