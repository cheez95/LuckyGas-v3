-- Initialize test database for Lucky Gas v3

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create test user if not exists
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_user
      WHERE usename = 'luckygas_test') THEN

      CREATE USER luckygas_test WITH PASSWORD 'test_password_secure_123';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE luckygas_test TO luckygas_test;
ALTER USER luckygas_test CREATEDB;

-- Set default search path
ALTER DATABASE luckygas_test SET search_path TO public;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS test_data;
GRANT ALL ON SCHEMA test_data TO luckygas_test;

-- Performance settings for testing
ALTER DATABASE luckygas_test SET shared_buffers = '256MB';
ALTER DATABASE luckygas_test SET work_mem = '4MB';
ALTER DATABASE luckygas_test SET maintenance_work_mem = '64MB';

-- Set timezone
ALTER DATABASE luckygas_test SET timezone = 'Asia/Taipei';

-- Create audit log table for testing
CREATE TABLE IF NOT EXISTS test_data.audit_log (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    user_name VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    old_data JSONB,
    new_data JSONB
);

-- Create test configuration table
CREATE TABLE IF NOT EXISTS test_data.test_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert test configuration
INSERT INTO test_data.test_config (key, value, description) VALUES
    ('test_mode', 'true', 'Enable test mode features'),
    ('mock_services', 'true', 'Use mock external services'),
    ('test_data_seed', 'true', 'Auto-seed test data on startup'),
    ('test_user_count', '50', 'Number of test users to create'),
    ('test_order_count', '200', 'Number of test orders to create')
ON CONFLICT (key) DO NOTHING;

-- Create indexes for better test performance
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON test_data.audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_table ON test_data.audit_log(table_name);

-- Function to reset test data
CREATE OR REPLACE FUNCTION test_data.reset_test_database()
RETURNS void AS $$
BEGIN
    -- Truncate all tables except migrations
    TRUNCATE TABLE 
        users,
        customers,
        gas_products,
        orders,
        order_items,
        routes,
        route_deliveries,
        vehicles,
        delivery_histories,
        delivery_history_items,
        invoices,
        notifications,
        order_templates,
        customer_inventories
    CASCADE;
    
    -- Reset sequences
    ALTER SEQUENCE users_id_seq RESTART WITH 1;
    ALTER SEQUENCE customers_id_seq RESTART WITH 1;
    ALTER SEQUENCE gas_products_id_seq RESTART WITH 1;
    ALTER SEQUENCE orders_id_seq RESTART WITH 1;
    ALTER SEQUENCE routes_id_seq RESTART WITH 1;
    ALTER SEQUENCE vehicles_id_seq RESTART WITH 1;
    
    -- Log reset
    INSERT INTO test_data.audit_log (table_name, operation, user_name)
    VALUES ('all_tables', 'RESET', current_user);
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION test_data.reset_test_database() TO luckygas_test;

-- Create view for test statistics
CREATE OR REPLACE VIEW test_data.test_statistics AS
SELECT 
    'users' as table_name, COUNT(*) as record_count FROM users
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'routes', COUNT(*) FROM routes
UNION ALL
SELECT 'vehicles', COUNT(*) FROM vehicles
UNION ALL
SELECT 'products', COUNT(*) FROM gas_products;

-- Grant select on view
GRANT SELECT ON test_data.test_statistics TO luckygas_test;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Test database initialization completed successfully';
END $$;