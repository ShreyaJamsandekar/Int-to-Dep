-- UP
CREATE TABLE IF NOT EXISTS auth_credential_service_records (record_id TEXT, user_id TEXT, quantity INTEGER, status TEXT);
-- DOWN
DROP TABLE IF EXISTS auth_credential_service_records;
