package com.party.drawguess.repository;

import com.party.drawguess.model.Room;
import com.party.drawguess.model.RoomStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RoomRepository extends JpaRepository<Room, Long> {
    Optional<Room> findByRoomCode(String roomCode);
    boolean existsByRoomCode(String roomCode);
    Optional<Room> findByRoomCodeAndStatus(String roomCode, RoomStatus status);
}
