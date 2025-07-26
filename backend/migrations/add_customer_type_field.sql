-- Add customer_type field to customers table
ALTER TABLE customers 
ADD COLUMN customer_type VARCHAR(50) DEFAULT 'household';

-- Add index for better search performance
CREATE INDEX idx_customers_customer_type ON customers(customer_type);

-- Update existing customers based on their names or other criteria (example)
-- This is optional and should be adjusted based on actual business rules
UPDATE customers 
SET customer_type = 'restaurant' 
WHERE short_name ILIKE '%餐廳%' 
   OR short_name ILIKE '%飯店%' 
   OR short_name ILIKE '%食堂%';

UPDATE customers 
SET customer_type = 'industrial' 
WHERE short_name ILIKE '%工廠%' 
   OR short_name ILIKE '%製造%' 
   OR short_name ILIKE '%工業%';

UPDATE customers 
SET customer_type = 'commercial' 
WHERE short_name ILIKE '%公司%' 
   OR short_name ILIKE '%企業%' 
   OR short_name ILIKE '%商行%';