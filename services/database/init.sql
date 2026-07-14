CREATE TABLE IF NOT EXISTS reservations (
    id UUID PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    customer_email VARCHAR(150) NOT NULL,
    event_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reservations_event_id
ON reservations(event_id);

CREATE INDEX IF NOT EXISTS idx_reservations_customer_email
ON reservations(customer_email);