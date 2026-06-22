package com.lab.requisition.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class InventoryCreateRequest {

    @NotNull
    private Long skuId;

    @NotBlank
    private String location;

    @NotNull
    @Min(0)
    private Integer quantity;
}
