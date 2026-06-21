package com.chess.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.time.LocalDateTime;

@Entity
@Table(name = "moves")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Move {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long matchId;

    @Column(nullable = false)
    private Integer moveNumber;

    @Column(nullable = false, length = 64)
    private String playerId;

    @Column(nullable = false)
    private Integer fromRow;

    @Column(nullable = false)
    private Integer fromCol;

    @Column(nullable = false)
    private Integer toRow;

    @Column(nullable = false)
    private Integer toCol;

    @Column(length = 8)
    private String pieceType;

    @Column(length = 16)
    private String capturedPieceType;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String boardSnapshotAfter;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
    }
}
