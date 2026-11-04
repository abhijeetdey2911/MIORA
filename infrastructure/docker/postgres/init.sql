-- Project JobHunter PostgreSQL Initialization Script
-- Executed on container first run

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Project JobHunter Database Initialized Successfully.';
END $$;

