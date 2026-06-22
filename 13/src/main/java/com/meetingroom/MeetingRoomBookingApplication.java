package com.meetingroom;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class MeetingRoomBookingApplication {

    public static void main(String[] args) {
        SpringApplication.run(MeetingRoomBookingApplication.class, args);
        System.out.println("\n" +
                "╔════════════════════════════════════════════════════════════╗\n" +
                "║     会议室预定服务启动成功！                                ║\n" +
                "║     服务地址: http://localhost:8080                        ║\n" +
                "║     数据库: SQLite (./data/meeting_room.db)                ║\n" +
                "╚════════════════════════════════════════════════════════════╝\n");
    }
}
