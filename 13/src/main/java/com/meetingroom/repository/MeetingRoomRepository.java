package com.meetingroom.repository;

import com.meetingroom.entity.MeetingRoom;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface MeetingRoomRepository extends JpaRepository<MeetingRoom, Long> {

    List<MeetingRoom> findByFloor(Integer floor);

    List<MeetingRoom> findByCapacityGreaterThanEqual(Integer capacity);

    @Query("SELECT r FROM MeetingRoom r WHERE r.floor = :floor AND r.capacity >= :capacity")
    List<MeetingRoom> findByFloorAndCapacity(
            @Param("floor") Integer floor,
            @Param("capacity") Integer capacity);
}
