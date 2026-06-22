package com.lab.requisition.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class SkuCreateRequest {

    @NotBlank
    private String skuCode;

    @NotBlank
    private String name;

    private String category;

    private String unit;

    private String specification;

    private String lab;

    @Min(0)
    private Integer safetyStock;
}
