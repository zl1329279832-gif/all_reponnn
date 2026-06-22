package com.delivery.service;

import com.delivery.dto.CreateRiderRequest;
import com.delivery.entity.Rider;
import com.delivery.enums.OrderStatus;
import com.delivery.enums.RiderStatus;
import com.delivery.exception.BusinessException;
import com.delivery.repository.DeliveryOrderRepository;
import com.delivery.repository.RiderRepository;
import com.delivery.util.GridUtils;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Arrays;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class RiderService {

    private final RiderRepository riderRepository;
    private final DeliveryOrderRepository deliveryOrderRepository;
    private final DispatchService dispatchService;

    @Transactional
    public Rider createRider(CreateRiderRequest request) {
        if (riderRepository.findByRiderNo(request.getRiderNo()).isPresent()) {
            throw new BusinessException("骑手编号已存在");
        }

        Rider rider = new Rider();
        rider.setRiderNo(request.getRiderNo());
        rider.setName(request.getName());
        rider.setPhone(request.getPhone());
        rider.setStatus(RiderStatus.IDLE);
        rider.setLatitude(request.getLatitude());
        rider.setLongitude(request.getLongitude());

        if (request.getGridCode() != null && !request.getGridCode().isEmpty()) {
            rider.setGridCode(request.getGridCode());
        } else if (request.getLatitude() != null && request.getLongitude() != null) {
            rider.setGridCode(dispatchService.calculateGridCode(
                    request.getLatitude(), request.getLongitude()));
        }

        rider.setCurrentOrderCount(0);
        rider.setTotalOrderCount(0);
        return riderRepository.save(rider);
    }

    public Optional<Rider> getRider(Long id) {
        return riderRepository.findById(id);
    }

    public Optional<Rider> getRiderByNo(String riderNo) {
        return riderRepository.findByRiderNo(riderNo);
    }

    public Page<Rider> listRiders(Pageable pageable) {
        return riderRepository.findAll(pageable);
    }

    public Page<Rider> listRidersByStatus(RiderStatus status, Pageable pageable) {
        return riderRepository.findByStatus(status, pageable);
    }

    @Transactional
    public Rider updateRiderStatus(Long id, RiderStatus status) {
        Rider rider = riderRepository.findByIdWithLock(id)
                .orElseThrow(() -> new BusinessException("骑手不存在"));
        rider.setStatus(status);
        return riderRepository.save(rider);
    }

    @Transactional
    public Rider updateRiderLocation(Long id, Double latitude, Double longitude) {
        Rider rider = riderRepository.findByIdWithLock(id)
                .orElseThrow(() -> new BusinessException("骑手不存在"));
        rider.setLatitude(latitude);
        rider.setLongitude(longitude);
        if (latitude != null && longitude != null) {
            rider.setGridCode(dispatchService.calculateGridCode(latitude, longitude));
        }
        return riderRepository.save(rider);
    }

    @Transactional
    public void incrementOrderCount(Long riderId) {
        Rider rider = riderRepository.findByIdWithLock(riderId)
                .orElseThrow(() -> new BusinessException("骑手不存在"));
        rider.setCurrentOrderCount(rider.getCurrentOrderCount() + 1);
        rider.setTotalOrderCount(rider.getTotalOrderCount() + 1);
        if (rider.getStatus() == RiderStatus.IDLE && rider.getCurrentOrderCount() > 0) {
            rider.setStatus(RiderStatus.BUSY);
        }
        riderRepository.save(rider);
    }

    @Transactional
    public void decrementOrderCount(Long riderId) {
        Rider rider = riderRepository.findByIdWithLock(riderId)
                .orElseThrow(() -> new BusinessException("骑手不存在"));
        if (rider.getCurrentOrderCount() > 0) {
            rider.setCurrentOrderCount(rider.getCurrentOrderCount() - 1);
        }
        if (rider.getStatus() == RiderStatus.BUSY && rider.getCurrentOrderCount() == 0) {
            rider.setStatus(RiderStatus.IDLE);
        }
        riderRepository.save(rider);
    }

    public long getRiderWorkload(Long riderId) {
        List<OrderStatus> activeStatuses = Arrays.asList(
                OrderStatus.PENDING_PICKUP,
                OrderStatus.PICKED_UP,
                OrderStatus.IN_TRANSIT
        );
        return deliveryOrderRepository.countByRiderIdAndStatusIn(riderId, activeStatuses);
    }

    public List<Rider> getIdleRidersInGrid(String gridCode) {
        return riderRepository.findByStatusAndGridCode(RiderStatus.IDLE, gridCode);
    }
}
