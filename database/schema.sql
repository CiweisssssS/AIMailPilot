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
-- Row Level Security (RLS) Policies
-- Enable RLS for multi-tenant security
-- ==========================================
ALTER TABLE flag_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE deadline_overrides ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own data
CREATE POLICY flag_status_user_policy ON flag_status
    FOR ALL
    USING (user_email = current_setting('app.current_user_email', true));

CREATE POLICY deadline_overrides_user_policy ON deadline_overrides
    FOR ALL
    USING (user_email = current_setting('app.current_user_email', true));

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
