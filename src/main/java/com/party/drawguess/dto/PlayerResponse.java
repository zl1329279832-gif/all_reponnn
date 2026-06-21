package com.party.drawguess.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class PlayerResponse {
    private Long id;
    private String openId;
    private String nickname;
}
