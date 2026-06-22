package com.delivery.controller;

import com.delivery.common.Result;
import com.delivery.dto.ReassignRequest;
import com.delivery.dto.RedispatchRequest;
import com.delivery.entity.DeliveryOrder;
import com.delivery.service.DispatchService;
import com.delivery.service.OrderService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {

    private final OrderService orderService;
    private final DispatchService dispatchService;

    @PostMapping("/orders/reassign")
    public Result<DeliveryOrder> reassignOrder(@RequestBody ReassignRequest request) {
        DeliveryOrder order = orderService.reassignOrder(
                request.getOrderNo(),
                request.getTargetRiderId(),
                request.getReason(),
                request.getOperator()
        );
        return Result.success(order);
    }

    @PostMapping("/orders/redispatch")
    public Result<DeliveryOrder> redispatchOrder(@RequestBody RedispatchRequest request) {
        DeliveryOrder order = orderService.redispatchOrder(
                request.getOrderNo(),
                request.getTargetRiderId(),
                request.getOperator()
        );
        return Result.success(order);
    }

    @PostMapping("/orders/{orderNo}/cancel")
    public Result<DeliveryOrder> adminCancelOrder(
            @PathVariable String orderNo,
            @RequestParam(required = false) String reason,
            @RequestParam(required = false) String operator) {
        DeliveryOrder order = orderService.cancelOrder(orderNo, reason, operator);
        return Result.success(order);
    }
}
