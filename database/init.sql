-- Create a sample table to confirm database initialization
CREATE TABLE IF NOT EXISTS limitless_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    content TEXT,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS bee_computer_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    content TEXT,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS weather_log (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    temperature_celsius DECIMAL(5,2),
    description TEXT,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS mood_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    mood_rating INT, -- e.g., 1-5 or 1-10
    notes TEXT,
    metadata JSONB
);

-- Future: Add indexes optimized for date and location queries
-- CREATE INDEX IF NOT EXISTS idx_limitless_log_timestamp ON limitless_log(timestamp);
-- CREATE INDEX IF NOT EXISTS idx_bee_computer_log_timestamp ON bee_computer_log(timestamp);
-- CREATE INDEX IF NOT EXISTS idx_weather_log_date ON weather_log(date);
-- CREATE INDEX IF NOT EXISTS idx_mood_log_timestamp ON mood_log(timestamp);

GRANT ALL PRIVILEGES ON DATABASE lifeboard_db TO lifeboard_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lifeboard_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO lifeboard_user;

-- Placeholder for application user, if different from the admin/setup user
-- CREATE USER app_user WITH PASSWORD 'app_password';
-- GRANT CONNECT ON DATABASE lifeboard_db TO app_user;
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
