CREATE TABLE rate_limit_event (
    id SERIAL PRIMARY KEY,
    ip_address TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rate_limit_event_ip_created ON rate_limit_event (ip_address, created_at);
