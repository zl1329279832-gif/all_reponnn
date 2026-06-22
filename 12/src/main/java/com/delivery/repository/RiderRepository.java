package com.delivery.repository;

import com.delivery.entity.Rider;
import com.delivery.enums.RiderStatus;
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
public interface RiderRepository extends JpaRepository<Rider, Long> {

    Optional<Rider> findByRiderNo(String riderNo);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT r FROM Rider r WHERE r.id = :id")
    Optional<Rider> findByIdWithLock(Long id);

    Page<Rider> findByStatus(RiderStatus status, Pageable pageable);

    Page<Rider> findByGridCode(String gridCode, Pageable pageable);

    List<Rider> findByStatusAndGridCode(RiderStatus status, String gridCode);

    @Query("SELECT r FROM Rider r WHERE r.status = :status ORDER BY r.currentOrderCount ASC")
    List<Rider> findByStatusOrderByCurrentOrderCountAsc(RiderStatus status);

    @Query("SELECT r FROM Rider r WHERE r.status = :status AND r.gridCode = :gridCode ORDER BY r.currentOrderCount ASC")
    List<Rider> findByStatusAndGridCodeOrderByCurrentOrderCountAsc(RiderStatus status, String gridCode);

    @Query("SELECT r.gridCode, COUNT(r) FROM Rider r WHERE r.status = :status GROUP BY r.gridCode")
    List<Object[]> countByStatusGroupByGrid(RiderStatus status);

    long countByStatus(RiderStatus status);
}
