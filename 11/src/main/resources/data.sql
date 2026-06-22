INSERT INTO skus (sku_code, name, category, unit, specification, lab, safety_stock, created_at, updated_at) VALUES
('SKU-001', '96孔培养板', '耗材', '块', '96孔,平底', '生物实验室A', 50, NOW(), NOW()),
('SKU-002', '15ml离心管', '耗材', '支', '15ml,灭菌', '生物实验室A', 200, NOW(), NOW()),
('SKU-003', '移液枪头 1000ul', '耗材', '盒', '1000ul,灭菌', '化学实验室B', 100, NOW(), NOW()),
('SKU-004', '分析纯乙醇', '试剂', '瓶', '500ml,AR级', '化学实验室B', 20, NOW(), NOW()),
('SKU-005', '一次性手套', '防护', '盒', 'M号,无粉', '生物实验室A', 30, NOW(), NOW());

INSERT INTO inventory (sku_id, location, quantity, reserved_quantity, version, created_at, updated_at) VALUES
(1, 'A-01-01', 120, 0, 0, NOW(), NOW()),
(1, 'A-01-02', 30, 0, 0, NOW(), NOW()),
(2, 'A-02-01', 500, 0, 0, NOW(), NOW()),
(3, 'B-01-01', 150, 0, 0, NOW(), NOW()),
(4, 'B-02-01', 15, 0, 0, NOW(), NOW()),
(5, 'A-03-01', 25, 0, 0, NOW(), NOW());
