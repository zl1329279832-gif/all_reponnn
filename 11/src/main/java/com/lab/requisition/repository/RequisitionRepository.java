package com.lab.requisition.repository;

import com.lab.requisition.entity.Requisition;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RequisitionRepository extends JpaRepository<Requisition, Long> {

    Optional<Requisition> findByIdempotencyKey(String idempotencyKey);

    Page<Requisition> findByStatus(Requisition.Status status, Pageable pageable);

    Page<Requisition> findByResearcher(String researcher, Pageable pageable);

    Page<Requisition> findBySkuId(Long skuId, Pageable pageable);
}
