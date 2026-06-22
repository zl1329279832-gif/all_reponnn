package com.delivery.service;

import com.delivery.enums.OrderStatus;
import com.delivery.enums.TrackEventType;
import com.delivery.exception.StatusTransitionException;
import org.springframework.stereotype.Component;

import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

@Component
public class OrderStateMachine {

    private final Map<OrderStatus, Set<OrderStatus>> allowedTransitions;
    private final Map<TrackEventType, OrderStatus> eventToStatusMap;

    public OrderStateMachine() {
        allowedTransitions = new EnumMap<>(OrderStatus.class);
        eventToStatusMap = new EnumMap<>(TrackEventType.class);

        allowedTransitions.put(OrderStatus.PENDING_PICKUP, EnumSet.of(
                OrderStatus.PICKED_UP,
                OrderStatus.CANCELLED
        ));
        allowedTransitions.put(OrderStatus.PICKED_UP, EnumSet.of(
                OrderStatus.IN_TRANSIT,
                OrderStatus.CANCELLED
        ));
        allowedTransitions.put(OrderStatus.IN_TRANSIT, EnumSet.of(
                OrderStatus.DELIVERED,
                OrderStatus.CANCELLED
        ));
        allowedTransitions.put(OrderStatus.DELIVERED, EnumSet.noneOf(OrderStatus.class));
        allowedTransitions.put(OrderStatus.CANCELLED, EnumSet.noneOf(OrderStatus.class));

        eventToStatusMap.put(TrackEventType.ORDER_CREATED, OrderStatus.PENDING_PICKUP);
        eventToStatusMap.put(TrackEventType.ORDER_ASSIGNED, OrderStatus.PENDING_PICKUP);
        eventToStatusMap.put(TrackEventType.PICKUP_ARRIVED, OrderStatus.PENDING_PICKUP);
        eventToStatusMap.put(TrackEventType.PICKED_UP, OrderStatus.PICKED_UP);
        eventToStatusMap.put(TrackEventType.DELIVERY_TRANSIT, OrderStatus.IN_TRANSIT);
        eventToStatusMap.put(TrackEventType.DELIVERY_ARRIVED, OrderStatus.IN_TRANSIT);
        eventToStatusMap.put(TrackEventType.DELIVERED, OrderStatus.DELIVERED);
        eventToStatusMap.put(TrackEventType.CANCELLED, OrderStatus.CANCELLED);
    }

    public boolean canTransition(OrderStatus currentStatus, OrderStatus targetStatus) {
        if (currentStatus == null || targetStatus == null) {
            return false;
        }
        Set<OrderStatus> allowed = allowedTransitions.get(currentStatus);
        return allowed != null && allowed.contains(targetStatus);
    }

    public OrderStatus getStatusForEvent(TrackEventType eventType) {
        return eventToStatusMap.get(eventType);
    }

    public boolean isStatusAdvancing(OrderStatus currentStatus, TrackEventType eventType) {
        OrderStatus targetStatus = getStatusForEvent(eventType);
        if (targetStatus == null) {
            return false;
        }
        if (currentStatus == targetStatus) {
            return false;
        }
        return canTransition(currentStatus, targetStatus);
    }

    public void validateTransition(OrderStatus currentStatus, OrderStatus targetStatus) {
        if (!canTransition(currentStatus, targetStatus)) {
            throw new StatusTransitionException(
                    String.format("无法从状态 %s 流转到 %s", currentStatus, targetStatus)
            );
        }
    }

    public void validateEventTransition(OrderStatus currentStatus, TrackEventType eventType) {
        OrderStatus targetStatus = getStatusForEvent(eventType);
        if (targetStatus == null) {
            return;
        }
        if (currentStatus == targetStatus) {
            return;
        }
        validateTransition(currentStatus, targetStatus);
    }

    public boolean isFinalStatus(OrderStatus status) {
        return status == OrderStatus.DELIVERED || status == OrderStatus.CANCELLED;
    }
}
