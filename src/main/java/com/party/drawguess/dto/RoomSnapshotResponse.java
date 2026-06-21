package com.party.drawguess.dto;

import com.party.drawguess.model.RoomStatus;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class RoomSnapshotResponse {
    private Long roomId;
    private String roomCode;
    private String roomName;
    private Boolean hasPassword;
    private Integer maxPlayers;
    private Integer totalRounds;
    private RoomStatus status;
    private Long ownerId;
    private String ownerNickname;
    private Integer currentRound;
    private Long currentGameId;
    private List<PlayerInfo> players;
    private List<Long> readyPlayerIds;
    private Map<Long, Integer> currentScores;
    private RoundInfo currentRoundInfo;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PlayerInfo {
        private Long id;
        private String nickname;
        private Boolean isOwner;
        private Boolean isReady;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RoundInfo {
        private Long roundId;
        private Integer roundNumber;
        private Long drawerId;
        private String drawerNickname;
        private String description;
        private List<SubmissionInfo> submissions;
        private Boolean completed;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SubmissionInfo {
        private Long playerId;
        private String playerNickname;
        private String submissionType;
        private String content;
        private Boolean isCorrect;
        private Integer scoreEarned;
    }
}
