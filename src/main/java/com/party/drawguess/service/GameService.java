package com.party.drawguess.service;

import com.party.drawguess.dto.*;
import com.party.drawguess.exception.GameException;
import com.party.drawguess.model.*;
import com.party.drawguess.repository.GameRepository;
import com.party.drawguess.repository.RoundRepository;
import com.party.drawguess.repository.RoundSubmissionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class GameService {
    private final GameRepository gameRepository;
    private final RoundRepository roundRepository;
    private final RoundSubmissionRepository submissionRepository;
    private final PlayerService playerService;
    private final com.party.drawguess.repository.RoomRepository roomRepository;

    private final Map<String, Object> submissionLocks = new ConcurrentHashMap<>();

    public GameService(GameRepository gameRepository,
                       RoundRepository roundRepository,
                       RoundSubmissionRepository submissionRepository,
                       PlayerService playerService,
                       com.party.drawguess.repository.RoomRepository roomRepository) {
        this.gameRepository = gameRepository;
        this.roundRepository = roundRepository;
        this.submissionRepository = submissionRepository;
        this.playerService = playerService;
        this.roomRepository = roomRepository;
    }

    private static final int CORRECT_GUESS_SCORE = 10;
    private static final int DRAWER_BONUS_SCORE = 5;

    @Transactional
    public Game createGame(Room room) {
        Game game = new Game();
        game.setRoomId(room.getId());
        game.setRoomCode(room.getRoomCode());
        game.setTotalRounds(room.getTotalRounds());

        Map<Long, String> playerNicknames = new HashMap<>();
        Map<Long, Integer> scores = new HashMap<>();
        for (Long playerId : room.getPlayerIds()) {
            Player p = playerService.getById(playerId);
            playerNicknames.put(playerId, p.getNickname());
            scores.put(playerId, 0);
        }
        game.setPlayerNicknames(playerNicknames);
        game.setScores(scores);

        return gameRepository.save(game);
    }

    @Transactional
    public void startNextRound(Room room, Game game) {
        int roundNumber = game.getCompletedRounds() + 1;
        if (roundNumber > game.getTotalRounds()) {
            endGame(room, game);
            return;
        }

        List<Long> playerIds = new ArrayList<>(room.getPlayerIds());
        int drawerIndex = (roundNumber - 1) % playerIds.size();
        Long drawerId = playerIds.get(drawerIndex);
        Player drawer = playerService.getById(drawerId);

        List<Long> guesserIds = new ArrayList<>(playerIds);
        guesserIds.remove(drawerId);

        Round round = new Round();
        round.setGameId(game.getId());
        round.setRoundNumber(roundNumber);
        round.setDrawerId(drawerId);
        round.setDrawerNickname(drawer.getNickname());
        round.setGuesserIds(guesserIds);
        round.setTargetWord("");

        roundRepository.save(round);
        log.info("开始新轮次: gameId={}, round={}, drawer={}",
                game.getId(), roundNumber, drawer.getNickname());
    }

    @Transactional
    public RoomSnapshotResponse submitDescription(SubmitDescriptionRequest request) {
        Player player = playerService.getById(request.getPlayerId());
        Game game = getById(request.getGameId());
        Round round = getRound(game.getId(), request.getRoundNumber());

        String lockKey = "desc_" + round.getId() + "_" + player.getId();
        Object lock = submissionLocks.computeIfAbsent(lockKey, k -> new Object());
        synchronized (lock) {
            try {
                if (submissionRepository.existsByRoundIdAndPlayerIdAndSubmissionType(
                        round.getId(), player.getId(), RoundSubmission.SubmissionType.DESCRIPTION)) {
                    throw new GameException(409, "本轮描述已提交，请勿重复提交");
                }

                if (!round.getDrawerId().equals(player.getId())) {
                    throw new GameException(403, "只有本轮出题者可以提交描述");
                }

                if (round.getCompleted()) {
                    throw new GameException("本轮已结束");
                }

                round.setTargetWord(request.getTargetWord().trim());
                round.setDescription(request.getDescription().trim());
                roundRepository.save(round);

                RoundSubmission submission = new RoundSubmission();
                submission.setRoundId(round.getId());
                submission.setGameId(game.getId());
                submission.setPlayerId(player.getId());
                submission.setPlayerNickname(player.getNickname());
                submission.setSubmissionType(RoundSubmission.SubmissionType.DESCRIPTION);
                submission.setContent(request.getDescription().trim());
                submission.setIsCorrect(true);
                submission.setScoreEarned(0);
                submissionRepository.save(submission);

                log.info("描述已提交: round={}, drawer={}, word={}",
                        round.getRoundNumber(), player.getNickname(), request.getTargetWord());

                Room room = getRoomForGame(game);
                return toRoomSnapshot(room);
            } finally {
                submissionLocks.remove(lockKey);
            }
        }
    }

    @Transactional
    public RoomSnapshotResponse submitGuess(SubmitGuessRequest request) {
        Player player = playerService.getById(request.getPlayerId());
        Game game = getById(request.getGameId());
        Round round = getRound(game.getId(), request.getRoundNumber());

        if (round.getDescription() == null || round.getDescription().isEmpty()) {
            throw new GameException("出题者尚未提交描述，请等待");
        }

        if (round.getDrawerId().equals(player.getId())) {
            throw new GameException(403, "出题者不能猜词");
        }

        if (!round.getGuesserIds().contains(player.getId())) {
            throw new GameException(403, "你不在本轮猜词者列表中");
        }

        String lockKey = "guess_" + round.getId() + "_" + player.getId();
        Object lock = submissionLocks.computeIfAbsent(lockKey, k -> new Object());
        synchronized (lock) {
            try {
                if (submissionRepository.existsByRoundIdAndPlayerIdAndSubmissionType(
                        round.getId(), player.getId(), RoundSubmission.SubmissionType.GUESS)) {
                    throw new GameException(409, "你已提交过本轮猜词，请勿重复提交");
                }

                if (round.getCompleted()) {
                    throw new GameException("本轮已结束");
                }

                String guess = request.getGuess().trim();
                boolean isCorrect = guess.equalsIgnoreCase(round.getTargetWord());
                int scoreEarned = isCorrect ? CORRECT_GUESS_SCORE : 0;

                RoundSubmission submission = new RoundSubmission();
                submission.setRoundId(round.getId());
                submission.setGameId(game.getId());
                submission.setPlayerId(player.getId());
                submission.setPlayerNickname(player.getNickname());
                submission.setSubmissionType(RoundSubmission.SubmissionType.GUESS);
                submission.setContent(guess);
                submission.setIsCorrect(isCorrect);
                submission.setScoreEarned(scoreEarned);
                submissionRepository.save(submission);

                if (isCorrect) {
                    Map<Long, Integer> scores = game.getScores();
                    scores.put(player.getId(), scores.getOrDefault(player.getId(), 0) + scoreEarned);

                    long correctCount = submissionRepository.findByRoundIdOrderBySubmittedAtAsc(round.getId())
                            .stream()
                            .filter(s -> s.getSubmissionType() == RoundSubmission.SubmissionType.GUESS
                                    && Boolean.TRUE.equals(s.getIsCorrect()))
                            .count();
                    if (correctCount == 1) {
                        scores.put(round.getDrawerId(),
                                scores.getOrDefault(round.getDrawerId(), 0) + DRAWER_BONUS_SCORE);
                    }

                    game.setScores(scores);
                    gameRepository.save(game);
                }

                log.info("猜词已提交: round={}, player={}, guess={}, correct={}",
                        round.getRoundNumber(), player.getNickname(), guess, isCorrect);

                checkRoundCompletion(game, round);

                Room room = getRoomForGame(game);
                return toRoomSnapshot(room);
            } finally {
                submissionLocks.remove(lockKey);
            }
        }
    }

    private void checkRoundCompletion(Game game, Round round) {
        List<Long> guesserIds = round.getGuesserIds();
        long submittedCount = guesserIds.stream()
                .filter(id -> submissionRepository.existsByRoundIdAndPlayerIdAndSubmissionType(
                        round.getId(), id, RoundSubmission.SubmissionType.GUESS))
                .count();

        if (submittedCount >= guesserIds.size()) {
            completeRound(game, round);
        }
    }

    private void completeRound(Game game, Round round) {
        round.setCompleted(true);
        round.setCompletedAt(LocalDateTime.now());
        roundRepository.save(round);

        game.setCompletedRounds(game.getCompletedRounds() + 1);
        game = gameRepository.save(game);

        log.info("轮次完成: gameId={}, round={}", game.getId(), round.getRoundNumber());

        Room room = getRoomForGame(game);
        room.setCurrentRound(game.getCompletedRounds() + 1);
        roomRepository.save(room);

        if (game.getCompletedRounds() >= game.getTotalRounds()) {
            endGame(room, game);
        } else {
            startNextRound(room, game);
        }
    }

    private void endGame(Room room, Game game) {
        Map<Long, Integer> scores = game.getScores();
        if (!scores.isEmpty()) {
            Map.Entry<Long, Integer> winner = scores.entrySet().stream()
                    .max(Map.Entry.comparingByValue())
                    .orElse(null);
            if (winner != null) {
                game.setWinnerId(winner.getKey());
                game.setWinnerNickname(game.getPlayerNicknames().get(winner.getKey()));
            }
        }
        game.setEndedAt(LocalDateTime.now());
        gameRepository.save(game);

        room.setStatus(RoomStatus.FINISHED);
        roomRepository.save(room);

        log.info("游戏结束: gameId={}, winner={}, scores={}",
                game.getId(), game.getWinnerNickname(), scores);
    }

    @Transactional(readOnly = true)
    public Page<GameHistoryResponse> getMyGames(Long playerId, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "startedAt"));
        Page<Game> gamePage = gameRepository.findByPlayerId(playerId, pageable);
        return gamePage.map(this::toGameHistoryResponse);
    }

    @Transactional(readOnly = true)
    public GameHistoryResponse getGameDetail(Long gameId) {
        Game game = getById(gameId);
        return toGameHistoryResponse(game);
    }

    @Transactional(readOnly = true)
    public Game getById(Long id) {
        return gameRepository.findById(id)
                .orElseThrow(() -> new GameException(404, "游戏不存在: " + id));
    }

    @Transactional(readOnly = true)
    public Optional<Round> getCurrentRound(Long gameId) {
        return roundRepository.findByGameIdAndCompletedFalse(gameId);
    }

    @Transactional(readOnly = true)
    public List<RoundSubmission> getRoundSubmissions(Long roundId) {
        return submissionRepository.findByRoundIdOrderBySubmittedAtAsc(roundId);
    }

    private Round getRound(Long gameId, Integer roundNumber) {
        return roundRepository.findByGameIdAndRoundNumber(gameId, roundNumber)
                .orElseThrow(() -> new GameException(404, "轮次不存在: game=" + gameId + ", round=" + roundNumber));
    }

    private Room getRoomForGame(Game game) {
        return roomRepository.findById(game.getRoomId())
                .orElseThrow(() -> new GameException(404, "房间不存在: " + game.getRoomId()));
    }

    private RoomSnapshotResponse toRoomSnapshot(Room room) {
        RoomSnapshotResponse response = new RoomSnapshotResponse();
        response.setRoomId(room.getId());
        response.setRoomCode(room.getRoomCode());
        response.setRoomName(room.getRoomName());
        response.setHasPassword(room.getPassword() != null && !room.getPassword().isEmpty());
        response.setMaxPlayers(room.getMaxPlayers());
        response.setTotalRounds(room.getTotalRounds());
        response.setStatus(room.getStatus());
        response.setOwnerId(room.getOwnerId());
        response.setOwnerNickname(playerService.getById(room.getOwnerId()).getNickname());
        response.setCurrentRound(room.getCurrentRound());
        response.setCurrentGameId(room.getCurrentGameId());

        List<RoomSnapshotResponse.PlayerInfo> playerInfos = room.getPlayerIds().stream()
                .map(pid -> {
                    Player p = playerService.getById(pid);
                    return new RoomSnapshotResponse.PlayerInfo(
                            p.getId(),
                            p.getNickname(),
                            p.getId().equals(room.getOwnerId()),
                            room.getReadyPlayerIds().contains(p.getId())
                    );
                })
                .collect(Collectors.toList());
        response.setPlayers(playerInfos);
        response.setReadyPlayerIds(room.getReadyPlayerIds());

        if (room.getCurrentGameId() != null) {
            Game game = getById(room.getCurrentGameId());
            response.setCurrentScores(new HashMap<>(game.getScores()));

            Optional<Round> currentRound = getCurrentRound(game.getId());
            if (currentRound.isPresent()) {
                Round round = currentRound.get();
                List<RoundSubmission> submissions = getRoundSubmissions(round.getId());
                List<RoomSnapshotResponse.SubmissionInfo> subInfos = submissions.stream()
                        .map(s -> new RoomSnapshotResponse.SubmissionInfo(
                                s.getPlayerId(),
                                s.getPlayerNickname(),
                                s.getSubmissionType().name(),
                                s.getContent(),
                                s.getIsCorrect(),
                                s.getScoreEarned()
                        ))
                        .collect(Collectors.toList());

                response.setCurrentRoundInfo(new RoomSnapshotResponse.RoundInfo(
                        round.getId(),
                        round.getRoundNumber(),
                        round.getDrawerId(),
                        round.getDrawerNickname(),
                        round.getDescription(),
                        subInfos,
                        round.getCompleted()
                ));
            }
        }

        return response;
    }

    private GameHistoryResponse toGameHistoryResponse(Game game) {
        List<Round> rounds = roundRepository.findByGameIdOrderByRoundNumberAsc(game.getId());
        List<RoundDetailResponse> roundDetails = rounds.stream()
                .map(this::toRoundDetailResponse)
                .collect(Collectors.toList());

        Room room = roomRepository.findById(game.getRoomId()).orElse(null);
        String roomName = room != null ? room.getRoomName() : "未知房间";

        return new GameHistoryResponse(
                game.getId(),
                game.getRoomCode(),
                roomName,
                game.getTotalRounds(),
                game.getCompletedRounds(),
                game.getWinnerId(),
                game.getWinnerNickname(),
                game.getScores(),
                game.getPlayerNicknames(),
                game.getStartedAt(),
                game.getEndedAt(),
                roundDetails
        );
    }

    private RoundDetailResponse toRoundDetailResponse(Round round) {
        List<RoundSubmission> submissions = submissionRepository.findByRoundIdOrderBySubmittedAtAsc(round.getId());
        List<SubmissionDetailResponse> subDetails = submissions.stream()
                .map(s -> new SubmissionDetailResponse(
                        s.getId(),
                        s.getPlayerId(),
                        s.getPlayerNickname(),
                        s.getSubmissionType().name(),
                        s.getContent(),
                        s.getIsCorrect(),
                        s.getScoreEarned(),
                        s.getSubmittedAt()
                ))
                .collect(Collectors.toList());

        return new RoundDetailResponse(
                round.getId(),
                round.getRoundNumber(),
                round.getDrawerId(),
                round.getDrawerNickname(),
                round.getTargetWord(),
                round.getDescription(),
                round.getCompleted(),
                round.getCreatedAt(),
                round.getCompletedAt(),
                subDetails
        );
    }
}
