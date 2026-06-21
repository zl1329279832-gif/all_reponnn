package com.party.drawguess.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "round_submissions", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"round_id", "player_id", "submission_type"})
})
public class RoundSubmission {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "round_id", nullable = false)
    private Long roundId;

    @Column(name = "game_id", nullable = false)
    private Long gameId;

    @Column(name = "player_id", nullable = false)
    private Long playerId;

    @Column(name = "player_nickname", nullable = false, length = 50)
    private String playerNickname;

    @Enumerated(EnumType.STRING)
    @Column(name = "submission_type", nullable = false, length = 20)
    private SubmissionType submissionType;

    @Column(nullable = false, length = 500)
    private String content;

    @Column(name = "is_correct")
    private Boolean isCorrect;

    @Column(name = "score_earned", nullable = false)
    private Integer scoreEarned;

    @Column(name = "submitted_at", nullable = false)
    private LocalDateTime submittedAt;

    public enum SubmissionType {
        DESCRIPTION,
        GUESS
    }

    @PrePersist
    protected void onCreate() {
        submittedAt = LocalDateTime.now();
    }
}
