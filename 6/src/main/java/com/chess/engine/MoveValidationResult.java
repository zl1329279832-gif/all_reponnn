package com.chess.engine;

import lombok.Data;

@Data
public class MoveValidationResult {
    private boolean success;
    private String errorMessage;
    private PieceType capturedPiece;
    private ChessBoard boardAfter;

    private MoveValidationResult() {
    }

    public static MoveValidationResult success(PieceType capturedPiece) {
        MoveValidationResult result = new MoveValidationResult();
        result.success = true;
        result.capturedPiece = capturedPiece;
        return result;
    }

    public static MoveValidationResult fail(String errorMessage) {
        MoveValidationResult result = new MoveValidationResult();
        result.success = false;
        result.errorMessage = errorMessage;
        return result;
    }
}
