package com.delivery.enums;

public enum OrderStatus {
    PENDING_PICKUP("待揽收"),
    PICKED_UP("已揽收"),
    IN_TRANSIT("配送中"),
    PENDING_REDISPATCH("待重派"),
    DELIVERED("已签收"),
    CANCELLED("已取消"),
    RETURNED("已退回");

    private final String description;

    OrderStatus(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}
