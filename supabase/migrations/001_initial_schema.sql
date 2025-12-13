-- YouTube Context Engine - Initial Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. PROFILES - User Profile Extension
-- ============================================
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  avatar_url TEXT,

  -- Subscription
  subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro')),
  tests_used_this_month INT DEFAULT 0,
  tests_limit INT DEFAULT 5,

  -- Stripe billing
  stripe_customer_id TEXT UNIQUE,
  stripe_subscription_id TEXT,
  billing_cycle_start TIMESTAMPTZ DEFAULT NOW(),

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 2. USER API KEYS - User's Own Google API Keys
-- ============================================
CREATE TABLE user_api_keys (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,

  -- Encrypted API key (one key for YouTube + Gemini)
  google_api_key_encrypted TEXT,

  -- Validation
  key_verified BOOLEAN DEFAULT FALSE,
  last_verified_at TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER user_api_keys_updated_at BEFORE UPDATE ON user_api_keys
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 3. YOUTUBE CHANNELS - Cached Channel Data
-- ============================================
CREATE TABLE youtube_channels (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Channel identifiers
  channel_id TEXT UNIQUE NOT NULL, -- UC...
  channel_handle TEXT NOT NULL, -- @MrBeast
  channel_name TEXT, -- MrBeast
  channel_avatar_url TEXT,

  -- Stats
  subscriber_count BIGINT,

  -- Cache metadata
  last_fetched_at TIMESTAMPTZ DEFAULT NOW(),
  fetch_count INT DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT unique_channel_id UNIQUE(channel_id)
);

CREATE INDEX idx_channels_channel_id ON youtube_channels(channel_id);
CREATE INDEX idx_channels_handle ON youtube_channels(channel_handle);

-- ============================================
-- 4. YOUTUBE VIDEOS - Cached Video Data
-- ============================================
CREATE TABLE youtube_videos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Video identifiers
  video_id TEXT UNIQUE NOT NULL,
  channel_id TEXT NOT NULL REFERENCES youtube_channels(channel_id) ON DELETE CASCADE,

  -- Video metadata
  title TEXT NOT NULL,
  thumbnail_url TEXT NOT NULL, -- YouTube CDN URL (never expires)
  view_count BIGINT,
  published_at TIMESTAMPTZ,
  duration_seconds INT,
  is_short BOOLEAN DEFAULT FALSE,

  -- Cache metadata (no expiry - keep forever)
  last_fetched_at TIMESTAMPTZ DEFAULT NOW(),
  fetch_count INT DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT unique_video_id UNIQUE(video_id)
);

CREATE INDEX idx_videos_video_id ON youtube_videos(video_id);
CREATE INDEX idx_videos_channel_id ON youtube_videos(channel_id);

-- ============================================
-- 5. THUMBNAIL TESTS - User's Test Runs
-- ============================================
CREATE TABLE thumbnail_tests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Input data
  persona TEXT NOT NULL,
  video_title TEXT NOT NULL,

  -- File paths (local storage - files deleted after 24h)
  thumbnail_path TEXT NOT NULL, -- "static/uploads/abc.png"
  avatar_path TEXT, -- Optional
  thumbnail_expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',

  -- Results summary
  status TEXT DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
  channels_discovered TEXT[], -- ["@MrBeast", "@Veritasium"]
  total_videos_fetched INT,

  -- API usage tracking
  used_user_api_key BOOLEAN DEFAULT FALSE,

  -- Timestamps (keep records forever - only delete thumbnail files)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_tests_user_id ON thumbnail_tests(user_id, created_at DESC);
CREATE INDEX idx_tests_status ON thumbnail_tests(status);
CREATE INDEX idx_tests_expires ON thumbnail_tests(thumbnail_expires_at);

-- ============================================
-- 6. TEST VIDEOS - Videos in Each Test
-- ============================================
CREATE TABLE test_videos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  test_id UUID REFERENCES thumbnail_tests(id) ON DELETE CASCADE,
  video_id UUID REFERENCES youtube_videos(id) ON DELETE CASCADE,

  -- Position in this specific test (0-indexed)
  position INT NOT NULL,
  is_user_video BOOLEAN DEFAULT FALSE,

  created_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT unique_test_video UNIQUE(test_id, video_id)
);

CREATE INDEX idx_test_videos_test_id ON test_videos(test_id);

-- ============================================
-- 7. USAGE LOGS - Analytics & Audit Trail
-- ============================================
CREATE TABLE usage_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Action tracking
  action TEXT NOT NULL, -- 'test_created', 'api_key_added', 'subscription_upgraded'
  metadata JSONB, -- Flexible additional data

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_user_date ON usage_logs(user_id, created_at DESC);
CREATE INDEX idx_usage_action ON usage_logs(action);

-- ============================================
-- UTILITY FUNCTIONS
-- ============================================

-- Function to reset monthly test usage (called by cron)
CREATE OR REPLACE FUNCTION reset_monthly_tests()
RETURNS void AS $$
BEGIN
  UPDATE profiles
  SET
    tests_used_this_month = 0,
    billing_cycle_start = NOW()
  WHERE
    billing_cycle_start < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Function to check if user can create test
CREATE OR REPLACE FUNCTION can_create_test(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
  v_profile profiles%ROWTYPE;
  v_has_api_key BOOLEAN;
BEGIN
  -- Get user profile
  SELECT * INTO v_profile FROM profiles WHERE id = p_user_id;

  -- Check if user has their own API key
  SELECT EXISTS(
    SELECT 1 FROM user_api_keys
    WHERE user_id = p_user_id AND key_verified = TRUE
  ) INTO v_has_api_key;

  -- Allow if:
  -- 1. User has own verified API key (unlimited)
  -- 2. User is pro tier (higher limit)
  -- 3. User hasn't exceeded free tier limit
  RETURN (
    v_has_api_key OR
    v_profile.subscription_tier = 'pro' OR
    v_profile.tests_used_this_month < v_profile.tests_limit
  );
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE youtube_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE youtube_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE thumbnail_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can read/update their own profile
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

-- User API Keys: Users can manage their own keys
CREATE POLICY "Users can view own API keys" ON user_api_keys
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own API keys" ON user_api_keys
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own API keys" ON user_api_keys
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own API keys" ON user_api_keys
  FOR DELETE USING (auth.uid() = user_id);

-- YouTube Channels: Everyone can read (shared cache)
CREATE POLICY "Anyone can view channels" ON youtube_channels
  FOR SELECT USING (true);

-- YouTube Videos: Everyone can read (shared cache)
CREATE POLICY "Anyone can view videos" ON youtube_videos
  FOR SELECT USING (true);

-- Thumbnail Tests: Users can view/create their own tests
CREATE POLICY "Users can view own tests" ON thumbnail_tests
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own tests" ON thumbnail_tests
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Test Videos: Users can view videos from their tests
CREATE POLICY "Users can view own test videos" ON test_videos
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM thumbnail_tests
      WHERE id = test_id AND user_id = auth.uid()
    )
  );

-- Usage Logs: Users can view their own logs
CREATE POLICY "Users can view own usage logs" ON usage_logs
  FOR SELECT USING (auth.uid() = user_id);

-- ============================================
-- AUTOMATIC PROFILE CREATION
-- ============================================

-- Function to create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-create profile
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION handle_new_user();

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON TABLE profiles IS 'User profiles extending Supabase auth.users';
COMMENT ON TABLE user_api_keys IS 'User-provided Google API keys for unlimited tests';
COMMENT ON TABLE youtube_channels IS 'Cached YouTube channel data (shared across all users)';
COMMENT ON TABLE youtube_videos IS 'Cached YouTube video data (shared across all users)';
COMMENT ON TABLE thumbnail_tests IS 'User thumbnail test runs (thumbnails deleted after 24h, records kept forever)';
COMMENT ON TABLE test_videos IS 'Many-to-many link between tests and videos';
COMMENT ON TABLE usage_logs IS 'Audit trail and analytics';

-- ============================================
-- INITIAL DATA
-- ============================================

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;

-- Done!
SELECT 'Schema created successfully! 🚀' AS status;
