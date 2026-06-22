package com.lab.requisition.repository;

import com.lab.requisition.entity.Sku;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SkuRepository extends JpaRepository<Sku, Long> {

    Optional<Sku> findBySkuCode(String skuCode);

    Page<Sku> findByCategory(String category, Pageable pageable);

    Page<Sku> findByLab(String lab, Pageable pageable);

    Page<Sku> findByCategoryAndLab(String category, String lab, Pageable pageable);

    List<Sku> findBySafetyStockIsNotNull();
}
