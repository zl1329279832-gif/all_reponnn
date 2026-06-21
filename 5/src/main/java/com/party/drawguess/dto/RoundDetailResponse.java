package com.party.drawguess.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class RoundDetailResponse {
    private Long roundId;
    private Integer roundNumber;
    private Long drawerId;
    private String drawerNickname;
    private String targetWord;
    private String description;
    private Boolean completed;
    private LocalDateTime createdAt;
    private LocalDateTime completedAt;
    private List<SubmissionDetailResponse> submissions;
}
