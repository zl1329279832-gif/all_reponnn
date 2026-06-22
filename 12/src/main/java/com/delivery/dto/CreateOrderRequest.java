package com.delivery.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class CreateOrderRequest {

    @NotBlank(message = "商家名称不能为空")
    private String merchantName;

    @NotBlank(message = "取货地址不能为空")
    private String pickupAddress;

    private Double pickupLatitude;

    private Double pickupLongitude;

    @NotBlank(message = "收货地址不能为空")
    private String deliveryAddress;

    private Double deliveryLatitude;

    private Double deliveryLongitude;

    private String receiverName;

    private String receiverPhone;

    private BigDecimal orderAmount;

    private BigDecimal deliveryFee;

    private String remark;
}
