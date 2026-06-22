package com.delivery.dto;

import com.delivery.enums.RiderStatus;
import lombok.Data;

@Data
public class RiderWorkloadDTO {

    private Long riderId;
    private String riderNo;
    private String riderName;
    private RiderStatus status;
    private Integer currentOrderCount;
    private Integer totalOrderCount;
    private String gridCode;
    private Double latitude;
    private Double longitude;
}
