package com.delivery.dto;

import lombok.Data;

@Data
public class MarkExceptionRequest {

    private String orderNo;

    private String reason;

    private String requestId;

    private Double latitude;

    private Double longitude;

    private String operator;
}
