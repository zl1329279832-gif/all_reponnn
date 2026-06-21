package com.party.drawguess.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
@Entity
@Table(name = "rounds")
public class Round {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "game_id", nullable = false)
    private Long gameId;

    @Column(name = "round_number", nullable = false)
    private Integer roundNumber;

    @Column(name = "drawer_id", nullable = false)
    private Long drawerId;

    @Column(name = "drawer_nickname", nullable = false, length = 50)
    private String drawerNickname;

    @Column(name = "target_word", nullable = false, length = 100)
    private String targetWord;

    @Column(name = "description", length = 500)
    private String description;

    @Column(name = "completed", nullable = false)
    private Boolean completed;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "round_guessers", joinColumns = @JoinColumn(name = "round_id"))
    @Column(name = "player_id")
    private List<Long> guesserIds = new ArrayList<>();

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        completed = false;
    }
}
