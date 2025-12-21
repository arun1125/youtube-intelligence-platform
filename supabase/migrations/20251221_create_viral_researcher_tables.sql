-- Migration: Create Viral Researcher & Scripter Tables
-- Created: 2025-12-21
-- Description: Tables for viral video analysis, creator profiles, and generated scripts

-- =====================================================
-- Table 1: viral_videos
-- Stores scraped video metadata and transcripts
-- =====================================================
CREATE TABLE IF NOT EXISTS viral_videos (
    id BIGSERIAL PRIMARY KEY,
    video_id VARCHAR(20) UNIQUE NOT NULL,
    channel_id VARCHAR(30) NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    thumbnail_url TEXT,
    view_count BIGINT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    published_at TIMESTAMP NOT NULL,
    video_url TEXT NOT NULL,
    transcript TEXT,  -- NULL until fetched
    transcript_fetched_at TIMESTAMP,
    view_bucket VARCHAR(20),  -- '5-10k', '10-50k', '50-100k', '100k-1M', '1M+'
    scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for viral_videos
CREATE INDEX IF NOT EXISTS idx_viral_videos_channel_id ON viral_videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_viral_videos_view_bucket ON viral_videos(view_bucket);
CREATE INDEX IF NOT EXISTS idx_viral_videos_view_count ON viral_videos(view_count DESC);
CREATE INDEX IF NOT EXISTS idx_viral_videos_published_at ON viral_videos(published_at DESC);

-- =====================================================
-- Table 2: user_creator_profile
-- Stores user's creator bio, niche, and preferences
-- =====================================================
CREATE TABLE IF NOT EXISTS user_creator_profile (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) UNIQUE NOT NULL,
    creator_name VARCHAR(255),
    bio TEXT,
    niche VARCHAR(255),  -- e.g., "Tech Education", "Fitness", "Finance"
    expertise_areas TEXT[],  -- Array: ["Python", "AI", "Web Development"]
    tone_preference VARCHAR(100),  -- e.g., "Educational", "Entertaining", "Professional"
    target_audience TEXT,
    additional_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for user_creator_profile
CREATE INDEX IF NOT EXISTS idx_user_creator_profile_user_id ON user_creator_profile(user_id);

-- =====================================================
-- Table 3: generated_scripts
-- Stores final outputs: scripts, titles, thumbnails
-- =====================================================
CREATE TABLE IF NOT EXISTS generated_scripts (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    original_video_id VARCHAR(20) REFERENCES viral_videos(video_id),
    selected_angle TEXT NOT NULL,  -- The angle user chose from 3-5 options
    angle_options JSONB,  -- Store all 3-5 angles that were generated
    script TEXT NOT NULL,
    titles TEXT[],  -- Array of 4 optimized titles
    thumbnail_descriptions TEXT[],  -- Array of 4 thumbnail concepts
    research_data JSONB,  -- Store Exa/Perplexity/Firecrawl findings
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for generated_scripts
CREATE INDEX IF NOT EXISTS idx_generated_scripts_user_id ON generated_scripts(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_scripts_created_at ON generated_scripts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_scripts_original_video_id ON generated_scripts(original_video_id);

-- =====================================================
-- Row Level Security (RLS) Policies
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE user_creator_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_scripts ENABLE ROW LEVEL SECURITY;
-- Note: viral_videos is shared across users, no RLS needed

-- Policy: Users can only read/write their own creator profile
CREATE POLICY user_creator_profile_select_policy ON user_creator_profile
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY user_creator_profile_insert_policy ON user_creator_profile
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_creator_profile_update_policy ON user_creator_profile
    FOR UPDATE USING (auth.uid() = user_id);

-- Policy: Users can only read/write their own generated scripts
CREATE POLICY generated_scripts_select_policy ON generated_scripts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY generated_scripts_insert_policy ON generated_scripts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY generated_scripts_update_policy ON generated_scripts
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY generated_scripts_delete_policy ON generated_scripts
    FOR DELETE USING (auth.uid() = user_id);

-- =====================================================
-- Triggers for updated_at timestamps
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for viral_videos
CREATE TRIGGER update_viral_videos_updated_at
    BEFORE UPDATE ON viral_videos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for user_creator_profile
CREATE TRIGGER update_user_creator_profile_updated_at
    BEFORE UPDATE ON user_creator_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for generated_scripts
CREATE TRIGGER update_generated_scripts_updated_at
    BEFORE UPDATE ON generated_scripts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Comments for documentation
-- =====================================================

COMMENT ON TABLE viral_videos IS 'Stores YouTube video metadata and transcripts for viral content analysis';
COMMENT ON TABLE user_creator_profile IS 'Stores creator profiles for personalizing script generation';
COMMENT ON TABLE generated_scripts IS 'Stores AI-generated scripts, titles, and thumbnails with research data';

COMMENT ON COLUMN viral_videos.view_bucket IS 'Categorizes videos: 5-10k, 10-50k, 50-100k, 100k-1M, 1M+';
COMMENT ON COLUMN viral_videos.transcript IS 'Fetched lazily via Apify when user views video details';
COMMENT ON COLUMN user_creator_profile.expertise_areas IS 'PostgreSQL array of expertise topics';
COMMENT ON COLUMN generated_scripts.angle_options IS 'JSON array of 3-5 angles generated by AI';
COMMENT ON COLUMN generated_scripts.research_data IS 'JSON object containing Exa, Perplexity, and Firecrawl results';
