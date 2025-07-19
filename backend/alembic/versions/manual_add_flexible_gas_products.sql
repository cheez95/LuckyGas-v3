-- Manual migration for flexible gas product system
-- Run this after database is set up

-- Create gas_products table
CREATE TABLE IF NOT EXISTS gas_products (
    id SERIAL PRIMARY KEY,
    delivery_method VARCHAR(50) NOT NULL,
    size_kg INTEGER NOT NULL,
    attribute VARCHAR(50) NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name_zh VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    description VARCHAR(500),
    unit_price FLOAT NOT NULL,
    deposit_amount FLOAT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_available BOOLEAN DEFAULT TRUE,
    track_inventory BOOLEAN DEFAULT TRUE,
    low_stock_threshold INTEGER DEFAULT 10,
    CONSTRAINT uq_product_combination UNIQUE (delivery_method, size_kg, attribute)
);

CREATE INDEX IF NOT EXISTS idx_gas_products_sku ON gas_products(sku);

-- Create customer_inventory table
CREATE TABLE IF NOT EXISTS customer_inventory (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    gas_product_id INTEGER NOT NULL REFERENCES gas_products(id),
    quantity_owned INTEGER DEFAULT 0,
    quantity_rented INTEGER DEFAULT 0,
    quantity_total INTEGER DEFAULT 0,
    flow_meter_count INTEGER DEFAULT 0,
    last_meter_reading FLOAT DEFAULT 0,
    deposit_paid FLOAT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_customer_product_inventory UNIQUE (customer_id, gas_product_id)
);

CREATE INDEX IF NOT EXISTS idx_customer_inventory_customer ON customer_inventory(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_inventory_product ON customer_inventory(gas_product_id);

-- Create order_items table
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    gas_product_id INTEGER NOT NULL REFERENCES gas_products(id),
    quantity INTEGER NOT NULL,
    unit_price FLOAT NOT NULL,
    subtotal FLOAT NOT NULL,
    discount_percentage FLOAT DEFAULT 0,
    discount_amount FLOAT DEFAULT 0,
    final_amount FLOAT NOT NULL,
    is_exchange BOOLEAN DEFAULT TRUE,
    empty_received INTEGER DEFAULT 0,
    is_flow_delivery BOOLEAN DEFAULT FALSE,
    meter_reading_start FLOAT,
    meter_reading_end FLOAT,
    actual_quantity FLOAT,
    notes VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(gas_product_id);

-- Insert seed data for gas products
-- This will be handled by the seed script: app/scripts/seed_gas_products.py

-- Migration notes:
-- After creating these tables:
-- 1. Run the seed script to populate gas products
-- 2. Run the data migration script to convert existing cylinder data
-- 3. The old cylinder columns in customers table can be kept for backward compatibility
--    or removed after successful migration