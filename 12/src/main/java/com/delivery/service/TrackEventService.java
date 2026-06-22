package com.delivery.service;

import com.delivery.entity.TrackEvent;
import com.delivery.enums.TrackEventType;
import com.delivery.repository.TrackEventRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class TrackEventService {

    private final TrackEventRepository trackEventRepository;

    @Transactional
    public TrackEvent addEvent(String orderNo, TrackEventType eventType, String description,
                                Long riderId, Double latitude, Double longitude, String operator) {
        if (trackEventRepository.existsByOrderNoAndEventType(orderNo, eventType)) {
            return trackEventRepository.findByOrderNoAndEventType(orderNo, eventType).get();
        }

        TrackEvent event = new TrackEvent();
        event.setOrderNo(orderNo);
        event.setEventType(eventType);
        event.setDescription(description != null ? description : eventType.getDescription());
        event.setRiderId(riderId);
        event.setLatitude(latitude);
        event.setLongitude(longitude);
        event.setOperator(operator);
        return trackEventRepository.save(event);
    }

    public List<TrackEvent> getTimeline(String orderNo) {
        return trackEventRepository.findByOrderNoOrderByEventTimeAsc(orderNo);
    }

    public Optional<TrackEvent> getLatestEvent(String orderNo) {
        return trackEventRepository.findFirstByOrderNoOrderByEventTimeDesc(orderNo);
    }

    public boolean hasEvent(String orderNo, TrackEventType eventType) {
        return trackEventRepository.existsByOrderNoAndEventType(orderNo, eventType);
    }
}
