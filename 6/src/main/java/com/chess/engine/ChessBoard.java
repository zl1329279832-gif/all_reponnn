package com.chess.engine;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class ChessBoard {

    public static final int ROWS = 10;
    public static final int COLS = 9;

    private PieceType[][] board;
    private Position redGeneralPos;
    private Position blackGeneralPos;

    public ChessBoard() {
        this.board = new PieceType[ROWS][COLS];
        initBoard();
    }

    public void initBoard() {
        for (int r = 0; r < ROWS; r++) {
            for (int c = 0; c < COLS; c++) {
                board[r][c] = null;
            }
        }

        board[0][0] = PieceType.BLACK_CHARIOT;
        board[0][1] = PieceType.BLACK_HORSE;
        board[0][4] = PieceType.BLACK_GENERAL;
        board[0][7] = PieceType.BLACK_HORSE;
        board[0][8] = PieceType.BLACK_CHARIOT;

        board[2][1] = PieceType.BLACK_CANNON;
        board[2][7] = PieceType.BLACK_CANNON;

        board[3][0] = PieceType.BLACK_SOLDIER;
        board[3][2] = PieceType.BLACK_SOLDIER;
        board[3][4] = PieceType.BLACK_SOLDIER;
        board[3][6] = PieceType.BLACK_SOLDIER;
        board[3][8] = PieceType.BLACK_SOLDIER;

        blackGeneralPos = new Position(0, 4);

        board[9][0] = PieceType.RED_CHARIOT;
        board[9][1] = PieceType.RED_HORSE;
        board[9][4] = PieceType.RED_GENERAL;
        board[9][7] = PieceType.RED_HORSE;
        board[9][8] = PieceType.RED_CHARIOT;

        board[7][1] = PieceType.RED_CANNON;
        board[7][7] = PieceType.RED_CANNON;

        board[6][0] = PieceType.RED_SOLDIER;
        board[6][2] = PieceType.RED_SOLDIER;
        board[6][4] = PieceType.RED_SOLDIER;
        board[6][6] = PieceType.RED_SOLDIER;
        board[6][8] = PieceType.RED_SOLDIER;

        redGeneralPos = new Position(9, 4);
    }

    public PieceType getPiece(int row, int col) {
        if (row < 0 || row >= ROWS || col < 0 || col >= COLS) {
            return null;
        }
        return board[row][col];
    }

    public PieceType getPiece(Position pos) {
        return getPiece(pos.getRow(), pos.getCol());
    }

    public void setPiece(int row, int col, PieceType piece) {
        board[row][col] = piece;
        if (piece == PieceType.RED_GENERAL) {
            redGeneralPos = new Position(row, col);
        } else if (piece == PieceType.BLACK_GENERAL) {
            blackGeneralPos = new Position(row, col);
        }
    }

    public MoveValidationResult validateMove(Position from, Position to, boolean isRedTurn) {
        if (!from.isValid() || !to.isValid()) {
            return MoveValidationResult.fail("坐标超出棋盘范围");
        }

        if (from.equals(to)) {
            return MoveValidationResult.fail("起点和终点不能相同");
        }

        PieceType movingPiece = getPiece(from);
        if (movingPiece == null) {
            return MoveValidationResult.fail("起点没有棋子");
        }

        if (movingPiece.isRed() != isRedTurn) {
            return MoveValidationResult.fail(isRedTurn ? "不能移动黑方棋子" : "不能移动红方棋子");
        }

        PieceType targetPiece = getPiece(to);
        if (targetPiece != null && targetPiece.isRed() == isRedTurn) {
            return MoveValidationResult.fail("不能吃自己的棋子");
        }

        MoveValidationResult pieceResult = validatePieceMove(from, to, movingPiece, targetPiece);
        if (!pieceResult.isSuccess()) {
            return pieceResult;
        }

        return MoveValidationResult.success(targetPiece);
    }

    private MoveValidationResult validatePieceMove(Position from, Position to, PieceType moving, PieceType target) {
        int dRow = to.getRow() - from.getRow();
        int dCol = to.getCol() - from.getCol();
        int absRow = Math.abs(dRow);
        int absCol = Math.abs(dCol);

        switch (moving) {
            case RED_GENERAL:
            case BLACK_GENERAL:
                return validateGeneral(from, to, dRow, dCol, absRow, absCol, moving.isRed());

            case RED_CHARIOT:
            case BLACK_CHARIOT:
                return validateChariot(from, to, absRow, absCol);

            case RED_HORSE:
            case BLACK_HORSE:
                return validateHorse(from, to, dRow, dCol, absRow, absCol);

            case RED_CANNON:
            case BLACK_CANNON:
                return validateCannon(from, to, absRow, absCol, target);

            case RED_SOLDIER:
            case BLACK_SOLDIER:
                return validateSoldier(from, to, dRow, dCol, absRow, absCol, moving.isRed());

            default:
                return MoveValidationResult.fail("未知棋子类型");
        }
    }

    private MoveValidationResult validateGeneral(Position from, Position to, int dRow, int dCol,
                                                  int absRow, int absCol, boolean isRed) {
        if (absRow + absCol != 1) {
            return MoveValidationResult.fail("将/帅每次只能走一步直线");
        }

        boolean inPalace = isRed ? to.isInRedPalace() : to.isInBlackPalace();
        if (!inPalace) {
            return MoveValidationResult.fail("将/帅不能离开九宫格");
        }

        return MoveValidationResult.success(null);
    }

    private MoveValidationResult validateChariot(Position from, Position to, int absRow, int absCol) {
        if (absRow != 0 && absCol != 0) {
            return MoveValidationResult.fail("车必须走直线");
        }

        if (hasObstaclesOnLine(from, to)) {
            return MoveValidationResult.fail("车的移动路径上有障碍物");
        }

        return MoveValidationResult.success(null);
    }

    private MoveValidationResult validateHorse(Position from, Position to, int dRow, int dCol,
                                                int absRow, int absCol) {
        if (!((absRow == 2 && absCol == 1) || (absRow == 1 && absCol == 2))) {
            return MoveValidationResult.fail("马必须走日字");
        }

        Position legPos;
        if (absRow == 2) {
            legPos = new Position(from.getRow() + (dRow > 0 ? 1 : -1), from.getCol());
        } else {
            legPos = new Position(from.getRow(), from.getCol() + (dCol > 0 ? 1 : -1));
        }

        if (getPiece(legPos) != null) {
            return MoveValidationResult.fail("马脚被堵，无法移动");
        }

        return MoveValidationResult.success(null);
    }

    private MoveValidationResult validateCannon(Position from, Position to, int absRow, int absCol, PieceType target) {
        if (absRow != 0 && absCol != 0) {
            return MoveValidationResult.fail("炮必须走直线");
        }

        int obstacleCount = countObstaclesOnLine(from, to);

        if (target == null) {
            if (obstacleCount > 0) {
                return MoveValidationResult.fail("炮移动时路径上不能有障碍物");
            }
        } else {
            if (obstacleCount != 1) {
                return MoveValidationResult.fail("炮吃子时必须且只能隔一个棋子（炮架）");
            }
        }

        return MoveValidationResult.success(target);
    }

    private MoveValidationResult validateSoldier(Position from, Position to, int dRow, int dCol,
                                                  int absRow, int absCol, boolean isRed) {
        if (absRow + absCol != 1) {
            return MoveValidationResult.fail("兵/卒每次只能走一步");
        }

        if (isRed) {
            if (dRow > 0) {
                return MoveValidationResult.fail("红兵不能后退");
            }
            if (!from.hasCrossedRiverForRed() && absCol == 1) {
                return MoveValidationResult.fail("红兵未过河不能横走");
            }
        } else {
            if (dRow < 0) {
                return MoveValidationResult.fail("黑卒不能后退");
            }
            if (!from.hasCrossedRiverForBlack() && absCol == 1) {
                return MoveValidationResult.fail("黑卒未过河不能横走");
            }
        }

        return MoveValidationResult.success(null);
    }

    private boolean hasObstaclesOnLine(Position from, Position to) {
        return countObstaclesOnLine(from, to) > 0;
    }

    private int countObstaclesOnLine(Position from, Position to) {
        int count = 0;
        if (from.getRow() == to.getRow()) {
            int row = from.getRow();
            int minCol = Math.min(from.getCol(), to.getCol());
            int maxCol = Math.max(from.getCol(), to.getCol());
            for (int c = minCol + 1; c < maxCol; c++) {
                if (board[row][c] != null) {
                    count++;
                }
            }
        } else if (from.getCol() == to.getCol()) {
            int col = from.getCol();
            int minRow = Math.min(from.getRow(), to.getRow());
            int maxRow = Math.max(from.getRow(), to.getRow());
            for (int r = minRow + 1; r < maxRow; r++) {
                if (board[r][col] != null) {
                    count++;
                }
            }
        }
        return count;
    }

    public boolean isGeneralsFacing() {
        if (redGeneralPos == null || blackGeneralPos == null) {
            return false;
        }
        if (redGeneralPos.getCol() != blackGeneralPos.getCol()) {
            return false;
        }
        int col = redGeneralPos.getCol();
        int minRow = Math.min(redGeneralPos.getRow(), blackGeneralPos.getRow());
        int maxRow = Math.max(redGeneralPos.getRow(), blackGeneralPos.getRow());
        for (int r = minRow + 1; r < maxRow; r++) {
            if (board[r][col] != null) {
                return false;
            }
        }
        return true;
    }

    public MoveValidationResult applyMove(Position from, Position to, boolean isRedTurn) {
        MoveValidationResult result = validateMove(from, to, isRedTurn);
        if (!result.isSuccess()) {
            return result;
        }

        PieceType movingPiece = getPiece(from);
        PieceType capturedPiece = result.getCapturedPiece();

        setPiece(from.getRow(), from.getCol(), null);
        setPiece(to.getRow(), to.getCol(), movingPiece);

        if (isGeneralsFacing()) {
            setPiece(from.getRow(), from.getCol(), movingPiece);
            setPiece(to.getRow(), to.getCol(), capturedPiece);
            if (capturedPiece == PieceType.RED_GENERAL) {
                redGeneralPos = new Position(to.getRow(), to.getCol());
            } else if (capturedPiece == PieceType.BLACK_GENERAL) {
                blackGeneralPos = new Position(to.getRow(), to.getCol());
            }
            if (movingPiece == PieceType.RED_GENERAL) {
                redGeneralPos = new Position(from.getRow(), from.getCol());
            } else if (movingPiece == PieceType.BLACK_GENERAL) {
                blackGeneralPos = new Position(from.getRow(), from.getCol());
            }
            return MoveValidationResult.fail("将帅不能照面");
        }

        result.setBoardAfter(this);
        return result;
    }

    public boolean isGeneralCaptured(boolean isRed) {
        if (isRed) {
            return redGeneralPos == null || getPiece(redGeneralPos) != PieceType.RED_GENERAL;
        } else {
            return blackGeneralPos == null || getPiece(blackGeneralPos) != PieceType.BLACK_GENERAL;
        }
    }

    public String toSnapshot() {
        ObjectMapper mapper = new ObjectMapper();
        try {
            String[][] codeBoard = new String[ROWS][COLS];
            for (int r = 0; r < ROWS; r++) {
                for (int c = 0; c < COLS; c++) {
                    codeBoard[r][c] = board[r][c] != null ? board[r][c].getCode() : null;
                }
            }
            return mapper.writeValueAsString(codeBoard);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize board", e);
        }
    }

    public static ChessBoard fromSnapshot(String snapshot) {
        ObjectMapper mapper = new ObjectMapper();
        try {
            String[][] codeBoard = mapper.readValue(snapshot, String[][].class);
            ChessBoard board = new ChessBoard();
            for (int r = 0; r < ROWS; r++) {
                for (int c = 0; c < COLS; c++) {
                    String code = codeBoard[r][c];
                    PieceType piece = code != null ? PieceType.fromCode(code) : null;
                    board.setPiece(r, c, piece);
                }
            }
            return board;
        } catch (Exception e) {
            throw new RuntimeException("Failed to deserialize board", e);
        }
    }

    public String toFen() {
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r < ROWS; r++) {
            int empty = 0;
            for (int c = 0; c < COLS; c++) {
                PieceType piece = board[r][c];
                if (piece == null) {
                    empty++;
                } else {
                    if (empty > 0) {
                        sb.append(empty);
                        empty = 0;
                    }
                    sb.append(piece.getCode()).append(",");
                }
            }
            if (empty > 0) {
                sb.append(empty);
            }
            if (r < ROWS - 1) {
                sb.append("/");
            }
        }
        return sb.toString();
    }

    public List<String> getBoardDisplay() {
        List<String> rows = new ArrayList<>();
        for (int r = 0; r < ROWS; r++) {
            StringBuilder sb = new StringBuilder();
            for (int c = 0; c < COLS; c++) {
                PieceType piece = board[r][c];
                if (piece == null) {
                    sb.append(". ");
                } else {
                    String name = piece.getDisplayName();
                    if (piece.isRed()) {
                        sb.append(name).append("R");
                    } else {
                        sb.append(name).append("B");
                    }
                    sb.append(" ");
                }
            }
            rows.add(sb.toString().trim());
        }
        return rows;
    }

    public Position getRedGeneralPos() {
        return redGeneralPos != null ? new Position(redGeneralPos.getRow(), redGeneralPos.getCol()) : null;
    }

    public Position getBlackGeneralPos() {
        return blackGeneralPos != null ? new Position(blackGeneralPos.getRow(), blackGeneralPos.getCol()) : null;
    }

    public void setRedGeneralPos(Position pos) {
        this.redGeneralPos = pos != null ? new Position(pos.getRow(), pos.getCol()) : null;
    }

    public void setBlackGeneralPos(Position pos) {
        this.blackGeneralPos = pos != null ? new Position(pos.getRow(), pos.getCol()) : null;
    }

    public ChessBoard copy() {
        ChessBoard copy = new ChessBoard();
        for (int r = 0; r < ROWS; r++) {
            System.arraycopy(this.board[r], 0, copy.board[r], 0, COLS);
        }
        copy.redGeneralPos = this.redGeneralPos != null ? new Position(this.redGeneralPos.getRow(), this.redGeneralPos.getCol()) : null;
        copy.blackGeneralPos = this.blackGeneralPos != null ? new Position(this.blackGeneralPos.getRow(), this.blackGeneralPos.getCol()) : null;
        return copy;
    }
}
