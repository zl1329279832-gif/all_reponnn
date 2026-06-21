package com.chess.engine;

public enum PieceType {
    RED_GENERAL("帅", "R_GEN", true),
    RED_CHARIOT("车", "R_CHA", true),
    RED_HORSE("马", "R_HOR", true),
    RED_CANNON("炮", "R_CAN", true),
    RED_SOLDIER("兵", "R_SOL", true),

    BLACK_GENERAL("将", "B_GEN", false),
    BLACK_CHARIOT("车", "B_CHA", false),
    BLACK_HORSE("马", "B_HOR", false),
    BLACK_CANNON("炮", "B_CAN", false),
    BLACK_SOLDIER("卒", "B_SOL", false);

    private final String displayName;
    private final String code;
    private final boolean isRed;

    PieceType(String displayName, String code, boolean isRed) {
        this.displayName = displayName;
        this.code = code;
        this.isRed = isRed;
    }

    public String getDisplayName() {
        return displayName;
    }

    public String getCode() {
        return code;
    }

    public boolean isRed() {
        return isRed;
    }

    public static PieceType fromCode(String code) {
        for (PieceType type : values()) {
            if (type.code.equals(code)) {
                return type;
            }
        }
        return null;
    }
}
