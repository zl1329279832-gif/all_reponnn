package com.delivery.dto;

import lombok.Data;

@Data
public class RedispatchRequest {

    private String orderNo;

    private Long targetRiderId;

    private String operator;
}
