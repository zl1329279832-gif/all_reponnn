package com.party.drawguess.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
@Entity
@Table(name = "rooms")
public class Room {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "room_code", unique = true, nullable = false, length = 8)
    private String roomCode;

    @Column(name = "room_name", nullable = false, length = 100)
    private String roomName;

    @Column(length = 50)
    private String password;

    @Column(name = "max_players", nullable = false)
    private Integer maxPlayers;

    @Column(name = "total_rounds", nullable = false)
    private Integer totalRounds;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private RoomStatus status;

    @Column(name = "owner_id", nullable = false)
    private Long ownerId;

    @Column(name = "current_round")
    private Integer currentRound;

    @Column(name = "current_game_id")
    private Long currentGameId;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @Version
    @Column(name = "version", nullable = false)
    private Long version;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "room_players", joinColumns = @JoinColumn(name = "room_id"))
    @Column(name = "player_id")
    private List<Long> playerIds = new ArrayList<>();

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "room_ready_players", joinColumns = @JoinColumn(name = "room_id"))
    @Column(name = "player_id")
    private List<Long> readyPlayerIds = new ArrayList<>();

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
        status = RoomStatus.WAITING;
        currentRound = 0;
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
