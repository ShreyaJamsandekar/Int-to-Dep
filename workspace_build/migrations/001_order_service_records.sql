-- UP
CREATE TABLE IF NOT EXISTS order_service_records (record_id TEXT, order_sku TEXT, quantity INTEGER, status TEXT);
-- DOWN
DROP TABLE IF EXISTS order_service_records;
