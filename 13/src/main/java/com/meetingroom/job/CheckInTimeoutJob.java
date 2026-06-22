package com.meetingroom.job;

import com.meetingroom.service.ReservationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class CheckInTimeoutJob {

    private final ReservationService reservationService;

    @Scheduled(fixedDelay = 60000, initialDelay = 30000)
    public void releaseTimedOutReservations() {
        int released = reservationService.releaseTimedOutReservations();
        if (released > 0) {
            log.info("定时任务执行完毕，本次自动释放 {} 个超时未签到的预定", released);
        }
    }
}
