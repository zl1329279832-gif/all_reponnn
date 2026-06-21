package com.party.drawguess.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SubmissionDetailResponse {
    private Long submissionId;
    private Long playerId;
    private String playerNickname;
    private String submissionType;
    private String content;
    private Boolean isCorrect;
    private Integer scoreEarned;
    private LocalDateTime submittedAt;
}
