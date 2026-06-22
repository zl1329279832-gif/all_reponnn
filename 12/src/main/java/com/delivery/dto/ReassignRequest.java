package com.delivery.dto;

import lombok.Data;

@Data
public class ReassignRequest {

    private String orderNo;

    private Long targetRiderId;

    private String reason;

    private String operator;
}
