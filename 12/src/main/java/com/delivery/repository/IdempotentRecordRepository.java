package com.delivery.repository;

import com.delivery.entity.IdempotentRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface IdempotentRecordRepository extends JpaRepository<IdempotentRecord, Long> {

    Optional<IdempotentRecord> findByRequestKey(String requestKey);

    boolean existsByRequestKey(String requestKey);
}
