# Viral Researcher & Scripter - Build Summary

**Status:** Core Backend & Services Complete ✅
**Remaining:** Templates, Route Registration, Testing

---

## ✅ Completed Components

### 1. Database Migration
**File:** `supabase/migrations/20251221_create_viral_researcher_tables.sql`

Created 3 tables with full RLS policies and triggers:
- `viral_videos` - Stores video metadata, transcripts, view buckets
- `user_creator_profile` - Stores user profiles for personalization
- `generated_scripts` - Stores final scripts, titles, thumbnails, research

### 2. Service Layer (All Complete)

#### `app/services/creator_profile_service.py` ✅
- `profile_exists()` - Check if user has profile
- `get_user_profile()` - Retrieve profile
- `create_profile()` - Create new profile
- `update_profile()` - Update existing profile
- `get_profile_summary()` - Format for AI prompts

#### `app/services/viral_video_service.py` ✅
- `calculate_view_bucket()` - Categorize videos (5-10k, 10-50k, etc.)
- `check_channel_exists()` - Avoid re-scraping
- `scrape_channel()` - Fetch last 365 days of videos (>5 min)
- `get_videos_by_bucket()` - Filter videos
- `get_video_details()` - Single video info
- `get_bucket_stats()` - Video counts per bucket
- `get_all_channels()` - List scraped channels

#### `app/services/transcript_service.py` ✅
- `get_transcript_from_db()` - Check if transcript exists
- `fetch_transcript_from_apify()` - Fetch via Apify API
- `save_transcript()` - Store in database
- `fetch_transcript()` - Lazy loading with caching
- `bulk_fetch_transcripts()` - Multiple videos

#### `app/services/angle_generator_service.py` ✅
- `generate_angles()` - Claude generates 3-5 creative angles
- `_build_angle_prompt()` - Customized for user profile
- `_parse_angles_response()` - JSON parsing with fallback

#### `app/services/research_service.py` ✅
- `_exa_search()` - Find trending topics
- `_perplexity_search()` - Fact-check and recent news
- `_firecrawl_scrape()` - Scrape URLs from Exa/Perplexity
- `gather_research()` - Orchestrates all research sources
- `extract_claims_from_transcript()` - Find claims to verify

#### `app/services/research_synthesis_service.py` ✅
- `synthesize_research()` - Gemini processes raw research
- `_build_synthesis_prompt()` - Structured brief generation
- Outputs: new facts, statistics, quotes, narrative hooks

#### `app/services/script_generator_service.py` ✅
- `_load_knowledge_base()` - Loads viral video transcripts
- `generate_script()` - Claude writes full script
- `_build_script_prompt()` - Includes research brief + KB
- Outputs: script (1800-2200 words), 4 titles, 4 thumbnails

### 3. Routes
**File:** `app/routes/viral_researcher.py` ✅

Endpoints implemented:
- `GET /viral-researcher/` - Home page
- `POST /viral-researcher/scrape` - Scrape channels
- `GET /viral-researcher/videos/{channel_id}` - Video buckets
- `GET /viral-researcher/video/{video_id}` - Video details
- `POST /viral-researcher/video/{video_id}/fetch-transcript` - AJAX
- `POST /viral-researcher/video/{video_id}/generate-angles` - AJAX
- `POST /viral-researcher/generate-script` - Full workflow
- `GET /viral-researcher/script/{script_id}` - View script
- `GET /viral-researcher/my-scripts` - List user scripts

Includes `require_creator_profile()` middleware.

### 4. Configuration
**File:** `app/config.py` ✅

Added settings:
```python
# API Keys
apify_api_key: str
exa_api_key: str
perplexity_api_key: str
firecrawl_api_key: str

# Models
gemini_model: str = "gemini-2.0-flash"  # Research synthesis
claude_model: str = "claude-3-5-sonnet-20241022"  # Script writing

# Settings
video_min_duration: int = 300  # 5 minutes
max_videos_per_channel: int = 100
transcript_timeout: int = 60
```

### 5. Dependencies
**File:** `requirements.txt` ✅

Added packages:
```
exa-py==1.0.10
firecrawl-py==1.0.5
openai==1.57.4  # For Perplexity
```

---

## 🚧 Remaining Tasks

### 1. HTML Templates (Priority 1)
Need to create in `templates/`:

**viral_researcher_home.html**
- Channel input form
- List of previously scraped channels
- "Analyze Channels" button

**viral_videos_list.html**
- Bucket tabs (1M+, 100k-1M, 50-100k, 10-50k, 5-10k)
- Video grid with thumbnails
- "View Details" buttons

**video_details.html**
- Video embed
- Metadata display
- Transcript section (with lazy loading UI)
- "Fetch Transcript" button (if not loaded)
- "Re-Angle This Video" button

**angle_selection.html** (can be modal/AJAX)
- Display 3-5 angle cards
- Angle details (name, hook, differentiator)
- "Select This Angle" buttons
- "Generate Script" button

**script_output.html**
- Script display with section markers
- 4 title options (with copy buttons)
- 4 thumbnail descriptions (with copy buttons)
- Research sources (collapsible)
- "Download PDF" / "Try Different Angle" buttons

### 2. Route Registration (Priority 2)
**File:** `app/main.py`

Add:
```python
from app.routes import viral_researcher

app.include_router(viral_researcher.router)
```

### 3. Navigation Update (Priority 3)
**File:** `templates/base.html`

Add to navigation (line ~105):
```html
<a href="/viral-researcher" class="text-sm text-yt-text hover:text-yt-accent transition-colors">
    Viral Researcher
</a>
```

### 4. Creator Profile in Dashboard (Priority 3)
**File:** `templates/dashboard.html`

Add profile editor section:
- Form fields: creator_name, bio, niche, expertise_areas, tone_preference, target_audience
- Save button
- Required notice if empty

### 5. Knowledge Base Setup (Priority 4)
Run the Jupyter notebook to create `data/kb_full.pkl`:
```bash
cd /Users/arun/Desktop/00_Organized/Projects/python_projects/youtube-competitive-intelligence
jupyter notebook 2_apify_transcriptor.ipynb
# Run cells to create kb_full.pkl
# Move it to data/ directory
```

### 6. Database Migration (Priority 1)
Run Supabase migration:
```sql
-- In Supabase dashboard, run:
supabase/migrations/20251221_create_viral_researcher_tables.sql
```

### 7. Environment Variables
**File:** `.env`

Add these keys:
```
APIFY_API_KEY=your_key_here
EXA_API_KEY=your_key_here
PERPLEXITY_API_KEY=your_key_here
FIRECRAWL_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_claude_key_here  # Must use Sonnet now
```

### 8. Package Installation
```bash
cd /Users/arun/Desktop/00_Organized/Projects/python_projects/youtube-competitive-intelligence
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🔄 Complete Workflow (When Ready)

1. **User Setup**
   - User logs in
   - Creates creator profile (required)

2. **Channel Scraping**
   - User enters channel handles
   - System scrapes last 365 days (>5 min videos)
   - Videos categorized into buckets

3. **Video Selection**
   - User browses videos by bucket
   - Clicks video → sees details
   - Clicks "Fetch Transcript" (lazy load)

4. **Angle Generation**
   - User clicks "Re-Angle This Video"
   - Claude generates 3-5 angles based on profile
   - User selects preferred angle

5. **Script Generation**
   - System gathers research (Exa, Perplexity, Firecrawl)
   - Gemini synthesizes research into brief
   - Claude writes script using brief + knowledge base
   - Saves to database

6. **Output**
   - User sees script with 4 titles + 4 thumbnails
   - Can copy, download, or generate new angle

---

## 📊 Architecture Diagram

```
User Input (Channel Handle)
    ↓
Viral Video Service → YouTube API → Database
    ↓
User Browses Buckets (5-10k, 10-50k, etc.)
    ↓
User Clicks Video → Transcript Service → Apify API
    ↓
User Clicks "Re-Angle" → Angle Generator → Claude
    ↓
User Selects Angle
    ↓
Research Service → [Exa, Perplexity, Firecrawl]
    ↓
Research Synthesis → Gemini (creates brief)
    ↓
Script Generator → Claude + Knowledge Base
    ↓
Final Output: Script + Titles + Thumbnails
```

---

## 🎯 Next Steps for You

1. **Run database migration** in Supabase
2. **Add API keys** to `.env`
3. **Install new dependencies**: `pip install -r requirements.txt`
4. **Create HTML templates** (I can help with this)
5. **Register routes** in `main.py`
6. **Test the workflow** end-to-end

Let me know when you're ready to continue with the templates!

---

**Total Files Created:** 10
**Lines of Code:** ~2,500
**Estimated Implementation Time Remaining:** 4-6 hours (mostly frontend)
