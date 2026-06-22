package com.delivery.dto;

import lombok.Data;

@Data
public class OrderCallbackRequest {

    private String requestId;

    private String orderNo;

    private String eventType;

    private Double latitude;

    private Double longitude;

    private String description;

    private String operator;
}
