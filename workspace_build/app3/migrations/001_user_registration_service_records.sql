-- UP
CREATE TABLE IF NOT EXISTS user_registration_service_records (record_id TEXT, user_id TEXT, quantity INTEGER, status TEXT);
-- DOWN
DROP TABLE IF EXISTS user_registration_service_records;
