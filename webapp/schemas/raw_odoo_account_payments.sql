CREATE TABLE IF NOT EXISTS raw_odoo_account_payments (
    payment_id             TEXT    PRIMARY KEY,
    payment_move_id        TEXT    NOT NULL,
    invoice_move_id        TEXT    NOT NULL,
    invoice_number_ref     TEXT,
    amount                 NUMERIC,
    create_date            TIMESTAMP,
    last_updated           TIMESTAMP,
    ingested_at            TIMESTAMP DEFAULT NOW()
);
