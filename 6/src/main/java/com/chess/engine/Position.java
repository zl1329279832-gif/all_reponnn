package com.chess.engine;

import lombok.Data;

@Data
public class Position {
    private int row;
    private int col;

    public Position() {
    }

    public Position(int row, int col) {
        this.row = row;
        this.col = col;
    }

    public boolean isValid() {
        return row >= 0 && row < 10 && col >= 0 && col < 9;
    }

    public boolean isInRedPalace() {
        return row >= 7 && row <= 9 && col >= 3 && col <= 5;
    }

    public boolean isInBlackPalace() {
        return row >= 0 && row <= 2 && col >= 3 && col <= 5;
    }

    public boolean hasCrossedRiverForRed() {
        return row <= 4;
    }

    public boolean hasCrossedRiverForBlack() {
        return row >= 5;
    }
}
