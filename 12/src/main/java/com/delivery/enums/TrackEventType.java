package com.delivery.enums;

public enum TrackEventType {
    ORDER_CREATED("运单创建"),
    ORDER_ASSIGNED("骑手接单"),
    PICKUP_ARRIVED("到达取货点"),
    PICKED_UP("已取货"),
    DELIVERY_TRANSIT("配送途中"),
    DELIVERY_ARRIVED("到达收货点"),
    DELIVERED("已签收"),
    EXCEPTION_MARKED("配送异常"),
    REDISPATCHED("重新派单"),
    RETURNED("退回商家"),
    RETURNED_ROLLBACK("退回回滚"),
    REASSIGNED("运单改派"),
    CANCELLED("运单取消"),
    CANCELLED_ROLLBACK("取消回滚");

    private final String description;

    TrackEventType(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}
