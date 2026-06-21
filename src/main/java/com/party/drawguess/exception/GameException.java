package com.party.drawguess.exception;

import lombok.Getter;

@Getter
public class GameException extends RuntimeException {
    private final int code;

    public GameException(int code, String message) {
        super(message);
        this.code = code;
    }

    public GameException(String message) {
        this(400, message);
    }
}
