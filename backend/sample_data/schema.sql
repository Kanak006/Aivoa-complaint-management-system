-- This is generated automatically by SQLAlchemy on app startup (Base.metadata.create_all).
-- Included here for reference / manual setup if needed.

CREATE TABLE IF NOT EXISTS complaints (
    id SERIAL PRIMARY KEY,
    complaint_source VARCHAR(120),
    customer_name VARCHAR(200),
    product_name VARCHAR(200),
    product_strength VARCHAR(120),
    batch_lot_number VARCHAR(120),
    manufacturing_date DATE,
    expiry_date DATE,
    quantity_affected VARCHAR(60),
    complaint_type VARCHAR(120),
    complaint_date DATE,
    description TEXT,
    initial_severity VARCHAR(40),
    priority VARCHAR(40),
    completeness_score FLOAT,
    missing_fields JSON,
    risk_classification VARCHAR(40),
    risk_justification TEXT,
    capa_recommendation TEXT,
    raw_source_text TEXT,
    status VARCHAR(40) DEFAULT 'Pending Triage',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ
);
