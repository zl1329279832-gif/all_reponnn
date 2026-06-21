package com.chess.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class MakeMoveRequest {

    @NotBlank(message = "playerId 不能为空")
    private String playerId;

    @NotNull(message = "fromRow 不能为空")
    @Min(value = 0, message = "fromRow 必须 >= 0")
    @Max(value = 9, message = "fromRow 必须 <= 9")
    private Integer fromRow;

    @NotNull(message = "fromCol 不能为空")
    @Min(value = 0, message = "fromCol 必须 >= 0")
    @Max(value = 8, message = "fromCol 必须 <= 8")
    private Integer fromCol;

    @NotNull(message = "toRow 不能为空")
    @Min(value = 0, message = "toRow 必须 >= 0")
    @Max(value = 9, message = "toRow 必须 <= 9")
    private Integer toRow;

    @NotNull(message = "toCol 不能为空")
    @Min(value = 0, message = "toCol 必须 >= 0")
    @Max(value = 8, message = "toCol 必须 <= 8")
    private Integer toCol;
}
