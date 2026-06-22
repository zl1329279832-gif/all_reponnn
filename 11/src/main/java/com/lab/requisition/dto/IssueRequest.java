package com.lab.requisition.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class IssueRequest {

    @NotNull
    @Min(1)
    private Integer quantity;

    @NotBlank
    private String operator;
}
