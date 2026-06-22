package com.delivery.enums;

public enum RiderStatus {
    OFFLINE("离线"),
    IDLE("空闲"),
    BUSY("配送中");

    private final String description;

    RiderStatus(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}
