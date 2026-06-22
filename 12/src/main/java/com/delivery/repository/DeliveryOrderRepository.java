package com.delivery.repository;

import com.delivery.entity.DeliveryOrder;
import com.delivery.enums.OrderStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;

@Repository
public interface DeliveryOrderRepository extends JpaRepository<DeliveryOrder, Long> {

    Optional<DeliveryOrder> findByOrderNo(String orderNo);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT o FROM DeliveryOrder o WHERE o.orderNo = :orderNo")
    Optional<DeliveryOrder> findByOrderNoWithLock(String orderNo);

    Page<DeliveryOrder> findByRiderId(Long riderId, Pageable pageable);

    Page<DeliveryOrder> findByStatus(OrderStatus status, Pageable pageable);

    Page<DeliveryOrder> findByGridCode(String gridCode, Pageable pageable);

    List<DeliveryOrder> findByRiderIdAndStatusIn(Long riderId, List<OrderStatus> statuses);

    long countByRiderIdAndStatusIn(Long riderId, List<OrderStatus> statuses);

    long countByStatus(OrderStatus status);

    @Query("SELECT o.gridCode, COUNT(o) FROM DeliveryOrder o WHERE o.status = :status GROUP BY o.gridCode")
    List<Object[]> countByStatusGroupByGrid(OrderStatus status);
}
