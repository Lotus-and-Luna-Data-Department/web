-- schema for raw_odoo_stock_pickings
CREATE TABLE IF NOT EXISTS raw_odoo_stock_pickings (
    stock_picking_id    TEXT    PRIMARY KEY,
    sale_order_reference TEXT,
    date_done           TIMESTAMP,
    scheduled_date      TIMESTAMP,
    create_date         TIMESTAMP,
    last_updated        TIMESTAMP,
    state               TEXT,
    picking_type        TEXT,
    ingested_at         TIMESTAMP DEFAULT NOW()
);
