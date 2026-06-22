package com.delivery;

import com.delivery.dto.CreateOrderRequest;
import com.delivery.dto.CreateRiderRequest;
import com.delivery.entity.DeliveryOrder;
import com.delivery.entity.Rider;
import com.delivery.entity.TrackEvent;
import com.delivery.enums.OrderStatus;
import com.delivery.enums.RiderStatus;
import com.delivery.enums.TrackEventType;
import com.delivery.exception.BusinessException;
import com.delivery.exception.StatusTransitionException;
import com.delivery.service.OrderService;
import com.delivery.service.OrderStateMachine;
import com.delivery.service.RiderService;
import com.delivery.service.TrackEventService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@Transactional
class OrderServiceIntegrationTest {

    @Autowired
    private OrderService orderService;

    @Autowired
    private RiderService riderService;

    @Autowired
    private OrderStateMachine stateMachine;

    @Autowired
    private TrackEventService trackEventService;

    private Rider testRider;

    @BeforeEach
    void setUp() {
        CreateRiderRequest riderRequest = new CreateRiderRequest();
        riderRequest.setRiderNo("R001");
        riderRequest.setName("测试骑手");
        riderRequest.setPhone("13800138000");
        riderRequest.setLatitude(39.9042);
        riderRequest.setLongitude(116.4074);
        testRider = riderService.createRider(riderRequest);
    }

    @Test
    @DisplayName("创建运单 - 成功")
    void testCreateOrder_Success() {
        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setPickupLatitude(39.9042);
        request.setPickupLongitude(116.4074);
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9142);
        request.setDeliveryLongitude(116.4174);
        request.setReceiverName("张三");
        request.setReceiverPhone("13900139000");
        request.setOrderAmount(new BigDecimal("100.00"));
        request.setDeliveryFee(new BigDecimal("8.00"));

        DeliveryOrder order = orderService.createOrder(request);

        assertNotNull(order);
        assertNotNull(order.getOrderNo());
        assertTrue(order.getOrderNo().startsWith("OD"));
        assertEquals(OrderStatus.PENDING_PICKUP, order.getStatus());
        assertEquals("测试商家", order.getMerchantName());
        assertNotNull(order.getGridCode());
    }

    @Test
    @DisplayName("状态机 - 正常流转路径")
    void testStateMachine_NormalFlow() {
        assertTrue(stateMachine.canTransition(OrderStatus.PENDING_PICKUP, OrderStatus.PICKED_UP));
        assertTrue(stateMachine.canTransition(OrderStatus.PICKED_UP, OrderStatus.IN_TRANSIT));
        assertTrue(stateMachine.canTransition(OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED));
    }

    @Test
    @DisplayName("状态机 - 禁止的流转")
    void testStateMachine_ForbiddenTransitions() {
        assertFalse(stateMachine.canTransition(OrderStatus.PENDING_PICKUP, OrderStatus.DELIVERED));
        assertFalse(stateMachine.canTransition(OrderStatus.DELIVERED, OrderStatus.CANCELLED));
        assertFalse(stateMachine.canTransition(OrderStatus.CANCELLED, OrderStatus.PENDING_PICKUP));
    }

    @Test
    @DisplayName("状态机 - 终态判断")
    void testStateMachine_FinalStatus() {
        assertTrue(stateMachine.isFinalStatus(OrderStatus.DELIVERED));
        assertTrue(stateMachine.isFinalStatus(OrderStatus.CANCELLED));
        assertFalse(stateMachine.isFinalStatus(OrderStatus.PENDING_PICKUP));
        assertFalse(stateMachine.isFinalStatus(OrderStatus.PICKED_UP));
    }

    @Test
    @DisplayName("运单状态流转 - 正常配送全流程")
    @Transactional
    void testOrderStatusFlow_FullDelivery() {
        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());
        assertEquals(OrderStatus.PENDING_PICKUP, order.getStatus());
        assertEquals(testRider.getId(), order.getRiderId());

        order = orderService.processCallback(orderNo, TrackEventType.PICKED_UP,
                "req-pickup-001", "已取货", 39.9042, 116.4074, "RIDER");
        assertEquals(OrderStatus.PICKED_UP, order.getStatus());
        assertNotNull(order.getPickupTime());
        assertTrue(order.getDeducted());

        order = orderService.processCallback(orderNo, TrackEventType.DELIVERY_TRANSIT,
                "req-transit-001", "配送中", 39.9092, 116.4124, "RIDER");
        assertEquals(OrderStatus.IN_TRANSIT, order.getStatus());

        order = orderService.processCallback(orderNo, TrackEventType.DELIVERED,
                "req-delivered-001", "已签收", 39.9142, 116.4174, "RIDER");
        assertEquals(OrderStatus.DELIVERED, order.getStatus());
        assertNotNull(order.getDeliveryTime());
    }

    @Test
    @DisplayName("幂等性 - 重复回调同一事件只推进一次")
    void testIdempotent_DuplicateCallback() {
        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());

        DeliveryOrder result1 = orderService.processCallback(orderNo, TrackEventType.PICKED_UP,
                "req-idem-001", "第一次回调", 39.9042, 116.4074, "RIDER");
        assertEquals(OrderStatus.PICKED_UP, result1.getStatus());

        DeliveryOrder result2 = orderService.processCallback(orderNo, TrackEventType.PICKED_UP,
                "req-idem-001", "重复回调", 39.9042, 116.4074, "RIDER");
        assertEquals(OrderStatus.PICKED_UP, result2.getStatus());
        assertEquals(result1.getId(), result2.getId());

        List<TrackEvent> events = trackEventService.getTimeline(orderNo);
        long pickedUpCount = events.stream()
                .filter(e -> e.getEventType() == TrackEventType.PICKED_UP)
                .count();
        assertEquals(1, pickedUpCount);
    }

    @Test
    @DisplayName("乱序回调 - 直接跳到终态会被拒绝")
    void testOutOfOrderCallback_JumpToFinal() {
        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());

        assertThrows(StatusTransitionException.class, () -> {
            orderService.processCallback(orderNo, TrackEventType.DELIVERED,
                    "req-outoforder-001", "乱序回调", null, null, "RIDER");
        });

        DeliveryOrder finalOrder = orderService.getOrderByNo(orderNo).get();
        assertEquals(OrderStatus.PENDING_PICKUP, finalOrder.getStatus());
    }

    @Test
    @DisplayName("运单取消 - 待揽收状态取消成功")
    void testCancelOrder_PendingPickup() {
        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());

        DeliveryOrder cancelledOrder = orderService.cancelOrder(orderNo, "用户取消", "USER");
        assertEquals(OrderStatus.CANCELLED, cancelledOrder.getStatus());
        assertNotNull(cancelledOrder.getCancelTime());
        assertFalse(cancelledOrder.getDeducted());

        assertTrue(trackEventService.hasEvent(orderNo, TrackEventType.CANCELLED));
    }

    @Test
    @DisplayName("运单取消 - 已揽收后取消回滚扣款标记")
    void testCancelOrder_PickedUp_RollbackDeduction() {
        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());
        order = orderService.processCallback(orderNo, TrackEventType.PICKED_UP,
                "req-cancel-test-001", "已取货", 39.9042, 116.4074, "RIDER");
        assertTrue(order.getDeducted());

        DeliveryOrder cancelledOrder = orderService.cancelOrder(orderNo, "商家取消", "MERCHANT");
        assertEquals(OrderStatus.CANCELLED, cancelledOrder.getStatus());
        assertFalse(cancelledOrder.getDeducted(), "已揽收后取消应回滚扣款标记");

        assertTrue(trackEventService.hasEvent(orderNo, TrackEventType.CANCELLED_ROLLBACK),
                "应有取消回滚轨迹事件");
    }

    @Test
    @DisplayName("运单取消 - 已签收状态不能取消")
    void testCancelOrder_DeliveredCannotCancel() {
        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());
        order = orderService.processCallback(orderNo, TrackEventType.PICKED_UP,
                "req-cancel-test-002", "已取货", 39.9042, 116.4074, "RIDER");
        order = orderService.processCallback(orderNo, TrackEventType.DELIVERY_TRANSIT,
                "req-cancel-test-003", "配送中", 39.9092, 116.4124, "RIDER");
        order = orderService.processCallback(orderNo, TrackEventType.DELIVERED,
                "req-cancel-test-004", "已签收", 39.9142, 116.4174, "RIDER");

        assertThrows(StatusTransitionException.class, () -> {
            orderService.cancelOrder(orderNo, "想取消", "USER");
        });
    }

    @Test
    @DisplayName("运单改派 - 成功改派")
    void testReassignOrder_Success() {
        CreateRiderRequest riderRequest2 = new CreateRiderRequest();
        riderRequest2.setRiderNo("R002");
        riderRequest2.setName("骑手二号");
        riderRequest2.setLatitude(39.9052);
        riderRequest2.setLongitude(116.4084);
        Rider rider2 = riderService.createRider(riderRequest2);

        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());
        assertEquals(testRider.getId(), order.getRiderId());

        DeliveryOrder reassignedOrder = orderService.reassignOrder(
                orderNo, rider2.getId(), "测试改派", "ADMIN");

        assertEquals(rider2.getId(), reassignedOrder.getRiderId());
        assertEquals(rider2.getName(), reassignedOrder.getRiderName());
        assertTrue(trackEventService.hasEvent(orderNo, TrackEventType.REASSIGNED));
    }

    @Test
    @DisplayName("运单改派 - 终态运单不可改派")
    void testReassignOrder_FinalStatusForbidden() {
        CreateRiderRequest riderRequest2 = new CreateRiderRequest();
        riderRequest2.setRiderNo("R003");
        riderRequest2.setName("骑手三号");
        Rider rider2 = riderService.createRider(riderRequest2);

        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());
        order = orderService.processCallback(orderNo, TrackEventType.PICKED_UP,
                "req-reassign-test-001", "已取货", 39.9042, 116.4074, "RIDER");
        order = orderService.processCallback(orderNo, TrackEventType.DELIVERY_TRANSIT,
                "req-reassign-test-002", "配送中", 39.9092, 116.4124, "RIDER");
        order = orderService.processCallback(orderNo, TrackEventType.DELIVERED,
                "req-reassign-test-003", "已签收", 39.9142, 116.4174, "RIDER");

        final String finalOrderNo = orderNo;
        assertThrows(StatusTransitionException.class, () -> {
            orderService.reassignOrder(finalOrderNo, rider2.getId(), "想改派", "ADMIN");
        });
    }

    @Test
    @DisplayName("轨迹时间线 - 按时间正序排列")
    void testTrackTimeline_Ordering() {
        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());
        order = orderService.processCallback(orderNo, TrackEventType.PICKED_UP,
                "req-timeline-001", "已取货", 39.9042, 116.4074, "RIDER");
        order = orderService.processCallback(orderNo, TrackEventType.DELIVERY_TRANSIT,
                "req-timeline-002", "配送中", 39.9092, 116.4124, "RIDER");

        List<TrackEvent> timeline = trackEventService.getTimeline(orderNo);
        assertNotNull(timeline);
        assertTrue(timeline.size() >= 3);

        for (int i = 1; i < timeline.size(); i++) {
            assertTrue(
                    timeline.get(i - 1).getEventTime().isBefore(timeline.get(i).getEventTime()) ||
                            timeline.get(i - 1).getEventTime().isEqual(timeline.get(i).getEventTime()),
                    "轨迹事件应按时间正序排列"
            );
        }
    }

    @Test
    @DisplayName("骑手负载 - 接单后负载增加，完成后减少")
    void testRiderWorkload_OrderLifecycle() {
        long initialCount = riderService.getRiderWorkload(testRider.getId());
        assertEquals(0, initialCount);

        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);
        DeliveryOrder order = orderService.createOrder(request);
        String orderNo = order.getOrderNo();

        order = orderService.acceptOrder(orderNo, testRider.getId());
        long afterAccept = riderService.getRiderWorkload(testRider.getId());
        assertEquals(1, afterAccept);

        order = orderService.processCallback(orderNo, TrackEventType.PICKED_UP,
                "req-workload-001", "已取货", 39.9042, 116.4074, "RIDER");
        long afterPickup = riderService.getRiderWorkload(testRider.getId());
        assertEquals(1, afterPickup);

        order = orderService.processCallback(orderNo, TrackEventType.DELIVERY_TRANSIT,
                "req-workload-002", "配送中", 39.9100, 116.4100, "RIDER");
        long afterTransit = riderService.getRiderWorkload(testRider.getId());
        assertEquals(1, afterTransit);

        order = orderService.processCallback(orderNo, TrackEventType.DELIVERED,
                "req-workload-003", "已签收", 39.9142, 116.4174, "RIDER");
        long afterDelivery = riderService.getRiderWorkload(testRider.getId());
        assertEquals(0, afterDelivery);
    }

    @Test
    @DisplayName("派单策略 - 同网格优先")
    void testDispatchStrategy_SameGridPriority() {
        CreateRiderRequest farRiderReq = new CreateRiderRequest();
        farRiderReq.setRiderNo("FAR001");
        farRiderReq.setName("远网格骑手");
        farRiderReq.setLatitude(40.0042);
        farRiderReq.setLongitude(116.5074);
        riderService.createRider(farRiderReq);

        riderService.updateRiderStatus(testRider.getId(), RiderStatus.OFFLINE);

        CreateOrderRequest request = new CreateOrderRequest();
        request.setMerchantName("测试商家");
        request.setPickupAddress("取货地址");
        request.setDeliveryAddress("收货地址");
        request.setDeliveryLatitude(39.9042);
        request.setDeliveryLongitude(116.4074);

        riderService.updateRiderStatus(testRider.getId(), RiderStatus.IDLE);

        DeliveryOrder order = orderService.createOrder(request);
        assertNotNull(order.getRiderId());
        assertEquals(testRider.getId(), order.getRiderId(), "应优先分配同网格骑手");
    }

    @Test
    @DisplayName("业务异常 - 不存在的运单")
    void testBusinessException_NonexistentOrder() {
        assertThrows(BusinessException.class, () -> {
            orderService.getOrderByNo("NONEXISTENT_ORDER").orElseThrow(
                    () -> new BusinessException("运单不存在"));
        });
    }

    @Test
    @DisplayName("事件与状态映射 - 校验关键事件")
    void testEventToStatusMapping() {
        assertEquals(OrderStatus.PENDING_PICKUP,
                stateMachine.getStatusForEvent(TrackEventType.ORDER_CREATED));
        assertEquals(OrderStatus.PICKED_UP,
                stateMachine.getStatusForEvent(TrackEventType.PICKED_UP));
        assertEquals(OrderStatus.IN_TRANSIT,
                stateMachine.getStatusForEvent(TrackEventType.DELIVERY_TRANSIT));
        assertEquals(OrderStatus.DELIVERED,
                stateMachine.getStatusForEvent(TrackEventType.DELIVERED));
        assertEquals(OrderStatus.CANCELLED,
                stateMachine.getStatusForEvent(TrackEventType.CANCELLED));
    }
}
