-- AIMailPilot Database Schema for Supabase
-- This script creates the necessary tables for data persistence

-- Enable UUID extension (optional, using SERIAL for simplicity)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================
-- Table: flag_status
-- Purpose: Store user's flagged/bookmarked emails
-- ==========================================
CREATE TABLE IF NOT EXISTS flag_status (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    email_id VARCHAR(255) NOT NULL,
    is_flagged BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_user_email_flag UNIQUE(user_email, email_id)
);

-- Index for faster queries by user
CREATE INDEX IF NOT EXISTS idx_flag_status_user_email ON flag_status(user_email);
CREATE INDEX IF NOT EXISTS idx_flag_status_user_email_flagged ON flag_status(user_email, is_flagged);

-- ==========================================
-- Table: deadline_overrides
-- Purpose: Store user's manually edited task deadlines
-- ==========================================
CREATE TABLE IF NOT EXISTS deadline_overrides (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    email_id VARCHAR(255) NOT NULL,
    task_index INTEGER NOT NULL,
    original_deadline VARCHAR(100),
    override_deadline VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_user_email_task UNIQUE(user_email, email_id, task_index)
);

-- Index for faster queries by user
CREATE INDEX IF NOT EXISTS idx_deadline_overrides_user_email ON deadline_overrides(user_email);

-- ==========================================
-- Trigger: Auto-update updated_at timestamp
-- ==========================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_flag_status_updated_at BEFORE UPDATE ON flag_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_deadline_overrides_updated_at BEFORE UPDATE ON deadline_overrides
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Table: emails
-- Purpose: Store normalized email messages with MIME-decoded content
-- ==========================================
CREATE TABLE IF NOT EXISTS emails (
    message_id VARCHAR(255) PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    from_name VARCHAR(500),
    from_email VARCHAR(500) NOT NULL,
    subject TEXT,
    date_iso TIMESTAMP WITH TIME ZONE,
    snippet TEXT,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    normalized_html TEXT,
    normalized_text TEXT,
    processed BOOLEAN DEFAULT false,
    last_history_id_at_create VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emails_user_email ON emails(user_email);
CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_user_processed ON emails(user_email, processed);
CREATE INDEX IF NOT EXISTS idx_emails_date_iso ON emails(date_iso DESC);

CREATE TRIGGER update_emails_updated_at BEFORE UPDATE ON emails
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Table: tasks
-- Purpose: Store extracted tasks with state machine (new|viewed|saved|done)
-- ==========================================
CREATE TABLE IF NOT EXISTS tasks (
    task_id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    priority VARCHAR(20) NOT NULL CHECK (priority IN ('urgent', 'todo', 'fyi')),
    state VARCHAR(20) NOT NULL DEFAULT 'new' CHECK (state IN ('new', 'viewed', 'saved', 'done')),
    rule_key VARCHAR(255),
    normalized_title TEXT NOT NULL,
    snooze_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_task_per_message UNIQUE(message_id, rule_key, normalized_title, user_email)
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_email ON tasks(user_email);
CREATE INDEX IF NOT EXISTS idx_tasks_message_id ON tasks(message_id);
CREATE INDEX IF NOT EXISTS idx_tasks_user_state ON tasks(user_email, state);
CREATE INDEX IF NOT EXISTS idx_tasks_user_priority ON tasks(user_email, priority);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Table: sync_meta
-- Purpose: Store sync state per user (last_history_id, sync timestamps)
-- ==========================================
CREATE TABLE IF NOT EXISTS sync_meta (
    user_id VARCHAR(255) PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL UNIQUE,
    last_history_id VARCHAR(100),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_backfill_from TIMESTAMP WITH TIME ZONE,
    latest_profile_history_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sync_meta_user_email ON sync_meta(user_email);

CREATE TRIGGER update_sync_meta_updated_at BEFORE UPDATE ON sync_meta
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Row Level Security (RLS) Policies
-- ==========================================
-- NOTE: RLS is DISABLED for this application because we use application-layer
-- access control (user_email parameter in queries) instead of database-level RLS.
-- 
-- IMPORTANT: Use SUPABASE_KEY with service_role key (not anon key) to bypass RLS.
-- This allows the application to enforce user isolation at the API layer while
-- maintaining full database access for background operations.
--
-- If you prefer database-level RLS:
-- 1. Use the anon key for SUPABASE_KEY
-- 2. Uncomment the policies below
-- 3. Modify app/db/supabase_client.py to set session variable before queries
--
-- ALTER TABLE flag_status ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE deadline_overrides ENABLE ROW LEVEL SECURITY;
--
-- CREATE POLICY flag_status_user_policy ON flag_status
--     FOR ALL
--     USING (user_email = current_setting('app.current_user_email', true));
--
-- CREATE POLICY deadline_overrides_user_policy ON deadline_overrides
--     FOR ALL
--     USING (user_email = current_setting('app.current_user_email', true));

-- ==========================================
-- Initial Data / Seed (Optional)
-- ==========================================
-- None needed for production

-- ==========================================
-- Verification Queries
-- ==========================================
-- Run these to verify the schema was created successfully:
-- SELECT * FROM pg_tables WHERE schemaname = 'public';
-- SELECT * FROM flag_status LIMIT 10;
-- SELECT * FROM deadline_overrides LIMIT 10;
