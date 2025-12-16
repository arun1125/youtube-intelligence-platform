-- Migration: Add Shot List (Production Planning) Tables
-- Description: Adds production_projects, production_videos, and production_shots tables for video production planning

-- Production Projects Table
CREATE TABLE IF NOT EXISTS production_projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Production Videos Table
CREATE TABLE IF NOT EXISTS production_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    project_id UUID REFERENCES production_projects(id) ON DELETE CASCADE,
    idea TEXT,
    hook TEXT,
    thumbnail_description TEXT,
    notes TEXT,
    global_vibe TEXT,
    font_preference TEXT DEFAULT 'mono' CHECK (font_preference IN ('mono', 'serif')),
    custom_column_defs JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Production Shots Table
CREATE TABLE IF NOT EXISTS production_shots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES production_videos(id) ON DELETE CASCADE,
    order_index INTEGER DEFAULT 0,
    shot_description TEXT,
    shot_type TEXT,
    script_line TEXT,
    music_link TEXT,
    vibes JSONB DEFAULT '[]'::jsonb,
    music_vibes JSONB DEFAULT '[]'::jsonb,
    music_inspiration TEXT,
    roll_type TEXT,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_production_projects_user_id ON production_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_production_projects_created_at ON production_projects(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_production_videos_user_id ON production_videos(user_id);
CREATE INDEX IF NOT EXISTS idx_production_videos_project_id ON production_videos(project_id);
CREATE INDEX IF NOT EXISTS idx_production_videos_created_at ON production_videos(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_production_shots_video_id ON production_shots(video_id);
CREATE INDEX IF NOT EXISTS idx_production_shots_order ON production_shots(video_id, order_index);

-- Row Level Security (RLS) Policies
ALTER TABLE production_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_shots ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for re-running migration)
DROP POLICY IF EXISTS "Users can manage their own projects" ON production_projects;
DROP POLICY IF EXISTS "Users can manage their own videos" ON production_videos;
DROP POLICY IF EXISTS "Users can manage their own shots" ON production_shots;

-- Projects: Users can only see/manage their own projects
CREATE POLICY "Users can manage their own projects"
    ON production_projects
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Videos: Users can only see/manage their own videos
CREATE POLICY "Users can manage their own videos"
    ON production_videos
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Shots: Users can manage shots for their own videos
CREATE POLICY "Users can manage their own shots"
    ON production_shots
    FOR ALL
    USING (
        video_id IN (
            SELECT id FROM production_videos WHERE user_id = auth.uid()
        )
    )
    WITH CHECK (
        video_id IN (
            SELECT id FROM production_videos WHERE user_id = auth.uid()
        )
    );

-- Update timestamps trigger function (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_production_projects_updated_at ON production_projects;
CREATE TRIGGER update_production_projects_updated_at
    BEFORE UPDATE ON production_projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_production_videos_updated_at ON production_videos;
CREATE TRIGGER update_production_videos_updated_at
    BEFORE UPDATE ON production_videos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_production_shots_updated_at ON production_shots;
CREATE TRIGGER update_production_shots_updated_at
    BEFORE UPDATE ON production_shots
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE production_projects IS 'Organizing container for production videos';
COMMENT ON TABLE production_videos IS 'Video production metadata and planning details';
COMMENT ON TABLE production_shots IS 'Individual shots within a video production with creative and technical specifications';
