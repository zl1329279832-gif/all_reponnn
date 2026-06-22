package com.lab.requisition.repository;

import com.lab.requisition.entity.Inventory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;

@Repository
public interface InventoryRepository extends JpaRepository<Inventory, Long> {

    List<Inventory> findBySkuId(Long skuId);

    Optional<Inventory> findBySkuIdAndLocation(Long skuId, String location);

    @Query("SELECT COALESCE(SUM(i.quantity), 0) FROM Inventory i WHERE i.skuId = :skuId")
    Integer sumQuantityBySkuId(Long skuId);

    @Lock(LockModeType.OPTIMISTIC_FORCE_INCREMENT)
    @Query("SELECT i FROM Inventory i WHERE i.id = :id")
    Optional<Inventory> findByIdWithOptimisticLock(Long id);
}
