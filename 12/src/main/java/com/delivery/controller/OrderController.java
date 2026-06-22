package com.delivery.controller;

import com.delivery.common.Result;
import com.delivery.dto.CreateOrderRequest;
import com.delivery.dto.MarkExceptionRequest;
import com.delivery.dto.OrderCallbackRequest;
import com.delivery.entity.DeliveryOrder;
import com.delivery.entity.TrackEvent;
import com.delivery.enums.OrderStatus;
import com.delivery.enums.TrackEventType;
import com.delivery.exception.BusinessException;
import com.delivery.service.OrderService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

    @PostMapping
    public Result<DeliveryOrder> createOrder(@Valid @RequestBody CreateOrderRequest request) {
        DeliveryOrder order = orderService.createOrder(request);
        return Result.success(order);
    }

    @GetMapping("/{orderNo}")
    public Result<DeliveryOrder> getOrder(@PathVariable String orderNo) {
        return orderService.getOrderByNo(orderNo)
                .map(Result::success)
                .orElseThrow(() -> new BusinessException("运单不存在"));
    }

    @GetMapping
    public Result<Page<DeliveryOrder>> listOrders(
            @RequestParam(required = false) OrderStatus status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createTime"));
        Page<DeliveryOrder> orders;
        if (status != null) {
            orders = orderService.listOrdersByStatus(status, pageable);
        } else {
            orders = orderService.listOrders(pageable);
        }
        return Result.success(orders);
    }

    @PostMapping("/{orderNo}/accept")
    public Result<DeliveryOrder> acceptOrder(
            @PathVariable String orderNo,
            @RequestParam Long riderId) {
        DeliveryOrder order = orderService.acceptOrder(orderNo, riderId);
        return Result.success(order);
    }

    @PostMapping("/{orderNo}/callback")
    public Result<DeliveryOrder> callback(
            @PathVariable String orderNo,
            @RequestBody OrderCallbackRequest request) {
        TrackEventType eventType;
        try {
            eventType = TrackEventType.valueOf(request.getEventType());
        } catch (IllegalArgumentException e) {
            throw new BusinessException("无效的事件类型");
        }

        DeliveryOrder order = orderService.processCallback(
                orderNo,
                eventType,
                request.getRequestId(),
                request.getDescription(),
                request.getLatitude(),
                request.getLongitude(),
                request.getOperator()
        );
        return Result.success(order);
    }

    @PostMapping("/{orderNo}/cancel")
    public Result<DeliveryOrder> cancelOrder(
            @PathVariable String orderNo,
            @RequestParam(required = false) String reason,
            @RequestParam(required = false) String operator) {
        DeliveryOrder order = orderService.cancelOrder(orderNo, reason, operator);
        return Result.success(order);
    }

    @GetMapping("/{orderNo}/timeline")
    public Result<List<TrackEvent>> getTimeline(@PathVariable String orderNo) {
        List<TrackEvent> timeline = orderService.getOrderTimeline(orderNo);
        return Result.success(timeline);
    }

    @PostMapping("/{orderNo}/exception")
    public Result<DeliveryOrder> markException(
            @PathVariable String orderNo,
            @RequestBody MarkExceptionRequest request) {
        DeliveryOrder order = orderService.markException(
                orderNo,
                request.getReason(),
                request.getRequestId(),
                request.getLatitude(),
                request.getLongitude(),
                request.getOperator()
        );
        return Result.success(order);
    }

    @GetMapping("/rider/{riderId}")
    public Result<Page<DeliveryOrder>> getRiderOrders(
            @PathVariable Long riderId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createTime"));
        Page<DeliveryOrder> orders = orderService.listOrdersByRider(riderId, pageable);
        return Result.success(orders);
    }
}
