package com.delivery.service;

import com.delivery.dto.RiderWorkloadDTO;
import com.delivery.entity.Rider;
import com.delivery.enums.OrderStatus;
import com.delivery.enums.RiderStatus;
import com.delivery.repository.DeliveryOrderRepository;
import com.delivery.repository.RiderRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class StatisticsService {

    private final DeliveryOrderRepository orderRepository;
    private final RiderRepository riderRepository;
    private final RiderService riderService;

    public Map<String, Object> getOverallStatistics() {
        Map<String, Object> stats = new HashMap<>();

        long totalRiders = riderRepository.count();
        long idleRiders = riderRepository.countByStatus(RiderStatus.IDLE);
        long busyRiders = riderRepository.countByStatus(RiderStatus.BUSY);
        long offlineRiders = riderRepository.countByStatus(RiderStatus.OFFLINE);

        stats.put("totalRiders", totalRiders);
        stats.put("idleRiders", idleRiders);
        stats.put("busyRiders", busyRiders);
        stats.put("offlineRiders", offlineRiders);

        long pendingOrders = orderRepository.countByStatus(OrderStatus.PENDING_PICKUP);
        long pickedUpOrders = orderRepository.countByStatus(OrderStatus.PICKED_UP);
        long inTransitOrders = orderRepository.countByStatus(OrderStatus.IN_TRANSIT);
        long deliveredOrders = orderRepository.countByStatus(OrderStatus.DELIVERED);
        long cancelledOrders = orderRepository.countByStatus(OrderStatus.CANCELLED);

        stats.put("pendingOrders", pendingOrders);
        stats.put("pickedUpOrders", pickedUpOrders);
        stats.put("inTransitOrders", inTransitOrders);
        stats.put("deliveredOrders", deliveredOrders);
        stats.put("cancelledOrders", cancelledOrders);
        stats.put("totalOrders", pendingOrders + pickedUpOrders + inTransitOrders + deliveredOrders + cancelledOrders);

        return stats;
    }

    public List<RiderWorkloadDTO> getRiderWorkloadList() {
        List<Rider> allRiders = riderRepository.findAll();
        List<RiderWorkloadDTO> workloadList = new ArrayList<>();

        for (Rider rider : allRiders) {
            RiderWorkloadDTO dto = new RiderWorkloadDTO();
            dto.setRiderId(rider.getId());
            dto.setRiderNo(rider.getRiderNo());
            dto.setRiderName(rider.getName());
            dto.setStatus(rider.getStatus());
            dto.setCurrentOrderCount(rider.getCurrentOrderCount());
            dto.setTotalOrderCount(rider.getTotalOrderCount());
            dto.setGridCode(rider.getGridCode());
            dto.setLatitude(rider.getLatitude());
            dto.setLongitude(rider.getLongitude());
            workloadList.add(dto);
        }

        workloadList.sort((a, b) -> Integer.compare(b.getCurrentOrderCount(), a.getCurrentOrderCount()));
        return workloadList;
    }

    public Map<String, Map<String, Object>> getGridStatistics() {
        Map<String, Map<String, Object>> gridStats = new HashMap<>();

        List<Object[]> riderGridCounts = riderRepository.countByStatusGroupByGrid(RiderStatus.IDLE);
        for (Object[] row : riderGridCounts) {
            String gridCode = (String) row[0];
            Long count = (Long) row[1];
            gridStats.computeIfAbsent(gridCode, k -> new HashMap<>())
                    .put("idleRiders", count);
        }

        List<Object[]> orderGridCounts = orderRepository.countByStatusGroupByGrid(OrderStatus.PENDING_PICKUP);
        for (Object[] row : orderGridCounts) {
            String gridCode = (String) row[0];
            Long count = (Long) row[1];
            gridStats.computeIfAbsent(gridCode, k -> new HashMap<>())
                    .put("pendingOrders", count);
        }

        return gridStats;
    }
}
