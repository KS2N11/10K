-- Reset Database SQL Script
-- This script drops and recreates all tables

-- Drop all tables in the correct order (respecting foreign keys)
DROP TABLE IF EXISTS product_matches CASCADE;
DROP TABLE IF EXISTS pain_points CASCADE;
DROP TABLE IF EXISTS pitches CASCADE;
DROP TABLE IF EXISTS analyses CASCADE;
DROP TABLE IF EXISTS analysis_jobs CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS system_metrics CASCADE;

-- Success message
SELECT '✅ All tables dropped successfully!' as status;
