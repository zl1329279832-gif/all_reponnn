package com.party.drawguess.service;

import com.party.drawguess.dto.*;
import com.party.drawguess.exception.GameException;
import com.party.drawguess.model.*;
import com.party.drawguess.repository.RoomRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class RoomService {
    private final RoomRepository roomRepository;
    private final PlayerService playerService;
    private final GameService gameService;

    @Autowired
    @Lazy
    private RoomService self;

    private static final Map<String, Object> roomLocks = new ConcurrentHashMap<>();

    private static final String ROOM_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    private static final int ROOM_CODE_LENGTH = 6;
    private static final SecureRandom random = new SecureRandom();

    @Transactional
    public RoomSnapshotResponse createRoom(CreateRoomRequest request) {
        Player owner = playerService.getById(request.getOwnerId());

        String roomCode = generateRoomCode();

        Room room = new Room();
        room.setRoomCode(roomCode);
        room.setRoomName(request.getRoomName());
        room.setPassword(request.getPassword());
        room.setMaxPlayers(request.getMaxPlayers());
        room.setTotalRounds(request.getTotalRounds());
        room.setOwnerId(owner.getId());
        room.getPlayerIds().add(owner.getId());
        room.getReadyPlayerIds().add(owner.getId());

        room = roomRepository.save(room);
        log.info("房间创建成功: code={}, owner={}", roomCode, owner.getNickname());
        return getRoomSnapshot(room.getId());
    }

    public RoomSnapshotResponse joinRoom(JoinRoomRequest request) {
        String roomCode = request.getRoomCode().toUpperCase();

        Object lock = roomLocks.computeIfAbsent(roomCode, k -> new Object());

        synchronized (lock) {
            int maxRetries = 3;
            int retryCount = 0;
            while (true) {
                try {
                    return self.doJoinInTransaction(request, roomCode);
                } catch (OptimisticLockingFailureException e) {
                    retryCount++;
                    if (retryCount >= maxRetries) {
                        throw new GameException(409, "加入房间冲突，请稍后重试");
                    }
                    log.warn("乐观锁冲突，重试加入房间: roomCode={}, retry={}", roomCode, retryCount);
                    try {
                        Thread.sleep(50);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new GameException(500, "加入房间被中断");
                    }
                }
            }
        }
    }

    @Transactional
    public RoomSnapshotResponse doJoinInTransaction(JoinRoomRequest request, String roomCode) {
        Player player = playerService.getById(request.getPlayerId());

        Room room = roomRepository.findByRoomCode(roomCode)
                .orElseThrow(() -> new GameException(404, "房间不存在: " + roomCode));

        if (room.getStatus() != RoomStatus.WAITING) {
            throw new GameException("房间已开始或已结束，无法加入");
        }

        if (room.getPassword() != null && !room.getPassword().isEmpty()) {
            if (request.getPassword() == null || !request.getPassword().equals(room.getPassword())) {
                throw new GameException(401, "房间密码错误");
            }
        }

        if (room.getPlayerIds().contains(player.getId())) {
            throw new GameException(409, "你已在该房间中");
        }

        if (room.getPlayerIds().size() >= room.getMaxPlayers()) {
            throw new GameException(409, "房间已满");
        }

        room.getPlayerIds().add(player.getId());
        room = roomRepository.save(room);
        log.info("玩家加入房间: room={}, player={}, 人数={}/{}",
                roomCode, player.getNickname(),
                room.getPlayerIds().size(), room.getMaxPlayers());
        return getRoomSnapshot(room.getId());
    }

    @Transactional
    public RoomSnapshotResponse ready(ReadyRequest request) {
        Player player = playerService.getById(request.getPlayerId());
        Room room = getById(request.getRoomId());

        if (room.getStatus() != RoomStatus.WAITING) {
            throw new GameException("房间已开始或已结束，无法准备");
        }

        if (!room.getPlayerIds().contains(player.getId())) {
            throw new GameException("你不在该房间中");
        }

        if (!room.getReadyPlayerIds().contains(player.getId())) {
            room.getReadyPlayerIds().add(player.getId());
            room = roomRepository.save(room);
            log.info("玩家准备: room={}, player={}", room.getRoomCode(), player.getNickname());
        }

        return getRoomSnapshot(room.getId());
    }

    @Transactional
    public RoomSnapshotResponse startGame(StartGameRequest request) {
        Room room = getById(request.getRoomId());
        Player owner = playerService.getById(request.getOwnerId());

        if (room.getStatus() != RoomStatus.WAITING) {
            throw new GameException("房间已开始或已结束");
        }

        if (!room.getOwnerId().equals(owner.getId())) {
            throw new GameException(403, "只有房主可以开始游戏");
        }

        if (room.getPlayerIds().size() < 2) {
            throw new GameException("至少需要 2 名玩家才能开始");
        }

        if (room.getReadyPlayerIds().size() < room.getPlayerIds().size()) {
            throw new GameException("还有玩家未准备");
        }

        room.setStatus(RoomStatus.PLAYING);
        room.setCurrentRound(1);
        room.getReadyPlayerIds().clear();
        room = roomRepository.save(room);

        Game game = gameService.createGame(room);
        room.setCurrentGameId(game.getId());
        room = roomRepository.save(room);

        gameService.startNextRound(room, game);

        log.info("游戏开始: room={}, gameId={}", room.getRoomCode(), game.getId());
        return getRoomSnapshot(room.getId());
    }

    @Transactional(readOnly = true)
    public RoomSnapshotResponse getRoomSnapshot(Long roomId) {
        Room room = getById(roomId);
        Player owner = playerService.getById(room.getOwnerId());

        List<RoomSnapshotResponse.PlayerInfo> playerInfos = room.getPlayerIds().stream()
                .map(playerId -> {
                    Player p = playerService.getById(playerId);
                    return new RoomSnapshotResponse.PlayerInfo(
                            p.getId(),
                            p.getNickname(),
                            p.getId().equals(room.getOwnerId()),
                            room.getReadyPlayerIds().contains(p.getId())
                    );
                })
                .collect(Collectors.toList());

        Map<Long, Integer> currentScores = new HashMap<>();
        RoomSnapshotResponse.RoundInfo currentRoundInfo = null;

        if (room.getCurrentGameId() != null) {
            Game game = gameService.getById(room.getCurrentGameId());
            currentScores = new HashMap<>(game.getScores());

            Optional<Round> currentRound = gameService.getCurrentRound(game.getId());
            if (currentRound.isPresent()) {
                Round round = currentRound.get();
                List<RoundSubmission> submissions = gameService.getRoundSubmissions(round.getId());

                List<RoomSnapshotResponse.SubmissionInfo> submissionInfos = submissions.stream()
                        .map(s -> new RoomSnapshotResponse.SubmissionInfo(
                                s.getPlayerId(),
                                s.getPlayerNickname(),
                                s.getSubmissionType().name(),
                                s.getContent(),
                                s.getIsCorrect(),
                                s.getScoreEarned()
                        ))
                        .collect(Collectors.toList());

                currentRoundInfo = new RoomSnapshotResponse.RoundInfo(
                        round.getId(),
                        round.getRoundNumber(),
                        round.getDrawerId(),
                        round.getDrawerNickname(),
                        round.getDescription(),
                        submissionInfos,
                        round.getCompleted()
                );
            }
        }

        return new RoomSnapshotResponse(
                room.getId(),
                room.getRoomCode(),
                room.getRoomName(),
                room.getPassword() != null && !room.getPassword().isEmpty(),
                room.getMaxPlayers(),
                room.getTotalRounds(),
                room.getStatus(),
                room.getOwnerId(),
                owner.getNickname(),
                room.getCurrentRound(),
                room.getCurrentGameId(),
                playerInfos,
                room.getReadyPlayerIds(),
                currentScores,
                currentRoundInfo
        );
    }

    @Transactional(readOnly = true)
    public Room getById(Long id) {
        return roomRepository.findById(id)
                .orElseThrow(() -> new GameException(404, "房间不存在: " + id));
    }

    @Transactional(readOnly = true)
    public Room getByCode(String code) {
        return roomRepository.findByRoomCode(code.toUpperCase())
                .orElseThrow(() -> new GameException(404, "房间不存在: " + code));
    }

    @Transactional
    public Room save(Room room) {
        return roomRepository.save(room);
    }

    private String generateRoomCode() {
        String code;
        int maxAttempts = 100;
        int attempts = 0;
        do {
            StringBuilder sb = new StringBuilder(ROOM_CODE_LENGTH);
            for (int i = 0; i < ROOM_CODE_LENGTH; i++) {
                sb.append(ROOM_CODE_CHARS.charAt(random.nextInt(ROOM_CODE_CHARS.length())));
            }
            code = sb.toString();
            attempts++;
            if (attempts > maxAttempts) {
                throw new GameException(500, "生成房间码失败，请稍后重试");
            }
        } while (roomRepository.existsByRoomCode(code));
        return code;
    }
}
