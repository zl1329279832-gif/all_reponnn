package com.lab.requisition.repository;

import com.lab.requisition.entity.StockAlert;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface StockAlertRepository extends JpaRepository<StockAlert, Long> {

    Page<StockAlert> findByStatus(StockAlert.AlertStatus status, Pageable pageable);

    Page<StockAlert> findByLab(String lab, Pageable pageable);

    Page<StockAlert> findByCategory(String category, Pageable pageable);

    Page<StockAlert> findByLabAndCategory(String lab, String category, Pageable pageable);

    @Query("SELECT s FROM StockAlert s WHERE s.skuId = :skuId AND s.status = 'ACTIVE' ORDER BY s.createdAt DESC")
    Optional<StockAlert> findLatestActiveBySkuId(@Param("skuId") Long skuId);

    @Query("SELECT s FROM StockAlert s WHERE " +
           "(:lab IS NULL OR s.lab = :lab) AND " +
           "(:category IS NULL OR s.category = :category) AND " +
           "(:status IS NULL OR s.status = :status)")
    Page<StockAlert> findByFilters(
            @Param("lab") String lab,
            @Param("category") String category,
            @Param("status") StockAlert.AlertStatus status,
            Pageable pageable);
}
