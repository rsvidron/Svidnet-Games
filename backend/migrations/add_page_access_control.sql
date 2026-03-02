-- ============================================
-- PAGE ACCESS CONTROL MIGRATION
-- ============================================

-- Create page_access table to manage which roles can access which pages
CREATE TABLE IF NOT EXISTS page_access (
    id SERIAL PRIMARY KEY,
    page_name VARCHAR(100) UNIQUE NOT NULL,  -- e.g., 'sportsbook', 'wordle', 'wrestling'
    display_name VARCHAR(100) NOT NULL,      -- e.g., 'Sportsbook', 'Wordle Game'
    allowed_roles TEXT[] DEFAULT ARRAY['admin']::TEXT[],  -- Array of roles that can access this page
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_page_access_page_name ON page_access(page_name);
CREATE INDEX IF NOT EXISTS idx_page_access_active ON page_access(is_active);

-- Insert default pages with initial access control
INSERT INTO page_access (page_name, display_name, allowed_roles, description) VALUES
('sportsbook', 'Sportsbook', ARRAY['admin']::TEXT[], 'Sports betting and predictions page'),
('wordle', 'Wordle', ARRAY['basic', 'user', 'admin']::TEXT[], 'Daily and endless Wordle games'),
('wrestling', 'Wrestling', ARRAY['user', 'admin']::TEXT[], 'Wrestling-themed games and content'),
('trivia-game', 'Trivia Game', ARRAY['basic', 'user', 'admin']::TEXT[], 'Trivia game modes'),
('movies', 'Movies', ARRAY['basic', 'user', 'admin']::TEXT[], 'Movie-related games and leaderboards'),
('dashboard', 'Dashboard', ARRAY['basic', 'user', 'admin']::TEXT[], 'User dashboard'),
('profile', 'Profile', ARRAY['basic', 'user', 'admin']::TEXT[], 'User profile page'),
('rankings', 'Rankings', ARRAY['basic', 'user', 'admin']::TEXT[], 'Global rankings and leaderboards'),
('admin', 'Admin Panel', ARRAY['admin']::TEXT[], 'Admin panel for managing the platform')
ON CONFLICT (page_name) DO NOTHING;

-- Add trigger to auto-update updated_at
CREATE TRIGGER update_page_access_updated_at BEFORE UPDATE ON page_access
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update users table role check constraint to include 'basic'
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('basic', 'user', 'admin'));
