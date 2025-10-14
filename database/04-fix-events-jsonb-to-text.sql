-- ============================================
-- Migration: Fix SQLTrackerStore JSONB Serialization Issue
-- Changes events.data column from JSONB to TEXT
-- ============================================
--
-- Problem: RASA 3.6.19 with psycopg2 fails to deserialize JSONB fields,
-- causing fallback to InMemoryTrackerStore and loss of conversation events.
--
-- Solution: Convert JSONB column to TEXT to ensure compatibility.
-- ============================================

-- Step 1: Check current column type
DO $$
BEGIN
    RAISE NOTICE 'Current data type for events.data column:';
END $$;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'events' AND column_name = 'data';

-- Step 2: Convert JSONB to TEXT
-- Using ::TEXT casting to preserve JSON string format
ALTER TABLE events
ALTER COLUMN data TYPE TEXT
USING data::TEXT;

-- Step 3: Verify the change
DO $$
BEGIN
    RAISE NOTICE 'New data type for events.data column:';
END $$;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'events' AND column_name = 'data';

-- Step 4: Verify data integrity (sample check)
DO $$
BEGIN
    RAISE NOTICE 'Sample data check - first 3 events:';
END $$;

SELECT id, sender_id, type_name,
       LEFT(data, 100) as data_preview,
       LENGTH(data) as data_length
FROM events
WHERE data IS NOT NULL
ORDER BY id DESC
LIMIT 3;

-- Log success
DO $$
BEGIN
    RAISE NOTICE '✅ Successfully migrated events.data from JSONB to TEXT';
    RAISE NOTICE 'RASA SQLTrackerStore should now work correctly without fallback to InMemoryTrackerStore';
END $$;
