-- Create order_templates table
CREATE TABLE IF NOT EXISTS order_templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,
    template_code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    
    -- Customer association
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    
    -- Template content (JSON)
    products JSONB NOT NULL,
    
    -- Delivery preferences
    delivery_notes TEXT,
    priority VARCHAR(20) DEFAULT 'normal',
    payment_method VARCHAR(20) DEFAULT 'cash',
    
    -- Scheduling options
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_pattern VARCHAR(50), -- daily, weekly, monthly, custom
    recurrence_interval INTEGER DEFAULT 1,
    recurrence_days JSONB, -- For weekly pattern
    next_scheduled_date TIMESTAMP,
    
    -- Usage tracking
    times_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);

-- Create indexes
CREATE INDEX idx_order_templates_customer_id ON order_templates(customer_id);
CREATE INDEX idx_order_templates_template_code ON order_templates(template_code);
CREATE INDEX idx_order_templates_is_active ON order_templates(is_active);
CREATE INDEX idx_order_templates_next_scheduled_date ON order_templates(next_scheduled_date);

-- Add update trigger for updated_at
CREATE OR REPLACE FUNCTION update_order_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_templates_updated_at_trigger
BEFORE UPDATE ON order_templates
FOR EACH ROW
EXECUTE FUNCTION update_order_templates_updated_at();