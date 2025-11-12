-- AfterMigrate script: Update statistics
-- This runs after every successful migration to ensure query planner has fresh stats

-- Analyze all tables to update statistics
ANALYZE users;
ANALYZE observations;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Statistics updated for all tables';
END $$;
