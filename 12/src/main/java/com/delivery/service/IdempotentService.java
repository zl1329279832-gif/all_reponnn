package com.delivery.service;

import com.delivery.entity.IdempotentRecord;
import com.delivery.repository.IdempotentRecordRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

@Service
@RequiredArgsConstructor
public class IdempotentService {

    private final IdempotentRecordRepository idempotentRecordRepository;

    @Transactional
    public boolean checkAndRecord(String requestKey, String orderNo, String operation) {
        Optional<IdempotentRecord> existing = idempotentRecordRepository.findByRequestKey(requestKey);
        if (existing.isPresent()) {
            return false;
        }

        IdempotentRecord record = new IdempotentRecord();
        record.setRequestKey(requestKey);
        record.setOrderNo(orderNo);
        record.setOperation(operation);
        idempotentRecordRepository.save(record);
        return true;
    }

    public boolean exists(String requestKey) {
        return idempotentRecordRepository.existsByRequestKey(requestKey);
    }

    public Optional<IdempotentRecord> getRecord(String requestKey) {
        return idempotentRecordRepository.findByRequestKey(requestKey);
    }
}
