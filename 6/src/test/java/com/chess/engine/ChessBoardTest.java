package com.chess.engine;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ChessBoardTest {

    private ChessBoard board;

    @BeforeEach
    void setUp() {
        board = new ChessBoard();
    }

    @Test
    @DisplayName("初始化棋盘 - 检查棋子位置正确")
    void testInitialBoardSetup() {
        assertEquals(PieceType.RED_GENERAL, board.getPiece(9, 4));
        assertEquals(PieceType.RED_CHARIOT, board.getPiece(9, 0));
        assertEquals(PieceType.RED_HORSE, board.getPiece(9, 1));
        assertEquals(PieceType.RED_CANNON, board.getPiece(7, 1));
        assertEquals(PieceType.RED_SOLDIER, board.getPiece(6, 0));
        assertEquals(PieceType.RED_SOLDIER, board.getPiece(6, 2));
        assertEquals(PieceType.RED_SOLDIER, board.getPiece(6, 4));

        assertEquals(PieceType.BLACK_GENERAL, board.getPiece(0, 4));
        assertEquals(PieceType.BLACK_CHARIOT, board.getPiece(0, 0));
        assertEquals(PieceType.BLACK_HORSE, board.getPiece(0, 1));
        assertEquals(PieceType.BLACK_CANNON, board.getPiece(2, 1));
        assertEquals(PieceType.BLACK_SOLDIER, board.getPiece(3, 0));
        assertEquals(PieceType.BLACK_SOLDIER, board.getPiece(3, 2));
        assertEquals(PieceType.BLACK_SOLDIER, board.getPiece(3, 4));

        assertNull(board.getPiece(5, 4));
    }

    @Test
    @DisplayName("车 - 正常直线移动")
    void testChariotNormalMove() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(5, 4, PieceType.RED_CHARIOT);
        board.setPiece(9, 3, PieceType.RED_GENERAL);
        board.setPiece(0, 5, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 3));
        board.setBlackGeneralPos(new Position(0, 5));

        MoveValidationResult result = board.applyMove(
                new Position(5, 4), new Position(5, 8), true
        );
        assertTrue(result.isSuccess(), "车横向移动应成功: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("车 - 路径有障碍物被拒绝")
    void testChariotBlocked() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(5, 0, PieceType.RED_CHARIOT);
        board.setPiece(5, 4, PieceType.RED_SOLDIER);
        board.setPiece(9, 3, PieceType.RED_GENERAL);
        board.setPiece(0, 5, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 3));
        board.setBlackGeneralPos(new Position(0, 5));

        MoveValidationResult result = board.applyMove(
                new Position(5, 0), new Position(5, 8), true
        );
        assertFalse(result.isSuccess(), "车路径有障碍物应被拒绝");
        assertTrue(result.getErrorMessage().contains("障碍物"),
                "错误信息应提到障碍物: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("马 - 马脚被堵拒绝场景")
    void testHorseBlockedLeg() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(9, 1, PieceType.RED_HORSE);
        board.setPiece(8, 1, PieceType.RED_SOLDIER);
        board.setPiece(9, 3, PieceType.RED_GENERAL);
        board.setPiece(0, 5, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 3));
        board.setBlackGeneralPos(new Position(0, 5));

        MoveValidationResult result = board.applyMove(
                new Position(9, 1), new Position(7, 2), true
        );
        assertFalse(result.isSuccess(), "马脚被堵应被拒绝");
        assertTrue(result.getErrorMessage().contains("马脚被堵"),
                "错误信息应提到马脚被堵: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("马 - 正常马移动（马脚不堵）")
    void testHorseNormalMove() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(9, 1, PieceType.RED_HORSE);
        board.setPiece(9, 3, PieceType.RED_GENERAL);
        board.setPiece(0, 5, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 3));
        board.setBlackGeneralPos(new Position(0, 5));

        MoveValidationResult result = board.applyMove(
                new Position(9, 1), new Position(7, 2), true
        );
        assertTrue(result.isSuccess(), "马脚不堵应成功: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("炮 - 无炮架吃子被拒绝（炮打隔子）")
    void testCannonCaptureWithoutScreen() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(7, 1, PieceType.RED_CANNON);
        board.setPiece(3, 1, PieceType.BLACK_SOLDIER);
        board.setPiece(9, 3, PieceType.RED_GENERAL);
        board.setPiece(0, 5, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 3));
        board.setBlackGeneralPos(new Position(0, 5));

        MoveValidationResult result = board.applyMove(
                new Position(7, 1), new Position(3, 1), true
        );
        assertFalse(result.isSuccess(), "炮无炮架吃子应被拒绝");
        assertTrue(result.getErrorMessage().contains("炮架") || result.getErrorMessage().contains("隔"),
                "错误信息应提到炮架/隔: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("炮 - 有一个炮架正常吃子")
    void testCannonCaptureWithOneScreen() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(7, 1, PieceType.RED_CANNON);
        board.setPiece(5, 1, PieceType.RED_SOLDIER);
        board.setPiece(3, 1, PieceType.BLACK_SOLDIER);
        board.setPiece(9, 3, PieceType.RED_GENERAL);
        board.setPiece(0, 5, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 3));
        board.setBlackGeneralPos(new Position(0, 5));

        MoveValidationResult result = board.applyMove(
                new Position(7, 1), new Position(3, 1), true
        );
        assertTrue(result.isSuccess(), "炮有一个炮架吃子应成功: " + result.getErrorMessage());
        assertEquals(PieceType.BLACK_SOLDIER, result.getCapturedPiece(),
                "应吃掉黑卒");
    }

    @Test
    @DisplayName("炮 - 多个炮架被拒绝")
    void testCannonCaptureWithMultipleScreens() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(7, 1, PieceType.RED_CANNON);
        board.setPiece(6, 1, PieceType.RED_SOLDIER);
        board.setPiece(5, 1, PieceType.BLACK_SOLDIER);
        board.setPiece(3, 1, PieceType.BLACK_CHARIOT);
        board.setPiece(9, 3, PieceType.RED_GENERAL);
        board.setPiece(0, 5, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 3));
        board.setBlackGeneralPos(new Position(0, 5));

        MoveValidationResult result = board.applyMove(
                new Position(7, 1), new Position(3, 1), true
        );
        assertFalse(result.isSuccess(), "炮有多个炮架吃子应被拒绝");
        assertTrue(result.getErrorMessage().contains("炮架") || result.getErrorMessage().contains("隔"),
                "错误信息应提到炮架/隔: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("炮 - 无障碍物时空移成功")
    void testCannonEmptyMove() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(7, 1, PieceType.RED_CANNON);
        board.setPiece(9, 3, PieceType.RED_GENERAL);
        board.setPiece(0, 5, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 3));
        board.setBlackGeneralPos(new Position(0, 5));

        MoveValidationResult result = board.applyMove(
                new Position(7, 1), new Position(4, 1), true
        );
        assertTrue(result.isSuccess(), "炮空移无障碍物应成功: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("将帅照面 - 被拒绝场景")
    void testGeneralsFacingRejected() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(9, 4, PieceType.RED_GENERAL);
        board.setPiece(0, 4, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 4));
        board.setBlackGeneralPos(new Position(0, 4));

        board.setPiece(4, 4, PieceType.RED_SOLDIER);

        MoveValidationResult result = board.applyMove(
                new Position(4, 4), new Position(4, 3), true
        );
        assertFalse(result.isSuccess(), "将帅照面应被拒绝");
        assertTrue(result.getErrorMessage().contains("将帅") || result.getErrorMessage().contains("照面"),
                "错误信息应提到将帅照面: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("将帅 - 帅不能出九宫格")
    void testGeneralOutOfPalace() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(9, 3, PieceType.RED_GENERAL);
        board.setPiece(0, 5, PieceType.BLACK_GENERAL);
        board.setRedGeneralPos(new Position(9, 3));
        board.setBlackGeneralPos(new Position(0, 5));

        MoveValidationResult result = board.applyMove(
                new Position(9, 3), new Position(9, 2), true
        );
        assertFalse(result.isSuccess(), "帅不能出九宫格");
        assertTrue(result.getErrorMessage().contains("九宫"),
                "错误信息应提到九宫: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("兵 - 未过河不能横走")
    void testSoldierCannotMoveSideBeforeRiver() {
        MoveValidationResult result = board.applyMove(
                new Position(6, 0), new Position(6, 1), true
        );
        assertFalse(result.isSuccess(), "红兵未过河不能横走");
        assertTrue(result.getErrorMessage().contains("过河") || result.getErrorMessage().contains("横走"),
                "错误信息应提到过河/横走: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("兵 - 过河后可以横走")
    void testSoldierCanMoveSideAfterRiver() {
        board = new ChessBoard();
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 9; c++) {
                board.setPiece(r, c, null);
            }
        }
        board.setPiece(4, 4, PieceType.RED_SOLDIER);
        board.setPiece(9, 4, PieceType.RED_GENERAL);
        board.setPiece(0, 4, PieceType.BLACK_GENERAL);
        board.setPiece(2, 4, PieceType.BLACK_SOLDIER);
        board.setRedGeneralPos(new Position(9, 4));
        board.setBlackGeneralPos(new Position(0, 4));

        MoveValidationResult result = board.applyMove(
                new Position(4, 4), new Position(4, 5), true
        );
        assertTrue(result.isSuccess(), "红兵过河后可以横走: " + result.getErrorMessage());
    }

    @Test
    @DisplayName("棋盘序列化和反序列化")
    void testBoardSerialization() {
        String snapshot = board.toSnapshot();
        assertNotNull(snapshot);

        ChessBoard restored = ChessBoard.fromSnapshot(snapshot);
        for (int r = 0; r < ChessBoard.ROWS; r++) {
            for (int c = 0; c < ChessBoard.COLS; c++) {
                assertEquals(board.getPiece(r, c), restored.getPiece(r, c),
                        String.format("位置 (%d,%d) 不匹配", r, c));
            }
        }
    }

    @Test
    @DisplayName("起点无棋子被拒绝")
    void testNoPieceAtSource() {
        MoveValidationResult result = board.applyMove(
                new Position(5, 5), new Position(5, 6), true
        );
        assertFalse(result.isSuccess());
        assertTrue(result.getErrorMessage().contains("没有棋子"));
    }

    @Test
    @DisplayName("不能移动对方棋子")
    void testCannotMoveOpponentPiece() {
        MoveValidationResult result = board.applyMove(
                new Position(0, 0), new Position(0, 1), true
        );
        assertFalse(result.isSuccess(), "红方不能移动黑车");
        assertTrue(result.getErrorMessage().contains("黑方"));
    }

    @Test
    @DisplayName("不能吃自己的棋子")
    void testCannotCaptureOwnPiece() {
        MoveValidationResult result = board.applyMove(
                new Position(9, 0), new Position(9, 1), true
        );
        assertFalse(result.isSuccess(), "不能吃自己的马");
        assertTrue(result.getErrorMessage().contains("自己"));
    }
}
