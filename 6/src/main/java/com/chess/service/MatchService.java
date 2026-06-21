package com.chess.service;

import com.chess.dto.*;
import com.chess.engine.ChessBoard;
import com.chess.engine.MoveValidationResult;
import com.chess.engine.PieceType;
import com.chess.engine.Position;
import com.chess.entity.Match;
import com.chess.entity.Move;
import com.chess.entity.Player;
import com.chess.repository.MatchRepository;
import com.chess.repository.MoveRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;

@Service
@RequiredArgsConstructor
public class MatchService {

    private final MatchRepository matchRepository;
    private final MoveRepository moveRepository;
    private final PlayerService playerService;
    private final EloService eloService;

    private final Map<Long, ReentrantLock> matchLocks = new ConcurrentHashMap<>();

    @Transactional
    public ApiResponse<MatchDto> createMatch(CreateMatchRequest request) {
        Player red = playerService.getOrCreatePlayer(request.getRedPlayerId(), request.getRedPlayerName());
        Player black = playerService.getOrCreatePlayer(request.getBlackPlayerId(), request.getBlackPlayerName());

        ChessBoard board = new ChessBoard();

        Match.MatchBuilder builder = Match.builder()
                .redPlayerId(request.getRedPlayerId())
                .blackPlayerId(request.getBlackPlayerId())
                .status(Match.MatchStatus.IN_PROGRESS)
                .currentTurn(0)
                .nextTurnPlayerId(request.getRedPlayerId())
                .boardSnapshot(board.toSnapshot());

        if (request.getBaseSeconds() != null && request.getBaseSeconds() > 0) {
            builder.baseSeconds(request.getBaseSeconds())
                    .redTimeLeft(request.getBaseSeconds())
                    .blackTimeLeft(request.getBaseSeconds());
        }

        Match match = builder.build();
        match = matchRepository.save(match);

        MatchDto dto = toMatchDto(match, board, red, black);
        return ApiResponse.success(dto);
    }

    @Transactional
    public ApiResponse<MoveDto> makeMove(Long matchId, MakeMoveRequest request) {
        ReentrantLock lock = matchLocks.computeIfAbsent(matchId, k -> new ReentrantLock());
        lock.lock();
        try {
            return doMakeMove(matchId, request);
        } finally {
            lock.unlock();
        }
    }

    private ApiResponse<MoveDto> doMakeMove(Long matchId, MakeMoveRequest request) {
        Optional<Match> matchOpt = matchRepository.findById(matchId);
        if (matchOpt.isEmpty()) {
            return ApiResponse.notFound("对局不存在");
        }

        Match match = matchOpt.get();

        if (match.getStatus() != Match.MatchStatus.IN_PROGRESS) {
            return ApiResponse.error("对局已结束");
        }

        if (!match.getNextTurnPlayerId().equals(request.getPlayerId())) {
            return ApiResponse.error("不是你的回合");
        }

        boolean isRedTurn = request.getPlayerId().equals(match.getRedPlayerId());
        LocalDateTime now = LocalDateTime.now();
        long elapsedSeconds = 0;

        if (match.getBaseSeconds() != null && match.getBaseSeconds() > 0) {
            LocalDateTime startTime = match.getLastMoveAt() != null ? match.getLastMoveAt() : match.getCreatedAt();
            elapsedSeconds = Duration.between(startTime, now).getSeconds();
            if (elapsedSeconds < 0) {
                elapsedSeconds = 0;
            }

            ApiResponse<MoveDto> timeoutResult = checkAndApplyTimeout(match, isRedTurn, now, elapsedSeconds);
            if (timeoutResult != null) {
                return timeoutResult;
            }
        }

        ChessBoard board = ChessBoard.fromSnapshot(match.getBoardSnapshot());

        Position from = new Position(request.getFromRow(), request.getFromCol());
        Position to = new Position(request.getToRow(), request.getToCol());

        MoveValidationResult validation = board.applyMove(from, to, isRedTurn);
        if (!validation.isSuccess()) {
            return ApiResponse.error(validation.getErrorMessage());
        }

        ChessBoard boardAfter = validation.getBoardAfter();

        Move move = Move.builder()
                .matchId(matchId)
                .moveNumber(match.getCurrentTurn() + 1)
                .playerId(request.getPlayerId())
                .fromRow(request.getFromRow())
                .fromCol(request.getFromCol())
                .toRow(request.getToRow())
                .toCol(request.getToCol())
                .pieceType(boardAfter.getPiece(to) != null ? boardAfter.getPiece(to).getCode() : null)
                .capturedPieceType(validation.getCapturedPiece() != null ? validation.getCapturedPiece().getCode() : null)
                .boardSnapshotAfter(boardAfter.toSnapshot())
                .build();

        move = moveRepository.save(move);

        match.setCurrentTurn(match.getCurrentTurn() + 1);
        match.setNextTurnPlayerId(isRedTurn ? match.getBlackPlayerId() : match.getRedPlayerId());
        match.setBoardSnapshot(boardAfter.toSnapshot());

        if (match.getBaseSeconds() != null && match.getBaseSeconds() > 0) {
            deductTime(match, isRedTurn, elapsedSeconds);
            match.setLastMoveAt(now);
        }

        boolean redGeneralCaptured = boardAfter.isGeneralCaptured(true);
        boolean blackGeneralCaptured = boardAfter.isGeneralCaptured(false);

        if (redGeneralCaptured || blackGeneralCaptured) {
            match.setStatus(redGeneralCaptured ? Match.MatchStatus.BLACK_WIN : Match.MatchStatus.RED_WIN);
            match.setEndedAt(LocalDateTime.now());
            String winner = redGeneralCaptured ? match.getBlackPlayerId() : match.getRedPlayerId();
            match.setWinnerPlayerId(winner);
        }

        try {
            match = matchRepository.save(match);
        } catch (OptimisticLockingFailureException e) {
            return ApiResponse.error("发生并发冲突，请重试");
        }

        if (match.getStatus() != Match.MatchStatus.IN_PROGRESS) {
            eloService.updateRatings(
                    match.getRedPlayerId(),
                    match.getBlackPlayerId(),
                    match.getWinnerPlayerId()
            );
        }

        Player player = playerService.getPlayer(request.getPlayerId());
        MoveDto moveDto = toMoveDto(move, player);
        return ApiResponse.success(moveDto);
    }

    private ApiResponse<MoveDto> checkAndApplyTimeout(Match match, boolean isRedTurn, LocalDateTime now, long elapsedSeconds) {
        int currentTimeLeft = isRedTurn
                ? (match.getRedTimeLeft() != null ? match.getRedTimeLeft() : 0)
                : (match.getBlackTimeLeft() != null ? match.getBlackTimeLeft() : 0);

        int newTimeLeft = (int) (currentTimeLeft - elapsedSeconds);

        if (newTimeLeft <= 0) {
            if (isRedTurn) {
                match.setRedTimeLeft(0);
            } else {
                match.setBlackTimeLeft(0);
            }
            match.setStatus(isRedTurn ? Match.MatchStatus.BLACK_WIN : Match.MatchStatus.RED_WIN);
            match.setEndedAt(now);
            match.setWinnerPlayerId(isRedTurn ? match.getBlackPlayerId() : match.getRedPlayerId());

            try {
                matchRepository.save(match);
            } catch (OptimisticLockingFailureException e) {
                return ApiResponse.error("发生并发冲突，请重试");
            }

            eloService.updateRatings(
                    match.getRedPlayerId(),
                    match.getBlackPlayerId(),
                    match.getWinnerPlayerId()
            );

            String loser = isRedTurn ? "红方" : "黑方";
            return ApiResponse.error(loser + "时间耗尽，对局结束");
        }
        return null;
    }

    private void deductTime(Match match, boolean isRedTurn, long elapsedSeconds) {
        if (isRedTurn) {
            int current = match.getRedTimeLeft() != null ? match.getRedTimeLeft() : 0;
            match.setRedTimeLeft(Math.max(0, (int) (current - elapsedSeconds)));
        } else {
            int current = match.getBlackTimeLeft() != null ? match.getBlackTimeLeft() : 0;
            match.setBlackTimeLeft(Math.max(0, (int) (current - elapsedSeconds)));
        }
    }

    public ApiResponse<MatchDto> getMatch(Long matchId) {
        Optional<Match> matchOpt = matchRepository.findById(matchId);
        if (matchOpt.isEmpty()) {
            return ApiResponse.notFound("对局不存在");
        }
        Match match = matchOpt.get();
        ChessBoard board = ChessBoard.fromSnapshot(match.getBoardSnapshot());
        Player red = playerService.getPlayer(match.getRedPlayerId());
        Player black = playerService.getPlayer(match.getBlackPlayerId());
        return ApiResponse.success(toMatchDto(match, board, red, black));
    }

    public ApiResponse<List<MoveDto>> getMatchMoves(Long matchId) {
        Optional<Match> matchOpt = matchRepository.findById(matchId);
        if (matchOpt.isEmpty()) {
            return ApiResponse.notFound("对局不存在");
        }

        List<Move> moves = moveRepository.findByMatchIdOrderByMoveNumberAsc(matchId);
        List<MoveDto> dtos = new ArrayList<>();
        for (Move move : moves) {
            Player player = playerService.getPlayer(move.getPlayerId());
            dtos.add(toMoveDto(move, player));
        }
        return ApiResponse.success(dtos);
    }

    public ApiResponse<Map<String, Object>> getMatchSnapshot(Long matchId) {
        Optional<Match> matchOpt = matchRepository.findById(matchId);
        if (matchOpt.isEmpty()) {
            return ApiResponse.notFound("对局不存在");
        }
        Match match = matchOpt.get();
        ChessBoard board = ChessBoard.fromSnapshot(match.getBoardSnapshot());

        Map<String, Object> snapshot = new java.util.LinkedHashMap<>();
        snapshot.put("matchId", matchId);
        snapshot.put("status", match.getStatus());
        snapshot.put("nextTurnPlayerId", match.getNextTurnPlayerId());
        snapshot.put("currentTurn", match.getCurrentTurn());
        snapshot.put("fen", board.toFen());
        snapshot.put("board", board.getBoardDisplay());

        Player red = playerService.getPlayer(match.getRedPlayerId());
        Player black = playerService.getPlayer(match.getBlackPlayerId());
        snapshot.put("redPlayerId", match.getRedPlayerId());
        snapshot.put("redPlayerName", red != null ? red.getName() : null);
        snapshot.put("blackPlayerId", match.getBlackPlayerId());
        snapshot.put("blackPlayerName", black != null ? black.getName() : null);

        if (match.getBaseSeconds() != null && match.getBaseSeconds() > 0) {
            snapshot.put("baseSeconds", match.getBaseSeconds());
            snapshot.put("redTimeLeft", match.getRedTimeLeft());
            snapshot.put("blackTimeLeft", match.getBlackTimeLeft());
            snapshot.put("timerEnabled", true);
        } else {
            snapshot.put("timerEnabled", false);
        }

        return ApiResponse.success(snapshot);
    }

    private MatchDto toMatchDto(Match match, ChessBoard board, Player red, Player black) {
        return MatchDto.builder()
                .id(match.getId())
                .redPlayerId(match.getRedPlayerId())
                .redPlayerName(red != null ? red.getName() : null)
                .blackPlayerId(match.getBlackPlayerId())
                .blackPlayerName(black != null ? black.getName() : null)
                .status(match.getStatus())
                .currentTurn(match.getCurrentTurn())
                .nextTurnPlayerId(match.getNextTurnPlayerId())
                .createdAt(match.getCreatedAt())
                .endedAt(match.getEndedAt())
                .winnerPlayerId(match.getWinnerPlayerId())
                .fen(board != null ? board.toFen() : null)
                .boardDisplay(board != null ? board.getBoardDisplay() : null)
                .baseSeconds(match.getBaseSeconds())
                .redTimeLeft(match.getRedTimeLeft())
                .blackTimeLeft(match.getBlackTimeLeft())
                .build();
    }

    private MoveDto toMoveDto(Move move, Player player) {
        PieceType piece = move.getPieceType() != null ? PieceType.fromCode(move.getPieceType()) : null;
        PieceType captured = move.getCapturedPieceType() != null ? PieceType.fromCode(move.getCapturedPieceType()) : null;

        return MoveDto.builder()
                .id(move.getId())
                .matchId(move.getMatchId())
                .moveNumber(move.getMoveNumber())
                .playerId(move.getPlayerId())
                .playerName(player != null ? player.getName() : null)
                .fromRow(move.getFromRow())
                .fromCol(move.getFromCol())
                .toRow(move.getToRow())
                .toCol(move.getToCol())
                .pieceType(move.getPieceType())
                .pieceDisplayName(piece != null ? piece.getDisplayName() : null)
                .capturedPieceType(move.getCapturedPieceType())
                .capturedPieceDisplayName(captured != null ? captured.getDisplayName() : null)
                .createdAt(move.getCreatedAt())
                .build();
    }
}
