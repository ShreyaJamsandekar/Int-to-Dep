-- UP
CREATE TABLE IF NOT EXISTS inventory_service_records (record_id TEXT, order_sku TEXT, quantity INTEGER, status TEXT);
-- DOWN
DROP TABLE IF EXISTS inventory_service_records;
