package com.meetingroom.repository;

import com.meetingroom.entity.ReservationAudit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ReservationAuditRepository extends JpaRepository<ReservationAudit, Long> {
}
