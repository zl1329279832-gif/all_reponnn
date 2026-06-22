package com.delivery.repository;

import com.delivery.entity.TrackEvent;
import com.delivery.enums.TrackEventType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TrackEventRepository extends JpaRepository<TrackEvent, Long> {

    List<TrackEvent> findByOrderNoOrderByEventTimeAsc(String orderNo);

    List<TrackEvent> findByOrderNoOrderByEventTimeDesc(String orderNo);

    Optional<TrackEvent> findFirstByOrderNoOrderByEventTimeDesc(String orderNo);

    Optional<TrackEvent> findByOrderNoAndEventType(String orderNo, TrackEventType eventType);

    boolean existsByOrderNoAndEventType(String orderNo, TrackEventType eventType);
}
