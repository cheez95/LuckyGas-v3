-- Migration to add missing 'name' column to routes table
-- This fixes the database schema mismatch issue

-- Add name column if it doesn't exist
ALTER TABLE routes ADD COLUMN IF NOT EXISTS name VARCHAR(100);

-- Update any null names with route_number as default
UPDATE routes SET name = route_number WHERE name IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN routes.name IS 'Human-readable name for the route, defaults to route_number';