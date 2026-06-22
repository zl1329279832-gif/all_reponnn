package com.delivery.exception;

public class StatusTransitionException extends BusinessException {

    public StatusTransitionException(String message) {
        super(409, message);
    }
}
