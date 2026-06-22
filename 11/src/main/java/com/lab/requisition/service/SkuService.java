package com.lab.requisition.service;

import com.lab.requisition.dto.SkuCreateRequest;
import com.lab.requisition.entity.Sku;
import com.lab.requisition.repository.SkuRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class SkuService {

    private final SkuRepository skuRepository;

    @Transactional(readOnly = true)
    public Page<Sku> list(String category, String lab, Pageable pageable) {
        if (category != null && lab != null) {
            return skuRepository.findByCategoryAndLab(category, lab, pageable);
        } else if (category != null) {
            return skuRepository.findByCategory(category, pageable);
        } else if (lab != null) {
            return skuRepository.findByLab(lab, pageable);
        }
        return skuRepository.findAll(pageable);
    }

    @Transactional(readOnly = true)
    public Sku getById(Long id) {
        return skuRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("SKU not found: " + id));
    }

    @Transactional(readOnly = true)
    public Sku getBySkuCode(String skuCode) {
        return skuRepository.findBySkuCode(skuCode)
                .orElseThrow(() -> new RuntimeException("SKU not found: " + skuCode));
    }

    @Transactional
    public Sku create(SkuCreateRequest request) {
        if (skuRepository.findBySkuCode(request.getSkuCode()).isPresent()) {
            throw new RuntimeException("SKU code already exists: " + request.getSkuCode());
        }
        Sku sku = new Sku();
        sku.setSkuCode(request.getSkuCode());
        sku.setName(request.getName());
        sku.setCategory(request.getCategory());
        sku.setUnit(request.getUnit());
        sku.setSpecification(request.getSpecification());
        sku.setLab(request.getLab());
        sku.setSafetyStock(request.getSafetyStock());
        return skuRepository.save(sku);
    }

    @Transactional
    public Sku update(Long id, SkuCreateRequest request) {
        Sku sku = getById(id);
        if (!sku.getSkuCode().equals(request.getSkuCode())
                && skuRepository.findBySkuCode(request.getSkuCode()).isPresent()) {
            throw new RuntimeException("SKU code already exists: " + request.getSkuCode());
        }
        sku.setSkuCode(request.getSkuCode());
        sku.setName(request.getName());
        sku.setCategory(request.getCategory());
        sku.setUnit(request.getUnit());
        sku.setSpecification(request.getSpecification());
        sku.setLab(request.getLab());
        sku.setSafetyStock(request.getSafetyStock());
        return skuRepository.save(sku);
    }

    @Transactional
    public void delete(Long id) {
        if (!skuRepository.existsById(id)) {
            throw new RuntimeException("SKU not found: " + id);
        }
        skuRepository.deleteById(id);
    }

    @Transactional(readOnly = true)
    public List<Sku> findAllWithSafetyStock() {
        return skuRepository.findBySafetyStockIsNotNull();
    }
}
