# Viral Researcher & Scripter - Detailed Design Document

## 1. Overview

An AI-powered content engine that identifies high-performing YouTube videos and transforms them into original, data-backed scripts. The system analyzes viral content, identifies outliers, and uses AI to create new angles tailored to the user's expertise.

### Key Objectives
- Automate the discovery of viral content patterns
- Extract and analyze video transcripts
- Generate creative re-angles based on user's creator profile
- Produce publication-ready scripts with titles and thumbnail descriptions
- Integrate seamlessly with existing FastAPI application

---

## 2. Database Schema

### 2.1 `viral_videos` Table
Stores scraped video metadata and transcripts.

```sql
CREATE TABLE viral_videos (
    id SERIAL PRIMARY KEY,
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

-- Indexes for performance
CREATE INDEX idx_viral_videos_channel_id ON viral_videos(channel_id);
CREATE INDEX idx_viral_videos_view_bucket ON viral_videos(view_bucket);
CREATE INDEX idx_viral_videos_view_count ON viral_videos(view_count DESC);
```

### 2.2 `user_creator_profile` Table
Stores user's creator bio, niche, and preferences for AI re-angling.

```sql
CREATE TABLE user_creator_profile (
    id SERIAL PRIMARY KEY,
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
```

### 2.3 `generated_scripts` Table
Stores final outputs: scripts, titles, thumbnail descriptions, and research data.

```sql
CREATE TABLE generated_scripts (
    id SERIAL PRIMARY KEY,
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

-- Index for user queries
CREATE INDEX idx_generated_scripts_user_id ON generated_scripts(user_id);
CREATE INDEX idx_generated_scripts_created_at ON generated_scripts(created_at DESC);
```

---

## 3. Complete User Workflow

### 3.1 Initial Setup
1. **Profile Creation (Required)**
   - User navigates to Dashboard
   - If no creator profile exists, redirect to profile creation form
   - User fills out:
     - Creator name
     - Bio/background
     - Niche
     - Expertise areas
     - Tone preferences
     - Target audience
   - Profile saved to `user_creator_profile`

### 3.2 Channel Scraping Flow
1. **Navigation**
   - User clicks "Viral Researcher & Scripter" in top nav
   - Lands on channel input page

2. **Channel Input**
   - User enters YouTube channel handles (e.g., `@MrBeast`, `@Veritasium`) or URLs
   - Supports multiple channels (comma-separated or one per line)

3. **Smart Scraping Process**
   ```
   For each channel:
   a) Resolve handle to channel_id (using existing channel_resolver.py)
   b) Check database: SELECT * FROM viral_videos WHERE channel_id = ?
   c) If channel exists in DB:
      - Show message: "Channel already scraped on [date]"
      - Offer "Refresh Data" button
   d) If new or user clicks "Refresh Data":
      - Fetch last 365 days of videos via YouTube API
      - Filter: duration_seconds >= 300 (5+ minutes only)
      - Calculate view_bucket for each video:
        * 5,000-10,000 → '5-10k'
        * 10,000-50,000 → '10-50k'
        * 50,000-100,000 → '50-100k'
        * 100,000-1,000,000 → '100k-1M'
        * 1,000,000+ → '1M+'
      - Insert/update viral_videos table
      - DO NOT fetch transcripts yet (lazy loading)
   ```

4. **Video Display**
   - Show videos grouped by view_bucket
   - Display in descending order (highest bucket first)
   - Each bucket shows:
     - Bucket name (e.g., "100k - 1M Views")
     - Video count in bucket
     - Grid of video cards with:
       * Thumbnail
       * Title
       * View count
       * Duration
       * Channel name
       * "View Details" button

### 3.3 Video Details & Transcript Loading
1. **User Clicks Video**
   - Navigate to video details page
   - Display metadata immediately

2. **Lazy Transcript Loading**
   ```
   a) Check database: SELECT transcript FROM viral_videos WHERE video_id = ?
   b) If transcript EXISTS and NOT NULL:
      - Display transcript immediately
   c) If transcript is NULL:
      - Show loading message: "Fetching transcript... This may take up to 1 minute"
      - Call Apify API (actor: "Uwpce1RSXlrzF6WBA")
      - Parse response and extract transcript text
      - UPDATE viral_videos SET transcript = ?, transcript_fetched_at = NOW()
      - Display transcript
   d) If Apify fails:
      - Show error: "Unable to fetch transcript. Video may not have captions."
   ```

3. **Video Details Page Shows**
   - Video embed (YouTube player)
   - Title, views, duration, publish date
   - Full transcript (scrollable)
   - "Re-Angle This Video" button (primary CTA)

### 3.4 Re-Angling Process (Phase 3)
1. **User Clicks "Re-Angle This Video"**
   - Show loading state: "Analyzing video and generating angles..."

2. **AI Analysis (Claude)**
   ```
   Input to Claude:
   - Original video title
   - Original video transcript
   - User creator profile (bio, niche, expertise, tone)

   Prompt:
   "Analyze this viral video transcript and generate 3-5 alternative angles
   for creating a similar video tailored to this creator's profile.

   Original Title: [title]
   Transcript: [transcript]

   Creator Profile:
   - Niche: [niche]
   - Expertise: [expertise_areas]
   - Tone: [tone_preference]
   - Target Audience: [target_audience]

   For each angle, provide:
   1. Angle Name (e.g., 'Technical Deep Dive', 'Contrarian Take')
   2. Core Hook (one sentence)
   3. Key Differentiator (what makes this angle unique)
   4. Target Emotion (curiosity, controversy, inspiration, etc.)
   "
   ```

3. **Display Angle Options**
   - Show 3-5 cards with angle options
   - Each card shows:
     * Angle name
     * Core hook
     * Key differentiator
     * "Select This Angle" button

4. **User Selects Angle**
   - Highlight selected angle
   - Show "Generate Script" button

### 3.5 Script Production (Phase 4)
1. **Deep Research Phase**
   ```
   When user clicks "Generate Script":

   a) EXA AI Search:
      - Query: "trending topics about [video topic] in [niche]"
      - Extract top 5-10 trending topics/articles
      - Collect URLs for further scraping

   b) Perplexity Fact-Checking:
      - Query: "recent news and data about [main claims in transcript]"
      - Verify facts from original video
      - Find updated statistics or newer developments

   c) Firecrawl Scraping:
      - For each URL from Exa/Perplexity:
        * Scrape full article content
        * Extract key facts, quotes, data points
      - Compile research findings into raw data

   Raw Research Data Structure:
   {
     "trending_topics": [
       {"title": "...", "url": "...", "content": "..."}
     ],
     "fact_checks": [
       {"original_claim": "...", "verification": "...", "source": "..."}
     ],
     "new_data": [
       {"data_point": "...", "source": "...", "url": "..."}
     ],
     "scraped_content": [
       {"url": "...", "raw_content": "...", "key_excerpts": ["..."]}
     ]
   }
   ```

2. **Research Synthesis (Gemini)**
   ```
   Input to Gemini:
   - Original video transcript
   - Selected angle
   - Raw research data (Exa + Perplexity + Firecrawl)
   - User creator profile

   Prompt:
   "Analyze and synthesize this research data into a structured brief
   for script writing.

   Original Video: [title]
   Transcript Summary: [first 500 words + key points]
   Selected Angle: [angle name and description]

   Raw Research Data:
   - Trending Topics: [Exa results]
   - Fact Checks: [Perplexity results]
   - New Data Points: [combined findings]
   - Scraped Content: [Firecrawl results]

   Your task:
   1. Identify 5-8 NEW facts/data points NOT in the original video
   2. Find contradictions or updates to original video claims
   3. Extract compelling statistics, quotes, and examples
   4. Organize by narrative flow (hook → body → conclusion)
   5. Note which sources are most credible/relevant
   6. Suggest narrative hooks based on most compelling findings

   Output format: Structured JSON for script writer
   "

   Gemini Output (Research Brief):
   {
     "executive_summary": "...",
     "new_facts": [
       {
         "fact": "...",
         "source": "...",
         "credibility": "high/medium/low",
         "placement_suggestion": "hook/introduction/body/conclusion"
       }
     ],
     "updated_claims": [
       {"original": "...", "update": "...", "source": "..."}
     ],
     "key_statistics": [...],
     "compelling_quotes": [...],
     "narrative_hooks": ["...", "...", "..."],
     "supporting_evidence": [...]
   }
   ```

3. **Script Generation (Claude)**
   ```
   Input to Claude:
   - Original video transcript
   - Selected angle
   - Research Brief (pre-synthesized by Gemini)
   - User creator profile

   Knowledge Base:
   - Transcripts from viral videos on how to write & make good videos
     (stored from 2_apify_transcriptor.ipynb)

   Prompt:
   "Create a high-retention YouTube script using this research brief and angle.

   Original Video Context:
   - Title: [title]
   - Main Points: [summary from transcript]

   Selected Angle: [angle name and full description]

   Research Brief (Pre-Synthesized by Research Team):
   [Gemini's structured JSON output with:
    - Executive summary
    - 5-8 new facts with sources and placement suggestions
    - Updated claims/contradictions
    - Key statistics and quotes
    - Suggested narrative hooks
    - Supporting evidence]

   Creator Profile:
   - Name: [creator_name]
   - Niche: [niche]
   - Tone: [tone_preference]
   - Target Audience: [target_audience]
   - Expertise: [expertise_areas]

   Knowledge Base (Best Practices):
   [Transcripts from viral "how to make videos" content showing
    proven hooks, structures, and retention techniques]

   Requirements:
   - Hook in first 5 seconds using the most compelling fact from research brief
   - Clear narrative structure following proven retention patterns
   - Incorporate ALL new facts from research brief naturally (cite sources)
   - Match creator's tone and speak directly to target audience
   - Length: 8-12 minutes (approximately 1800-2200 words)
   - Use storytelling and pattern interrupts to maintain engagement

   Structure:
   1. HOOK (0-5 seconds) - Use narrative hook from research brief
   2. INTRODUCTION (5-30 seconds) - Set up angle and value promise
   3. MAIN CONTENT (7-10 minutes) - Weave in new research with examples
   4. CONCLUSION & CTA (30-60 seconds) - Recap and strong call to action

   Also generate:
   - 4 high-CTR title variations (use power words specific to niche)
   - 4 thumbnail description variations (visual concepts that create curiosity)

   Format: Return as structured JSON with fields: script, titles[], thumbnails[]
   "
   ```

3. **Save & Display Results**
   ```
   INSERT INTO generated_scripts (
     user_id,
     original_video_id,
     selected_angle,
     angle_options,
     script,
     titles,
     thumbnail_descriptions,
     research_data
   ) VALUES (...)
   ```

4. **Results Page Shows**
   - Full script (with section markers)
   - 4 title options (with copy buttons)
   - 4 thumbnail descriptions (with copy buttons)
   - Research sources (expandable section)
   - "Download as PDF" button
   - "Generate New Angle" button (to try different angle)
   - "Start Over" button (to select different video)

---

## 4. API Integrations

### 4.1 YouTube Data API
- **Purpose:** Fetch video metadata
- **Endpoints Used:**
  - `channels().list()` - Get channel info
  - `playlistItems().list()` - Get uploads
  - `videos().list()` - Get video details
- **Rate Limits:** 10,000 units/day
- **Configuration:** Existing `youtube_service.py`

### 4.2 Apify API
- **Purpose:** Extract video transcripts
- **Actor ID:** `"Uwpce1RSXlrzF6WBA"`
- **Input Format:**
  ```python
  {
      "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
      "language": "en"
  }
  ```
- **Rate Limits:** Based on Apify plan
- **Error Handling:**
  - Retry once on failure
  - Show user-friendly message if no transcript available

### 4.3 Gemini (Google)
- **Purpose:** Research synthesis, data analysis
- **Model:** `gemini-2.0-flash` (fast, cost-effective for data processing)
- **Configuration:** Existing `GEMINI_API_KEY` in settings
- **Usage:**
  1. Research synthesis: ~15k tokens input, ~2k tokens output
  2. Converts raw research data into structured brief for Claude

### 4.4 Claude (Anthropic)
- **Purpose:** Creative re-angling, script writing
- **Model:** `claude-3-5-sonnet-20241022` (best for creative tasks)
- **Configuration:** Existing `ANTHROPIC_API_KEY` in settings
- **Usage:**
  1. Angle generation: ~2k tokens input, ~1k tokens output
  2. Script generation: ~12k tokens input (includes Gemini brief), ~5k tokens output

### 4.5 Exa AI
- **Purpose:** Search for trending topics in niche
- **API Key:** `EXA_API_KEY` in .env
- **Example Query:**
  ```python
  exa.search(
      query=f"trending topics about {video_topic} in {user_niche}",
      num_results=10,
      use_autoprompt=True
  )
  ```

### 4.6 Perplexity AI
- **Purpose:** Fact-checking, recent news/data
- **API Key:** `PERPLEXITY_API_KEY` in .env
- **Example Query:**
  ```python
  perplexity.chat.completions.create(
      model="sonar",
      messages=[{
          "role": "user",
          "content": f"Find recent news and data about: {claims}"
      }]
  )
  ```

### 4.7 Firecrawl
- **Purpose:** Scrape URLs from Exa/Perplexity
- **API Key:** `FIRECRAWL_API_KEY` in .env
- **Usage:**
  ```python
  firecrawl.scrape_url(
      url=article_url,
      params={"formats": ["markdown", "html"]}
  )
  ```

---

## 5. AI Workflow Summary

**Two-Tier AI Architecture for Cost & Quality Optimization:**

1. **Gemini (Research Synthesizer)**
   - Fast and cost-effective
   - Processes raw data from Exa, Perplexity, and Firecrawl
   - Outputs structured JSON brief with organized facts, statistics, and hooks
   - Handles large amounts of data efficiently

2. **Claude (Creative Writer)**
   - Best-in-class for creative writing
   - Receives clean, synthesized research brief from Gemini
   - Focuses purely on script quality and narrative structure
   - Uses knowledge base of viral video transcripts for proven patterns

This separation of concerns ensures:
- Lower costs (Gemini handles data-heavy tasks)
- Higher quality (Claude focuses on creativity)
- Faster processing (parallel execution possible)
- Better results (each AI does what it's best at)

---

## 6. UI/UX Structure

### 6.1 Navigation
- **Top-level nav item:** "Viral Researcher & Scripter"
- **Accessible after:** Profile creation required

### 6.2 Page Structure

#### Page 1: Channel Input
- **URL:** `/viral-researcher`
- **Elements:**
  - Heading: "Viral Researcher & Scripter"
  - Textarea: "Enter YouTube channel handles (e.g., @MrBeast)"
  - Button: "Analyze Channels"
  - Previously scraped channels list (optional)

#### Page 2: Video Buckets
- **URL:** `/viral-researcher/videos/{channel_id}`
- **Elements:**
  - Channel info header (name, thumbnail)
  - "Refresh Data" button
  - Bucket tabs/sections:
    * 1M+ Views
    * 100k-1M Views
    * 50-100k Views
    * 10-50k Views
    * 5-10k Views
  - Video grid (within each bucket)

#### Page 3: Video Details
- **URL:** `/viral-researcher/video/{video_id}`
- **Elements:**
  - Video embed
  - Metadata (title, views, date, duration)
  - Transcript section (with loading state)
  - "Re-Angle This Video" button
  - "Back to Videos" link

#### Page 4: Angle Selection
- **URL:** `/viral-researcher/video/{video_id}/angles`
- **Elements:**
  - Original video reference (thumbnail + title)
  - 3-5 angle cards (selectable)
  - "Generate Script" button (enabled when angle selected)
  - Loading state during angle generation

#### Page 5: Script Output
- **URL:** `/viral-researcher/script/{script_id}`
- **Elements:**
  - Tabbed interface:
    * Script tab
    * Titles tab (4 options)
    * Thumbnails tab (4 descriptions)
    * Research tab (sources + findings)
  - Copy buttons for each element
  - "Download PDF" button
  - "Try Different Angle" button
  - "Back to Videos" button

#### Dashboard Addition: Creator Profile Editor
- **URL:** `/dashboard` (existing page)
- **New Section:** "Creator Profile"
  - Edit form for all profile fields
  - Save button
  - "Required for Viral Researcher" notice if empty

---

## 7. Technical Implementation Details

### 7.1 Service Layer Structure

Create new services in `app/services/`:

1. **`viral_video_service.py`**
   - `scrape_channel(channel_id: str, days: int = 365)`
   - `get_videos_by_bucket(channel_id: str, bucket: str)`
   - `get_video_details(video_id: str)`
   - `calculate_view_bucket(view_count: int) -> str`
   - `check_channel_exists(channel_id: str) -> bool`

2. **`transcript_service.py`**
   - `fetch_transcript(video_id: str) -> str`
   - `get_transcript_from_db(video_id: str) -> Optional[str]`
   - `save_transcript(video_id: str, transcript: str)`

3. **`angle_generator_service.py`**
   - `generate_angles(video_data: dict, profile: dict) -> List[dict]`
   - `_build_angle_prompt(video_data, profile) -> str`

4. **`research_service.py`**
   - `gather_research(video_topic: str, claims: List[str]) -> dict`
   - `_exa_search(query: str) -> dict`
   - `_perplexity_search(query: str) -> dict`
   - `_firecrawl_scrape(url: str) -> dict`
   - Returns raw research data for synthesis

5. **`research_synthesis_service.py`**
   - `synthesize_research(raw_research: dict, video_data: dict, profile: dict) -> dict`
   - Uses Gemini to process and organize research
   - Outputs structured brief for script writing

6. **`script_generator_service.py`**
   - `generate_script(angle: str, research_brief: dict, profile: dict, kb: dict) -> dict`
   - Uses Claude with Gemini's synthesized brief
   - Includes knowledge base from viral video transcripts
   - Outputs script, titles, thumbnails

7. **`creator_profile_service.py`**
   - `get_user_profile(user_id: str) -> Optional[dict]`
   - `create_profile(user_id: str, data: dict)`
   - `update_profile(user_id: str, data: dict)`
   - `profile_exists(user_id: str) -> bool`

### 7.2 Route Structure

Create new routes in `app/routes/viral_researcher.py`:

```python
@router.get("/viral-researcher")
async def viral_researcher_home()

@router.post("/viral-researcher/scrape")
async def scrape_channels(channel_handles: List[str])

@router.get("/viral-researcher/videos/{channel_id}")
async def list_videos(channel_id: str, bucket: Optional[str])

@router.get("/viral-researcher/video/{video_id}")
async def video_details(video_id: str)

@router.post("/viral-researcher/video/{video_id}/angles")
async def generate_angles(video_id: str)

@router.post("/viral-researcher/generate-script")
async def generate_script(video_id: str, selected_angle: str)

@router.get("/viral-researcher/script/{script_id}")
async def view_script(script_id: int)
```

### 7.3 Configuration Updates

Add to `app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Apify
    apify_api_key: str
    apify_transcript_actor: str = "Uwpce1RSXlrzF6WBA"

    # Research APIs
    exa_api_key: str
    perplexity_api_key: str
    firecrawl_api_key: str

    # Viral Researcher Settings
    video_min_duration: int = 300  # 5 minutes
    max_videos_per_channel: int = 100  # Last 365 days cap
    transcript_timeout: int = 60  # seconds
```

### 7.4 Database Migrations

Create Supabase migration file:

```sql
-- Migration: create_viral_researcher_tables
-- Created: [DATE]

-- viral_videos table
CREATE TABLE viral_videos (
    -- [schema from section 2.1]
);

-- user_creator_profile table
CREATE TABLE user_creator_profile (
    -- [schema from section 2.2]
);

-- generated_scripts table
CREATE TABLE generated_scripts (
    -- [schema from section 2.3]
);

-- Indexes
CREATE INDEX idx_viral_videos_channel_id ON viral_videos(channel_id);
CREATE INDEX idx_viral_videos_view_bucket ON viral_videos(view_bucket);
-- ... etc
```

### 7.5 Frontend Templates

Create new Jinja2 templates in `templates/`:

1. `viral_researcher_home.html` - Channel input page
2. `viral_videos_list.html` - Video buckets page
3. `video_details.html` - Video details + transcript
4. `angle_selection.html` - Choose from 3-5 angles
5. `script_output.html` - Final script + titles + thumbnails
6. `creator_profile_form.html` - Profile editor (in dashboard)

### 7.6 Error Handling Strategy

```python
# Transcript fetching
try:
    transcript = await transcript_service.fetch_transcript(video_id)
except ApifyTimeout:
    return {"error": "Transcript fetch timed out. Please try again."}
except ApifyError:
    return {"error": "Unable to fetch transcript. Video may lack captions."}

# AI generation
try:
    angles = await angle_generator.generate_angles(video, profile)
except AnthropicAPIError:
    return {"error": "AI service temporarily unavailable. Please try again."}

# Research APIs
try:
    research = await script_generator.research_topic(topic)
except ExaAPIError as e:
    logger.warning(f"Exa failed: {e}, continuing with partial research")
    # Continue with degraded functionality
```

---

## 8. Implementation Phases

### Phase 1: Foundation (Days 1-2)
- [ ] Create database tables and migrations
- [ ] Build `creator_profile_service.py`
- [ ] Create profile editor UI in dashboard
- [ ] Add profile requirement middleware

### Phase 2: Video Scraping (Days 3-4)
- [ ] Build `viral_video_service.py`
- [ ] Create channel input page
- [ ] Implement smart scraping logic
- [ ] Build video buckets display page

### Phase 3: Transcripts (Days 5-6)
- [ ] Build `transcript_service.py`
- [ ] Integrate Apify API
- [ ] Create video details page
- [ ] Implement lazy loading UI

### Phase 4: Re-Angling (Days 7-8)
- [ ] Build `angle_generator_service.py`
- [ ] Create angle selection UI
- [ ] Integrate Claude API for angle generation
- [ ] Add angle preview cards

### Phase 5: Script Production (Days 9-11)
- [ ] Build `script_generator_service.py`
- [ ] Integrate Exa AI
- [ ] Integrate Perplexity
- [ ] Integrate Firecrawl
- [ ] Create script output page
- [ ] Add PDF export functionality

### Phase 6: Polish & Testing (Days 12-14)
- [ ] End-to-end testing
- [ ] Error handling refinement
- [ ] UI/UX polish
- [ ] Performance optimization
- [ ] Documentation

---

## 9. Key Decisions Summary

| Decision Point | Choice |
|----------------|--------|
| Scraping frequency | Manual refresh only |
| Transcript loading | Lazy (on-demand when user clicks) |
| View buckets | Absolute counts (5-10k, 10-50k, 50-100k, 100k-1M, 1M+) |
| Profile requirement | Mandatory before accessing feature |
| AI Architecture | Two-tier: Gemini for research synthesis, Claude for script writing |
| Video duration filter | >= 5 minutes only |
| Navigation | Top-level nav item |
| Profile editor location | Dashboard (with subscription info) |
| Angle count | 3-5 options per video |
| Title/thumbnail count | 4 variations each |
| Knowledge base | Viral video transcripts from 2_apify_transcriptor.ipynb |

---

## 10. Success Metrics

- **User Engagement:**
  - % of users who complete profile creation
  - Average videos analyzed per user
  - Script generation completion rate

- **Performance:**
  - Video scraping time < 30 seconds per channel
  - Transcript fetch time < 60 seconds
  - Angle generation time < 20 seconds
  - Full script generation time < 2 minutes

- **Quality:**
  - User satisfaction with generated scripts
  - Re-generation rate (lower is better)
  - Scripts used for actual video production

---

## 11. Future Enhancements (Post-MVP)

1. **Batch Processing**
   - Scrape multiple channels at once
   - Pre-fetch transcripts in background

2. **Advanced Analytics**
   - Track which angles perform best
   - A/B testing for titles/thumbnails

3. **Collaboration Features**
   - Share scripts with team
   - Comment on angles

4. **Export Options**
   - Export to Google Docs
   - Integration with video editing tools

5. **Smart Recommendations**
   - AI suggests which videos to re-angle
   - Predict which buckets have best ROI

---

**Document Version:** 1.0
**Last Updated:** 2025-12-21
**Status:** Ready for Implementation
