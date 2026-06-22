package com.delivery.service;

import com.delivery.dto.CreateOrderRequest;
import com.delivery.entity.DeliveryOrder;
import com.delivery.entity.Rider;
import com.delivery.entity.TrackEvent;
import com.delivery.enums.OrderStatus;
import com.delivery.enums.RiderStatus;
import com.delivery.enums.TrackEventType;
import com.delivery.exception.BusinessException;
import com.delivery.exception.StatusTransitionException;
import com.delivery.repository.DeliveryOrderRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class OrderService {

    private final DeliveryOrderRepository orderRepository;
    private final OrderStateMachine stateMachine;
    private final DispatchService dispatchService;
    private final RiderService riderService;
    private final TrackEventService trackEventService;
    private final IdempotentService idempotentService;

    @Transactional
    public DeliveryOrder createOrder(CreateOrderRequest request) {
        String orderNo = generateOrderNo();

        DeliveryOrder order = new DeliveryOrder();
        order.setOrderNo(orderNo);
        order.setMerchantName(request.getMerchantName());
        order.setPickupAddress(request.getPickupAddress());
        order.setPickupLatitude(request.getPickupLatitude());
        order.setPickupLongitude(request.getPickupLongitude());
        order.setDeliveryAddress(request.getDeliveryAddress());
        order.setDeliveryLatitude(request.getDeliveryLatitude());
        order.setDeliveryLongitude(request.getDeliveryLongitude());
        order.setReceiverName(request.getReceiverName());
        order.setReceiverPhone(request.getReceiverPhone());
        order.setOrderAmount(request.getOrderAmount());
        order.setDeliveryFee(request.getDeliveryFee());
        order.setRemark(request.getRemark());
        order.setStatus(OrderStatus.PENDING_PICKUP);
        order.setDeducted(false);

        if (request.getDeliveryLatitude() != null && request.getDeliveryLongitude() != null) {
            order.setGridCode(dispatchService.calculateGridCode(
                    request.getDeliveryLatitude(), request.getDeliveryLongitude()));
        }

        order = orderRepository.save(order);

        trackEventService.addEvent(
                orderNo,
                TrackEventType.ORDER_CREATED,
                "商家下单，运单创建成功",
                null,
                request.getPickupLatitude(),
                request.getPickupLongitude(),
                "SYSTEM"
        );

        autoDispatch(order);

        return order;
    }

    private void autoDispatch(DeliveryOrder order) {
        if (order.getRiderId() != null) {
            return;
        }

        Rider bestRider = dispatchService.findBestRider(
                order.getGridCode(),
                order.getDeliveryLatitude(),
                order.getDeliveryLongitude()
        );

        if (bestRider != null) {
            assignRider(order, bestRider);
        }
    }

    @Transactional
    public DeliveryOrder assignRider(DeliveryOrder order, Rider rider) {
        if (order.getRiderId() != null) {
            throw new BusinessException("运单已分配骑手，如需改派请使用改派接口");
        }

        if (rider.getStatus() != RiderStatus.IDLE) {
            throw new BusinessException("骑手当前不可接单");
        }

        order.setRiderId(rider.getId());
        order.setRiderName(rider.getName());
        order.setRiderPhone(rider.getPhone());
        order = orderRepository.save(order);

        riderService.incrementOrderCount(rider.getId());

        trackEventService.addEvent(
                order.getOrderNo(),
                TrackEventType.ORDER_ASSIGNED,
                String.format("骑手 %s 接单", rider.getName()),
                rider.getId(),
                rider.getLatitude(),
                rider.getLongitude(),
                "SYSTEM"
        );

        return order;
    }

    @Transactional
    public DeliveryOrder acceptOrder(String orderNo, Long riderId) {
        DeliveryOrder order = orderRepository.findByOrderNoWithLock(orderNo)
                .orElseThrow(() -> new BusinessException("运单不存在"));

        if (order.getStatus() != OrderStatus.PENDING_PICKUP) {
            throw new StatusTransitionException("当前状态不可接单");
        }

        if (order.getRiderId() != null) {
            if (!order.getRiderId().equals(riderId)) {
                throw new BusinessException("运单已被其他骑手接单");
            }
            return order;
        }

        Rider rider = riderService.getRider(riderId)
                .orElseThrow(() -> new BusinessException("骑手不存在"));

        if (rider.getStatus() != RiderStatus.IDLE) {
            throw new BusinessException("骑手当前不可接单");
        }

        order.setRiderId(rider.getId());
        order.setRiderName(rider.getName());
        order.setRiderPhone(rider.getPhone());
        riderService.incrementOrderCount(riderId);

        trackEventService.addEvent(
                orderNo,
                TrackEventType.ORDER_ASSIGNED,
                String.format("骑手 %s 接单", rider.getName()),
                riderId,
                rider.getLatitude(),
                rider.getLongitude(),
                "RIDER"
        );

        return orderRepository.save(order);
    }

    @Transactional
    public DeliveryOrder processCallback(String orderNo, TrackEventType eventType,
                                         String requestId, String description,
                                         Double latitude, Double longitude,
                                         String operator) {
        String idempotentKey = requestId != null ? requestId :
                String.format("%s_%s", orderNo, eventType);

        boolean isNew = idempotentService.checkAndRecord(idempotentKey, orderNo, eventType.name());
        if (!isNew) {
            return orderRepository.findByOrderNo(orderNo).orElseThrow(
                    () -> new BusinessException("运单不存在"));
        }

        DeliveryOrder order = orderRepository.findByOrderNoWithLock(orderNo)
                .orElseThrow(() -> new BusinessException("运单不存在"));

        stateMachine.validateEventTransition(order.getStatus(), eventType);

        OrderStatus targetStatus = stateMachine.getStatusForEvent(eventType);
        if (targetStatus != null && targetStatus != order.getStatus()) {
            if (targetStatus == OrderStatus.PICKED_UP) {
                order.setPickupTime(LocalDateTime.now());
                order.setDeducted(true);
            }
            if (targetStatus == OrderStatus.DELIVERED) {
                order.setDeliveryTime(LocalDateTime.now());
            }
            order.setStatus(targetStatus);
        }

        Long riderId = order.getRiderId();

        trackEventService.addEvent(
                orderNo,
                eventType,
                description,
                riderId,
                latitude,
                longitude,
                operator
        );

        if (targetStatus == OrderStatus.DELIVERED && riderId != null) {
            riderService.decrementOrderCount(riderId);
        }

        return orderRepository.save(order);
    }

    @Transactional
    public DeliveryOrder cancelOrder(String orderNo, String reason, String operator) {
        DeliveryOrder order = orderRepository.findByOrderNoWithLock(orderNo)
                .orElseThrow(() -> new BusinessException("运单不存在"));

        if (order.getStatus() == OrderStatus.DELIVERED || order.getStatus() == OrderStatus.CANCELLED) {
            throw new StatusTransitionException("当前状态不可取消");
        }

        boolean wasDeducted = Boolean.TRUE.equals(order.getDeducted());
        OrderStatus previousStatus = order.getStatus();

        order.setStatus(OrderStatus.CANCELLED);
        order.setCancelTime(LocalDateTime.now());

        if (wasDeducted) {
            order.setDeducted(false);
            trackEventService.addEvent(
                    orderNo,
                    TrackEventType.CANCELLED_ROLLBACK,
                    "已揽收后取消，回滚扣款标记",
                    order.getRiderId(),
                    null,
                    null,
                    operator
            );
        }

        trackEventService.addEvent(
                orderNo,
                TrackEventType.CANCELLED,
                reason != null ? reason : "运单取消",
                order.getRiderId(),
                null,
                null,
                operator
        );

        if (order.getRiderId() != null) {
            riderService.decrementOrderCount(order.getRiderId());
        }

        return orderRepository.save(order);
    }

    @Transactional
    public DeliveryOrder reassignOrder(String orderNo, Long targetRiderId,
                                       String reason, String operator) {
        DeliveryOrder order = orderRepository.findByOrderNoWithLock(orderNo)
                .orElseThrow(() -> new BusinessException("运单不存在"));

        if (order.getStatus() == OrderStatus.DELIVERED || order.getStatus() == OrderStatus.CANCELLED) {
            throw new StatusTransitionException("终态运单不可改派");
        }

        if (order.getRiderId() != null && order.getRiderId().equals(targetRiderId)) {
            throw new BusinessException("目标骑手与当前骑手相同");
        }

        Long oldRiderId = order.getRiderId();

        Rider targetRider = riderService.getRider(targetRiderId)
                .orElseThrow(() -> new BusinessException("目标骑手不存在"));

        if (targetRider.getStatus() == RiderStatus.OFFLINE) {
            throw new BusinessException("目标骑手已离线");
        }

        order.setRiderId(targetRiderId);
        order.setRiderName(targetRider.getName());
        order.setRiderPhone(targetRider.getPhone());

        if (oldRiderId != null) {
            riderService.decrementOrderCount(oldRiderId);
        }
        riderService.incrementOrderCount(targetRiderId);

        trackEventService.addEvent(
                orderNo,
                TrackEventType.REASSIGNED,
                reason != null ? String.format("改派原因：%s", reason) : "运单改派",
                targetRiderId,
                targetRider.getLatitude(),
                targetRider.getLongitude(),
                operator
        );

        return orderRepository.save(order);
    }

    public Optional<DeliveryOrder> getOrderByNo(String orderNo) {
        return orderRepository.findByOrderNo(orderNo);
    }

    public Page<DeliveryOrder> listOrders(Pageable pageable) {
        return orderRepository.findAll(pageable);
    }

    public Page<DeliveryOrder> listOrdersByStatus(OrderStatus status, Pageable pageable) {
        return orderRepository.findByStatus(status, pageable);
    }

    public Page<DeliveryOrder> listOrdersByRider(Long riderId, Pageable pageable) {
        return orderRepository.findByRiderId(riderId, pageable);
    }

    public List<TrackEvent> getOrderTimeline(String orderNo) {
        return trackEventService.getTimeline(orderNo);
    }

    private String generateOrderNo() {
        return "OD" + System.currentTimeMillis() +
                UUID.randomUUID().toString().substring(0, 6).toUpperCase();
    }
}
