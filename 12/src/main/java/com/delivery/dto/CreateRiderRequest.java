package com.delivery.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateRiderRequest {

    @NotBlank(message = "骑手编号不能为空")
    private String riderNo;

    @NotBlank(message = "骑手姓名不能为空")
    private String name;

    private String phone;

    private Double latitude;

    private Double longitude;

    private String gridCode;
}
