-- V006: vistas de consulta usadas por la API, el panel y los reportes
CREATE VIEW v_producto_detalle AS
SELECT p.product_id, p.name, p.description, p.unit_price, p.state, p.fk_car_product, p.fk_spare_part,
       COALESCE((SELECT SUM(i.quantity_available) FROM inventory i WHERE i.product_id = p.product_id), 0)::int AS stock_total,
       st.spare_part_type_id AS category_id,
       st.name               AS category,
       sb.name               AS part_brand
FROM product p
LEFT JOIN spare_part sp       ON sp.spare_part_id = p.fk_spare_part
LEFT JOIN spare_part_type st  ON st.spare_part_type_id = sp.spare_part_type_id
LEFT JOIN spare_part_brand sb ON sb.spare_part_brand_id = sp.spare_part_brand_id;

CREATE VIEW v_venta_resumen AS
SELECT s.sale_id, s.user_id, u.username, s.sale_type_id, ss.name AS state, s.company_warehouse_id, s.customer_name,
       s.description, s.sale_date, s.subtotal, s.tax, s.total,
       (SELECT COALESCE(SUM(d.quantity), 0) FROM sale_detail d WHERE d.sale_id = s.sale_id)::int AS items,
       dv.status AS delivery_status, dv.tracking_number, ei.invoice_id
FROM sale s
JOIN sale_state ss    ON ss.sale_state_id = s.sale_state_id
JOIN app_user u       ON u.user_id = s.user_id
LEFT JOIN delivery dv ON dv.sale_id = s.sale_id
LEFT JOIN electronic_invoice ei ON ei.sale_id = s.sale_id;

CREATE VIEW v_inventario_detalle AS
SELECT i.inventory_id, i.product_id, p.name AS product_name, st.name AS category,
       i.company_warehouse_id, w.name AS warehouse_name, i.quantity_available, i.minimum_stock,
       i.maximum_stock, i.reorder_stock, (i.quantity_available <= i.reorder_stock) AS needs_reorder
FROM inventory i
JOIN product p              ON p.product_id = i.product_id
JOIN company_warehouse w    ON w.company_warehouse_id = i.company_warehouse_id
LEFT JOIN spare_part sp     ON sp.spare_part_id = p.fk_spare_part
LEFT JOIN spare_part_type st ON st.spare_part_type_id = sp.spare_part_type_id;

CREATE VIEW v_entrega_detalle AS
SELECT d.delivery_id, d.sale_id, d.address, d.delivery_date, d.tracking_number, d.status, d.assigned_user_id,
       r.username AS courier, s.customer_name, ss.name AS sale_state, s.sale_date, s.total
FROM delivery d
JOIN sale s           ON s.sale_id = d.sale_id
JOIN sale_state ss    ON ss.sale_state_id = s.sale_state_id
LEFT JOIN app_user r  ON r.user_id = d.assigned_user_id;

-- Los indicadores excluyen las ventas canceladas
CREATE VIEW v_ventas_por_mes AS
SELECT date_trunc('month', s.sale_date AT TIME ZONE 'America/Bogota')::date AS mes,
       COUNT(*)::int AS cantidad, SUM(s.total) AS total
FROM sale s JOIN sale_state ss ON ss.sale_state_id = s.sale_state_id
WHERE ss.name <> 'Cancelada'
GROUP BY 1;

CREATE VIEW v_ventas_por_estado AS
SELECT ss.sale_state_id, ss.name AS state, COUNT(s.sale_id)::int AS cantidad, COALESCE(SUM(s.total), 0) AS total
FROM sale_state ss LEFT JOIN sale s ON s.sale_state_id = ss.sale_state_id
WHERE ss.sale_state_id <= 5
GROUP BY ss.sale_state_id, ss.name;

CREATE VIEW v_productos_mas_vendidos AS
SELECT p.product_id, p.name, SUM(d.quantity)::int AS cantidad, SUM(d.subtotal) AS total
FROM sale_detail d
JOIN sale s        ON s.sale_id = d.sale_id
JOIN sale_state ss ON ss.sale_state_id = s.sale_state_id
JOIN product p     ON p.product_id = d.product_id
WHERE ss.name <> 'Cancelada'
GROUP BY p.product_id, p.name;
