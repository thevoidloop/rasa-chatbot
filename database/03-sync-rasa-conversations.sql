-- ============================================
-- Sync Mechanism for rasa_conversations
-- Automatically populates rasa_conversations from events table
-- ============================================

-- Drop existing trigger and function if they exist
DROP TRIGGER IF EXISTS sync_conversations_on_event_trigger ON events;
DROP FUNCTION IF EXISTS sync_rasa_conversations_from_events();

-- Function to sync rasa_conversations when new events arrive
CREATE OR REPLACE FUNCTION sync_rasa_conversations_from_events()
RETURNS TRIGGER AS $$
DECLARE
    v_customer_id bigint;
    v_event_timestamp timestamp;
BEGIN
    -- Convert Unix timestamp to PostgreSQL timestamp
    v_event_timestamp := to_timestamp(NEW.timestamp);

    -- Try to find customer_id if sender_id matches a customer's phone
    -- This is optional and will be NULL if no match is found
    SELECT id INTO v_customer_id
    FROM customers
    WHERE phone = NEW.sender_id
    LIMIT 1;

    -- Insert or update rasa_conversations
    INSERT INTO rasa_conversations (
        sender_id,
        customer_id,
        events,
        created_at,
        updated_at,
        active
    )
    VALUES (
        NEW.sender_id,
        v_customer_id,
        '[]',  -- Empty JSON array, not used for metrics
        v_event_timestamp,
        v_event_timestamp,
        true
    )
    ON CONFLICT (sender_id) DO UPDATE SET
        updated_at = v_event_timestamp,
        active = true;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger that fires on every INSERT to events table
-- We trigger on ALL event types, not just session_started, to ensure capture
CREATE TRIGGER sync_conversations_on_event_trigger
AFTER INSERT ON events
FOR EACH ROW
EXECUTE FUNCTION sync_rasa_conversations_from_events();

-- Create unique index on sender_id to support ON CONFLICT
DROP INDEX IF EXISTS idx_rasa_conversations_sender_id_unique;
CREATE UNIQUE INDEX idx_rasa_conversations_sender_id_unique
ON rasa_conversations(sender_id);

-- Add comment for documentation
COMMENT ON FUNCTION sync_rasa_conversations_from_events() IS
'Automatically syncs rasa_conversations table from events table.
Triggers on every event insert to maintain up-to-date conversation records.';

COMMENT ON TRIGGER sync_conversations_on_event_trigger ON events IS
'Maintains rasa_conversations table in sync with events for dashboard metrics.';

-- Log success
DO $$
BEGIN
    RAISE NOTICE 'Successfully created rasa_conversations sync trigger';
END $$;
