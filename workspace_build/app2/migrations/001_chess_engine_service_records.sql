-- UP
CREATE TABLE IF NOT EXISTS chess_engine_service_records (record_id TEXT, game_id TEXT, quantity INTEGER, status TEXT);
-- DOWN
DROP TABLE IF EXISTS chess_engine_service_records;
