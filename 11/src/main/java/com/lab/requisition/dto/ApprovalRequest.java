package com.lab.requisition.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ApprovalRequest {

    @NotBlank
    private String approver;

    private String remark;
}
