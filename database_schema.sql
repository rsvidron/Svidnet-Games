-- ============================================
-- SVIDRON GAME PLATFORM - DATABASE SCHEMA
-- PostgreSQL Schema with Indexes & Constraints
-- ============================================

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ============================================
-- USER PROFILES & STATS
-- ============================================

CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    elo_rating INTEGER DEFAULT 1200,
    trivia_accuracy_percentage DECIMAL(5, 2) DEFAULT 0.00,
    wordle_current_streak INTEGER DEFAULT 0,
    wordle_max_streak INTEGER DEFAULT 0,
    total_games_played INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_elo ON user_profiles(elo_rating DESC);

-- ============================================
-- FRIENDS SYSTEM
-- ============================================

CREATE TABLE friendships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'blocked')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, friend_id),
    CHECK (user_id != friend_id)
);

CREATE INDEX idx_friendships_user_id ON friendships(user_id);
CREATE INDEX idx_friendships_friend_id ON friendships(friend_id);
CREATE INDEX idx_friendships_status ON friendships(status);

-- ============================================
-- CATEGORIES
-- ============================================

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    icon_url VARCHAR(500),
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('easy', 'medium', 'hard', 'expert')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_categories_name ON categories(name);
CREATE INDEX idx_categories_difficulty ON categories(difficulty_level);

-- ============================================
-- TRIVIA QUESTIONS
-- ============================================

CREATE TABLE trivia_questions (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    question_text TEXT NOT NULL,
    difficulty VARCHAR(20) CHECK (difficulty IN ('easy', 'medium', 'hard', 'expert')),
    question_type VARCHAR(50) DEFAULT 'multiple_choice' CHECK (question_type IN ('multiple_choice', 'true_false', 'fill_blank')),
    points INTEGER DEFAULT 100,
    time_limit_seconds INTEGER DEFAULT 30,
    is_approved BOOLEAN DEFAULT FALSE,
    source VARCHAR(50) DEFAULT 'manual' CHECK (source IN ('manual', 'ai_generated', 'imported')),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_trivia_questions_category ON trivia_questions(category_id);
CREATE INDEX idx_trivia_questions_difficulty ON trivia_questions(difficulty);
CREATE INDEX idx_trivia_questions_approved ON trivia_questions(is_approved);
CREATE INDEX idx_trivia_questions_source ON trivia_questions(source);

-- ============================================
-- TRIVIA ANSWERS
-- ============================================

CREATE TABLE trivia_answers (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES trivia_questions(id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_trivia_answers_question_id ON trivia_answers(question_id);
CREATE INDEX idx_trivia_answers_correct ON trivia_answers(is_correct);

-- ============================================
-- AI GENERATED QUESTIONS (PENDING APPROVAL)
-- ============================================

CREATE TABLE ai_generated_questions (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    question_data JSONB NOT NULL, -- Stores full question + answers
    generation_prompt TEXT,
    model_used VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ai_questions_status ON ai_generated_questions(status);
CREATE INDEX idx_ai_questions_category ON ai_generated_questions(category_id);

-- ============================================
-- GAME MODES
-- ============================================

CREATE TABLE game_modes (
    id SERIAL PRIMARY KEY,
    mode_name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    min_players INTEGER DEFAULT 1,
    max_players INTEGER DEFAULT 1,
    is_multiplayer BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default game modes
INSERT INTO game_modes (mode_name, display_name, description, min_players, max_players, is_multiplayer) VALUES
('fifth_grade', '5th Grade Trivia', 'Progressive difficulty trivia challenge', 1, 1, FALSE),
('jeopardy', 'Jeopardy Mode', 'Category-based trivia with buzzer system', 1, 8, TRUE),
('multiplayer_trivia', 'Multiplayer Trivia', 'Real-time trivia competition', 2, 8, TRUE),
('daily_wordle', 'Daily Wordle', 'One puzzle per day shared globally', 1, 1, FALSE),
('endless_wordle', 'Endless Wordle', 'Unlimited word puzzles', 1, 1, FALSE),
('word_connections', 'Word Connections', 'Group words into categories', 1, 4, TRUE),
('sports_predictions', 'Sports Predictions', 'Predict game outcomes', 1, 1, FALSE);

-- ============================================
-- GAME ROOMS (for multiplayer)
-- ============================================

CREATE TABLE game_rooms (
    id SERIAL PRIMARY KEY,
    room_code VARCHAR(6) UNIQUE NOT NULL,
    game_mode_id INTEGER NOT NULL REFERENCES game_modes(id) ON DELETE RESTRICT,
    host_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    room_name VARCHAR(100),
    max_players INTEGER DEFAULT 8,
    current_players INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'waiting' CHECK (status IN ('waiting', 'in_progress', 'completed', 'cancelled')),
    settings JSONB DEFAULT '{}', -- Game-specific settings
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_game_rooms_code ON game_rooms(room_code);
CREATE INDEX idx_game_rooms_status ON game_rooms(status);
CREATE INDEX idx_game_rooms_host ON game_rooms(host_user_id);

-- ============================================
-- GAME PARTICIPANTS
-- ============================================

CREATE TABLE game_participants (
    id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES game_rooms(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'player' CHECK (role IN ('player', 'spectator')),
    score INTEGER DEFAULT 0,
    position INTEGER,
    is_ready BOOLEAN DEFAULT FALSE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    left_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(room_id, user_id)
);

CREATE INDEX idx_game_participants_room ON game_participants(room_id);
CREATE INDEX idx_game_participants_user ON game_participants(user_id);
CREATE INDEX idx_game_participants_score ON game_participants(score DESC);

-- ============================================
-- GAME SESSIONS (Individual games)
-- ============================================

CREATE TABLE game_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_mode_id INTEGER NOT NULL REFERENCES game_modes(id) ON DELETE RESTRICT,
    room_id INTEGER REFERENCES game_rooms(id) ON DELETE SET NULL,
    score INTEGER DEFAULT 0,
    accuracy_percentage DECIMAL(5, 2),
    questions_answered INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    time_taken_seconds INTEGER,
    elo_change INTEGER DEFAULT 0,
    position INTEGER,
    game_data JSONB DEFAULT '{}', -- Store game-specific data
    completed BOOLEAN DEFAULT FALSE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_game_sessions_user ON game_sessions(user_id);
CREATE INDEX idx_game_sessions_mode ON game_sessions(game_mode_id);
CREATE INDEX idx_game_sessions_room ON game_sessions(room_id);
CREATE INDEX idx_game_sessions_score ON game_sessions(score DESC);
CREATE INDEX idx_game_sessions_completed ON game_sessions(completed, started_at DESC);

-- ============================================
-- USER ANSWERS (Detailed tracking)
-- ============================================

CREATE TABLE user_answers (
    id SERIAL PRIMARY KEY,
    game_session_id INTEGER NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES trivia_questions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    answer_id INTEGER REFERENCES trivia_answers(id) ON DELETE SET NULL,
    is_correct BOOLEAN NOT NULL,
    time_taken_seconds INTEGER,
    points_earned INTEGER DEFAULT 0,
    answered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_answers_session ON user_answers(game_session_id);
CREATE INDEX idx_user_answers_user ON user_answers(user_id);
CREATE INDEX idx_user_answers_question ON user_answers(question_id);

-- ============================================
-- WORDLE WORDS
-- ============================================

CREATE TABLE wordle_words (
    id SERIAL PRIMARY KEY,
    word VARCHAR(10) NOT NULL,
    word_length INTEGER NOT NULL,
    difficulty VARCHAR(20) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    is_daily BOOLEAN DEFAULT FALSE,
    daily_date DATE UNIQUE,
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_wordle_words_daily ON wordle_words(is_daily, daily_date);
CREATE INDEX idx_wordle_words_difficulty ON wordle_words(difficulty);
CREATE INDEX idx_wordle_words_length ON wordle_words(word_length);

-- ============================================
-- WORDLE ATTEMPTS
-- ============================================

CREATE TABLE wordle_attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    wordle_word_id INTEGER NOT NULL REFERENCES wordle_words(id) ON DELETE CASCADE,
    attempts_data JSONB NOT NULL, -- Array of guesses with feedback
    num_attempts INTEGER NOT NULL,
    solved BOOLEAN DEFAULT FALSE,
    time_taken_seconds INTEGER,
    game_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, wordle_word_id, game_date)
);

CREATE INDEX idx_wordle_attempts_user ON wordle_attempts(user_id);
CREATE INDEX idx_wordle_attempts_date ON wordle_attempts(game_date DESC);
CREATE INDEX idx_wordle_attempts_solved ON wordle_attempts(solved);

-- ============================================
-- WORD CONNECTIONS
-- ============================================

CREATE TABLE word_connection_puzzles (
    id SERIAL PRIMARY KEY,
    puzzle_name VARCHAR(100),
    puzzle_type VARCHAR(50) DEFAULT 'general' CHECK (puzzle_type IN ('general', 'sports', 'custom')),
    difficulty VARCHAR(20) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    puzzle_data JSONB NOT NULL, -- Categories and words
    is_daily BOOLEAN DEFAULT FALSE,
    daily_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_word_puzzles_daily ON word_connection_puzzles(is_daily, daily_date);
CREATE INDEX idx_word_puzzles_type ON word_connection_puzzles(puzzle_type);

-- ============================================
-- SPORTS EVENTS
-- ============================================

CREATE TABLE sports_events (
    id SERIAL PRIMARY KEY,
    sport_type VARCHAR(50) NOT NULL,
    league VARCHAR(50),
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    event_date TIMESTAMP WITH TIME ZONE NOT NULL,
    event_status VARCHAR(20) DEFAULT 'upcoming' CHECK (event_status IN ('upcoming', 'live', 'completed', 'cancelled')),
    home_score INTEGER,
    away_score INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sports_events_date ON sports_events(event_date DESC);
CREATE INDEX idx_sports_events_status ON sports_events(event_status);
CREATE INDEX idx_sports_events_sport ON sports_events(sport_type);

-- ============================================
-- PREDICTIONS
-- ============================================

CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sports_event_id INTEGER NOT NULL REFERENCES sports_events(id) ON DELETE CASCADE,
    prediction_type VARCHAR(50) NOT NULL CHECK (prediction_type IN ('winner', 'over_under', 'score')),
    prediction_data JSONB NOT NULL, -- Stores prediction details
    confidence_points INTEGER DEFAULT 0,
    is_correct BOOLEAN,
    points_earned INTEGER DEFAULT 0,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, sports_event_id, prediction_type)
);

CREATE INDEX idx_predictions_user ON predictions(user_id);
CREATE INDEX idx_predictions_event ON predictions(sports_event_id);
CREATE INDEX idx_predictions_type ON predictions(prediction_type);

-- ============================================
-- LEADERBOARDS
-- ============================================

CREATE TABLE leaderboards (
    id SERIAL PRIMARY KEY,
    leaderboard_type VARCHAR(50) NOT NULL CHECK (leaderboard_type IN ('global', 'friends', 'category', 'game_mode', 'weekly', 'monthly')),
    game_mode_id INTEGER REFERENCES game_modes(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    period_start DATE,
    period_end DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_leaderboards_type ON leaderboards(leaderboard_type);
CREATE INDEX idx_leaderboards_mode ON leaderboards(game_mode_id);

-- ============================================
-- LEADERBOARD ENTRIES
-- ============================================

CREATE TABLE leaderboard_entries (
    id SERIAL PRIMARY KEY,
    leaderboard_id INTEGER NOT NULL REFERENCES leaderboards(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    score INTEGER NOT NULL,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    accuracy DECIMAL(5, 2),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(leaderboard_id, user_id)
);

CREATE INDEX idx_leaderboard_entries_board ON leaderboard_entries(leaderboard_id);
CREATE INDEX idx_leaderboard_entries_user ON leaderboard_entries(user_id);
CREATE INDEX idx_leaderboard_entries_rank ON leaderboard_entries(rank ASC);

-- ============================================
-- NOTIFICATIONS
-- ============================================

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    action_url VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);

-- ============================================
-- AUDIT LOG (for admin actions)
-- ============================================

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    old_data JSONB,
    new_data JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trivia_questions_updated_at BEFORE UPDATE ON trivia_questions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sports_events_updated_at BEFORE UPDATE ON sports_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-create user profile on user creation
CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_profiles (user_id) VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_user_profile AFTER INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION create_user_profile();

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Global Leaderboard View
CREATE VIEW v_global_leaderboard AS
SELECT
    u.id,
    u.username,
    u.avatar_url,
    up.elo_rating,
    up.total_points,
    up.total_games_played,
    up.total_wins,
    CASE WHEN up.total_games_played > 0
         THEN ROUND((up.total_wins::DECIMAL / up.total_games_played * 100), 2)
         ELSE 0
    END as win_percentage,
    up.trivia_accuracy_percentage,
    RANK() OVER (ORDER BY up.elo_rating DESC) as rank
FROM users u
JOIN user_profiles up ON u.id = up.user_id
WHERE u.is_active = TRUE
ORDER BY up.elo_rating DESC;

-- Friends Leaderboard View
CREATE VIEW v_friends_leaderboard AS
SELECT
    f.user_id,
    u.id as friend_user_id,
    u.username,
    u.avatar_url,
    up.elo_rating,
    up.total_points,
    up.total_games_played,
    RANK() OVER (PARTITION BY f.user_id ORDER BY up.elo_rating DESC) as rank
FROM friendships f
JOIN users u ON f.friend_id = u.id
JOIN user_profiles up ON u.id = up.user_id
WHERE f.status = 'accepted' AND u.is_active = TRUE;

-- Recent Games View
CREATE VIEW v_recent_games AS
SELECT
    gs.id,
    gs.user_id,
    u.username,
    gm.display_name as game_mode,
    gs.score,
    gs.accuracy_percentage,
    gs.position,
    gs.completed,
    gs.started_at,
    gs.completed_at
FROM game_sessions gs
JOIN users u ON gs.user_id = u.id
JOIN game_modes gm ON gs.game_mode_id = gm.id
ORDER BY gs.started_at DESC;

-- ============================================
-- SAMPLE DATA FOR TESTING (Optional)
-- ============================================

-- Sample Category
INSERT INTO categories (name, description, difficulty_level) VALUES
('Science', 'General science questions', 'medium'),
('History', 'World history trivia', 'medium'),
('Sports', 'Sports knowledge', 'easy'),
('Geography', 'World geography', 'hard'),
('Pop Culture', 'Movies, music, and entertainment', 'easy');

-- ============================================
-- END OF SCHEMA
-- ============================================
