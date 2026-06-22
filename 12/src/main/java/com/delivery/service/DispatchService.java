package com.delivery.service;

import com.delivery.entity.Rider;
import com.delivery.enums.OrderStatus;
import com.delivery.enums.RiderStatus;
import com.delivery.repository.RiderRepository;
import com.delivery.util.GridUtils;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Service
@RequiredArgsConstructor
public class DispatchService {

    private final RiderRepository riderRepository;

    @Value("${delivery.grid-size:0.01}")
    private double gridSize;

    @Value("${delivery.max-orders-per-rider:10}")
    private int maxOrdersPerRider;

    public Rider findBestRider(String gridCode, Double deliveryLat, Double deliveryLng) {
        List<Rider> sameGridRiders = riderRepository
                .findByStatusAndGridCodeOrderByCurrentOrderCountAsc(RiderStatus.IDLE, gridCode);

        List<Rider> eligibleSameGridRiders = sameGridRiders.stream()
                .filter(r -> r.getCurrentOrderCount() < maxOrdersPerRider)
                .toList();

        if (!eligibleSameGridRiders.isEmpty()) {
            return eligibleSameGridRiders.get(0);
        }

        List<Rider> allIdleRiders = riderRepository
                .findByStatusOrderByCurrentOrderCountAsc(RiderStatus.IDLE);

        List<Rider> eligibleRiders = allIdleRiders.stream()
                .filter(r -> r.getCurrentOrderCount() < maxOrdersPerRider)
                .toList();

        if (eligibleRiders.isEmpty()) {
            return null;
        }

        if (deliveryLat != null && deliveryLng != null) {
            List<Rider> ridersWithLocation = new ArrayList<>(eligibleRiders.stream()
                    .filter(r -> r.getLatitude() != null && r.getLongitude() != null)
                    .toList());

            if (!ridersWithLocation.isEmpty()) {
                ridersWithLocation.sort(Comparator
                        .comparing((Rider r) -> GridUtils.distance(
                                deliveryLat, deliveryLng, r.getLatitude(), r.getLongitude()))
                        .thenComparing(Rider::getCurrentOrderCount));
                return ridersWithLocation.get(0);
            }
        }

        return eligibleRiders.get(0);
    }

    public String calculateGridCode(double latitude, double longitude) {
        return GridUtils.getGridCode(latitude, longitude, gridSize);
    }
}
