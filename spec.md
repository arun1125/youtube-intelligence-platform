# YouTube Context Engine - Complete Technical Specification

> **Last Updated:** December 2024
> **Status:** Production-Ready (with pending features)
> **Version:** 1.0.0

---

## 1. Executive Summary

### What is YouTube Context Engine?

A SaaS web application that helps YouTubers test how their thumbnails perform against real competitors by simulating a YouTube homepage. Users input their target viewer persona, upload their thumbnail, and the system generates a realistic YouTube homepage grid featuring their video mixed with real competitor videos.

### Core Value Proposition

- **For YouTubers:** See how your thumbnail performs in the real context of your competitors
- **AI-Powered:** Automatically discovers relevant competitor channels based on viewer persona
- **Data-Driven:** Uses real YouTube data (actual videos, thumbnails, view counts)
- **Instant Feedback:** No need to publish - test thumbnails before going live

---

## 2. Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.9+)
- **Server:** Uvicorn (ASGI)
- **Settings Management:** Pydantic Settings
- **API Integration:** Google Gemini AI, YouTube Data API v3

### Frontend
- **Templating:** Jinja2
- **CSS Framework:** Tailwind CSS (via CDN)
- **Interactivity:** HTMX (for dynamic updates without full page reloads)
- **Design:** YouTube Dark Mode clone

### Database & Storage
- **Database:** Supabase (PostgreSQL)
- **Authentication:** Supabase Auth (Google OAuth)
- **File Storage:** Local filesystem (`static/uploads/`)
- **Data Logging:** CSV files (`data/competitor_data.csv`)

### Payment Processing
- **Payment Gateway:** Stripe
- **Subscription Model:** Monthly recurring ($10/month Pro plan)
- **Webhook Handling:** Stripe webhooks for subscription events

### Deployment
- **Platform:** Render.com
- **Environment:** Docker-ready (Dockerfile included)
- **CI/CD:** Git-based deployments

---

## 3. Architecture Overview

### Design Pattern
**Service-Oriented Architecture** with clear separation of concerns:

```
Routes (HTTP Handlers)
    ↓
Services (Business Logic)
    ↓
Database / External APIs
```

### Key Principles
1. **Stateless:** Each request is independent (sessions stored in cookies + database)
2. **Async:** Uses FastAPI's async capabilities for concurrent operations
3. **Type-Safe:** Pydantic models for all data validation
4. **Cacheable:** Video and channel data cached in database to reduce API calls

---

## 4. Directory Structure

```
youtube-competitive-intelligence/
├── app/
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # Configuration (Pydantic Settings)
│   │
│   ├── routes/                     # HTTP request handlers
│   │   ├── __init__.py
│   │   ├── auth.py                 # Authentication (login, logout, callback)
│   │   ├── dashboard.py            # User dashboard
│   │   ├── payment.py              # Stripe checkout & webhooks
│   │   ├── thumbnail.py            # Main feature (generate, shuffle, preview)
│   │   └── user.py                 # User profile management
│   │
│   ├── services/                   # Business logic layer
│   │   ├── __init__.py
│   │   ├── ai_service.py           # Gemini AI channel discovery
│   │   ├── auth_service.py         # Authentication logic
│   │   ├── cleanup_service.py      # File cleanup (24h expiry)
│   │   ├── data_service.py         # CSV logging
│   │   ├── stripe_service.py       # Payment processing
│   │   ├── supabase_client.py      # Database client
│   │   └── youtube_service.py      # YouTube API integration
│   │
│   ├── models/                     # Data models
│   │   ├── __init__.py
│   │   ├── database.py             # Database schema models
│   │   └── schemas.py              # API request/response schemas
│   │
│   ├── middleware/                 # Request middleware
│   │   ├── __init__.py
│   │   └── auth.py                 # Auth decorators (require_auth, optional_auth)
│   │
│   └── utils/                      # Helper functions
│       ├── __init__.py
│       ├── channel_resolver.py     # Channel handle → ID resolution
│       ├── helpers.py              # Formatting, file upload
│       └── session.py              # Session management
│
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                   # Base layout (header, footer)
│   ├── index.html                  # Landing page + test form
│   ├── dashboard.html              # User dashboard
│   ├── upgrade.html                # Pricing/upgrade page
│   ├── test_detail.html            # Individual test view
│   └── components/
│       └── video_grid.html         # Video grid component (HTMX target)
│
├── static/                         # Static files
│   └── uploads/                    # User-uploaded thumbnails (auto-cleanup)
│
├── data/                           # Data files
│   └── competitor_data.csv         # All fetched video data
│
├── old_code/                       # Archived prototype scripts
│
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker container config
├── render.yaml                     # Render.com deployment config
├── .env.example                    # Environment variable template
├── .env                            # Environment variables (git-ignored)
├── README.md                       # Setup instructions
├── ROADMAP.md                      # Feature roadmap
└── spec.md                         # This file
```

---

## 5. Database Schema (Supabase PostgreSQL)

### 5.1 `profiles` - User Profiles
Extends Supabase's built-in `auth.users` table.

```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    full_name TEXT,
    avatar_url TEXT,

    -- Subscription info
    subscription_tier TEXT DEFAULT 'free',  -- 'free' | 'pro'
    tests_used_this_month INTEGER DEFAULT 0,
    tests_limit INTEGER DEFAULT 5,

    -- Billing
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    billing_cycle_start TIMESTAMPTZ DEFAULT NOW(),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Purpose:** Store user profile data and subscription status.

**Key Fields:**
- `subscription_tier`: 'free' (5 tests/month) or 'pro' (unlimited)
- `tests_used_this_month`: Counter reset monthly
- `stripe_customer_id`: Links to Stripe customer

---

### 5.2 `youtube_channels` - Cached Channel Data
Shared cache of YouTube channels to reduce API calls.

```sql
CREATE TABLE youtube_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id TEXT UNIQUE NOT NULL,        -- UC...
    channel_handle TEXT,                    -- @MrBeast
    channel_name TEXT,                      -- MrBeast
    channel_avatar_url TEXT,
    subscriber_count BIGINT,

    -- Cache metadata
    last_fetched_at TIMESTAMPTZ DEFAULT NOW(),
    fetch_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Purpose:** Cache channel info to avoid re-fetching.

**Key Logic:**
- Upsert on `channel_id` (insert if new, update if exists)
- Never expires (YouTube channels don't change often)

---

### 5.3 `youtube_videos` - Cached Video Data
Shared cache of YouTube videos.

```sql
CREATE TABLE youtube_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id TEXT UNIQUE NOT NULL,
    channel_id TEXT NOT NULL,

    -- Video metadata
    title TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,
    view_count BIGINT,
    published_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    is_short BOOLEAN DEFAULT FALSE,

    -- Cache metadata
    last_fetched_at TIMESTAMPTZ DEFAULT NOW(),
    fetch_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Purpose:** Cache video metadata to reduce YouTube API quota usage.

**Key Logic:**
- `is_short`: TRUE if `duration_seconds < 60` (filtered from display)
- Videos never expire (historical data is valuable)

---

### 5.4 `thumbnail_tests` - User's Test Runs
Each test represents one thumbnail preview generation.

```sql
CREATE TABLE thumbnail_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id),

    -- Input data
    persona TEXT NOT NULL,
    video_title TEXT NOT NULL,

    -- Uploaded files (local paths)
    thumbnail_path TEXT NOT NULL,           -- "static/uploads/abc.png"
    avatar_path TEXT,
    thumbnail_expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours'),

    -- Results
    status TEXT DEFAULT 'processing',       -- 'processing' | 'completed' | 'failed'
    channels_discovered TEXT[],             -- ["@MrBeast", "@Veritasium"]
    total_videos_fetched INTEGER,

    -- Metadata
    used_user_api_key BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

**Purpose:** Store each test run with its inputs and results.

**Key Logic:**
- Files auto-deleted after 24 hours (test records kept forever)
- `channels_discovered`: Array of channel handles used
- `status`: Tracks processing state

---

### 5.5 `test_videos` - Videos in Each Test
Junction table linking tests to videos.

```sql
CREATE TABLE test_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES thumbnail_tests(id),
    video_id UUID NOT NULL REFERENCES youtube_videos(id),

    position INTEGER NOT NULL,              -- Order in grid (0-indexed)
    is_user_video BOOLEAN DEFAULT FALSE,    -- TRUE for user's uploaded video

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Purpose:** Link videos to tests and preserve shuffle order.

**Key Logic:**
- `position`: Determines grid order (preserved on reload)
- `is_user_video`: Marks the user's video vs competitors

---

### 5.6 `user_api_keys` - User's Own API Keys (Future Feature)
Allows Pro users to use their own Google API keys for unlimited tests.

```sql
CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id),

    google_api_key_encrypted TEXT,
    key_verified BOOLEAN DEFAULT FALSE,
    last_verified_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Purpose:** Store user's own API keys (encrypted).

**Status:** Planned feature, not yet implemented.

---

### 5.7 Database Functions

#### `can_create_test(p_user_id UUID) → BOOLEAN`
Checks if user can create a new test.

```sql
CREATE OR REPLACE FUNCTION can_create_test(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_tier TEXT;
    v_used INTEGER;
    v_limit INTEGER;
BEGIN
    SELECT subscription_tier, tests_used_this_month, tests_limit
    INTO v_tier, v_used, v_limit
    FROM profiles
    WHERE id = p_user_id;

    IF v_tier = 'pro' THEN
        RETURN TRUE;  -- Pro users have unlimited tests
    ELSE
        RETURN v_used < v_limit;  -- Free users have monthly limit
    END IF;
END;
$$ LANGUAGE plpgsql;
```

#### `increment_test_usage(p_user_id UUID) → VOID`
Increments user's monthly test counter (atomic operation).

```sql
CREATE OR REPLACE FUNCTION increment_test_usage(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE profiles
    SET tests_used_this_month = tests_used_this_month + 1
    WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql;
```

---

## 6. Core Features & Use Cases

### 6.1 Thumbnail Testing (Core Feature)

**Use Case:** YouTuber wants to test if their thumbnail stands out against competitors.

**Actor:** Authenticated user

**Flow:**
1. User enters target viewer persona (e.g., "25yo software engineer who loves TypeScript")
2. User uploads thumbnail image (JPG/PNG, recommended 1280x720px)
3. User enters video title
4. User optionally uploads channel avatar
5. System generates preview grid
6. User sees their video mixed with 20 real competitor videos
7. User can shuffle to see different placements

**System Actions:**
1. Check user's test quota
2. Ask Gemini AI for 10 relevant channel suggestions
3. Resolve channel handles to IDs (parallel processing)
4. Fetch 2 recent videos per channel (YouTube API)
5. Cache channels and videos in database
6. Filter out YouTube Shorts (<60s)
7. Shuffle competitor videos
8. Insert user's video in top 2/3 of results
9. Save test to database
10. Increment usage counter
11. Display grid

---

### 6.2 Authentication & User Management

**Use Case:** User wants to access the platform.

**Supported Methods:**
- Google OAuth (via Supabase Auth)

**Flow:**
1. User clicks "Sign In with Google"
2. Redirects to Google OAuth consent screen
3. Google redirects back with authorization code
4. System exchanges code for session tokens
5. System creates/updates user profile in database
6. Session stored in HTTP-only cookie
7. User redirected to dashboard

**Session Management:**
- Access token stored in cookie (HTTPOnly, Secure, SameSite=Lax)
- Tokens auto-refresh using Supabase client
- Session expiry: 1 hour (configurable in Supabase)

---

### 6.3 Subscription & Payment

**Use Case:** User wants unlimited tests.

**Tiers:**
- **Free:** 5 tests/month, resets on billing cycle
- **Pro:** $10/month, unlimited tests

**Flow:**
1. User clicks "Upgrade to Pro"
2. System creates Stripe checkout session
3. User redirected to Stripe-hosted checkout
4. User completes payment
5. Stripe sends webhook to system
6. System updates user profile (subscription_tier = 'pro')
7. User redirected to dashboard

**Webhook Events Handled:**
- `checkout.session.completed`: New subscription
- `customer.subscription.updated`: Subscription changes
- `customer.subscription.deleted`: Cancellation

**Subscription Management:**
- Users can manage subscription via Stripe Customer Portal
- Actions: Update payment method, view invoices, cancel subscription

---

### 6.4 Dashboard

**Use Case:** User wants to see their test history and usage.

**Features:**
- Display subscription tier and usage stats
- Show 10 most recent tests
- Quick actions (New Test, Upgrade, Settings)
- Click test to view/re-shuffle

**Data Shown:**
- Tests used this month / limit
- Recent tests with persona, timestamp, video count
- Subscription status

---

### 6.5 Shuffle Feature

**Use Case:** User wants to see their thumbnail in different positions.

**Flow:**
1. User clicks "Shuffle Results" on a test
2. System retrieves videos from database OR memory
3. Separates user video from competitor videos
4. Re-shuffles competitor videos
5. Re-inserts user video in new random position (top 2/3)
6. Returns updated grid HTML (HTMX swap)

**Technical Details:**
- In-memory sessions for new tests (fast)
- Database fallback for historical tests
- No API calls needed (data already cached)

---

## 7. User Flow Diagrams

### 7.1 End-to-End Test Generation Flow

```
┌─────────────┐
│   Landing   │
│    Page     │
└──────┬──────┘
       │
       │ (Not signed in)
       ↓
┌─────────────┐
│  Sign In    │
│   (Google)  │
└──────┬──────┘
       │
       │ (OAuth redirect)
       ↓
┌─────────────┐
│  Dashboard  │
└──────┬──────┘
       │
       │ (Click "New Test")
       ↓
┌─────────────────────────────┐
│   Input Form (Landing)      │
│  • Persona                  │
│  • Thumbnail Upload         │
│  • Video Title              │
│  • Avatar (optional)        │
└──────┬──────────────────────┘
       │
       │ (Submit)
       ↓
┌─────────────────────────────┐
│   Backend Processing        │
│  1. Check quota             │
│  2. AI channel discovery    │
│  3. Resolve channel IDs     │
│  4. Fetch YouTube videos    │
│  5. Save to database        │
│  6. Log to CSV              │
│  7. Shuffle & inject        │
└──────┬──────────────────────┘
       │
       │ (Redirect to /preview/{test_id})
       ↓
┌─────────────────────────────┐
│   Preview Grid              │
│  • 3x3 video grid           │
│  • User video highlighted   │
│  • Shuffle button           │
│  • Edit title               │
└─────────────────────────────┘
```

### 7.2 Payment Flow

```
┌─────────────┐
│  Dashboard  │
│ (Free tier) │
└──────┬──────┘
       │
       │ (Hit limit OR click "Upgrade")
       ↓
┌─────────────┐
│   Upgrade   │
│    Page     │
└──────┬──────┘
       │
       │ (Click "Subscribe")
       ↓
┌─────────────────┐
│ Stripe Checkout │
│   (External)    │
└──────┬──────────┘
       │
       │ (Payment success)
       ↓
┌─────────────────┐
│ Stripe Webhook  │
│  to /webhook    │
└──────┬──────────┘
       │
       │ (Update database)
       ↓
┌─────────────────┐
│   Dashboard     │
│  (Pro tier)     │
└─────────────────┘
```

---

## 8. API Endpoints

### 8.1 Public Routes (No Auth Required)

#### `GET /`
**Purpose:** Landing page with test form

**Template:** `index.html`

**Behavior:**
- If authenticated: Show user info, load most recent test
- If not: Show sign-in prompt

---

#### `GET /health`
**Purpose:** Health check for monitoring

**Response:**
```json
{
    "status": "healthy",
    "app": "YouTube Context Engine",
    "version": "1.0.0"
}
```

---

### 8.2 Authentication Routes

#### `GET /auth/login`
**Purpose:** Initiate Google OAuth login

**Flow:**
1. Generate Google OAuth URL
2. Redirect to Google consent screen

---

#### `GET /auth/callback`
**Purpose:** OAuth callback handler

**Query Params:**
- `code`: Authorization code from Google

**Flow:**
1. Exchange code for session tokens
2. Store tokens in HTTP-only cookie
3. Create/update user profile
4. Redirect to `/dashboard` (or `?next=` param)

---

#### `GET /auth/logout`
**Purpose:** Sign out user

**Flow:**
1. Clear session cookie
2. Redirect to landing page

---

### 8.3 Thumbnail Testing Routes

#### `POST /generate`
**Purpose:** Generate thumbnail preview (core feature)

**Auth:** Optional (shows sign-in message if not authenticated)

**Form Data:**
- `persona` (string, required): Target viewer description
- `title` (string, required): Video title
- `thumbnail` (file, required): Thumbnail image
- `avatar` (file, optional): Channel avatar

**Response:** Redirect to `/preview/{test_id}`

**Side Effects:**
- Saves test to database
- Increments usage counter
- Logs videos to CSV

---

#### `GET /preview/{test_id}`
**Purpose:** View a specific test

**Auth:** Required (must be test owner)

**Response:** HTML page with video grid

---

#### `POST /shuffle`
**Purpose:** Re-shuffle test results

**Auth:** Optional (but test must exist)

**Form Data:**
- `session_id` (string): Test ID or session ID

**Response:** HTML fragment (video grid) for HTMX swap

---

#### `PATCH /test/{test_id}/title`
**Purpose:** Update video title for a test

**Auth:** Required (must be test owner)

**Form Data:**
- `title` (string): New title

**Response:**
```json
{
    "success": true,
    "title": "New Title"
}
```

---

### 8.4 Dashboard Routes

#### `GET /dashboard`
**Purpose:** User dashboard

**Auth:** Required

**Template:** `dashboard.html`

**Data:**
- User profile
- Subscription info
- Usage stats
- Recent tests (10 most recent)

---

#### `GET /test/{test_id}`
**Purpose:** Redirects to `/preview/{test_id}`

**Auth:** Required

---

### 8.5 Payment Routes

#### `GET /api/payment/upgrade`
**Purpose:** Upgrade/pricing page

**Auth:** Required

**Template:** `upgrade.html`

---

#### `POST /api/payment/create-checkout`
**Purpose:** Create Stripe checkout session

**Auth:** Required

**Response:** Redirect to Stripe checkout

---

#### `POST /api/payment/webhook`
**Purpose:** Stripe webhook handler

**Auth:** None (verified via Stripe signature)

**Headers:**
- `stripe-signature`: Webhook signature

**Events Handled:**
- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

---

#### `GET /api/payment/portal`
**Purpose:** Redirect to Stripe customer portal

**Auth:** Required

**Response:** Redirect to Stripe portal

---

### 8.6 User Routes

#### `GET /api/user/profile`
**Purpose:** Get user profile

**Auth:** Required

**Response:**
```json
{
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "subscription_tier": "pro",
    "tests_used_this_month": 15
}
```

---

## 9. Services Layer

### 9.1 AIService (`app/services/ai_service.py`)

**Purpose:** Interact with Google Gemini AI for channel suggestions.

#### Method: `get_channel_suggestions(persona: str, num_channels: int) → List[str]`

**Input:**
- `persona`: Target viewer description
- `num_channels`: Number of channels to return (default: 10)

**Output:**
- List of channel handles (e.g., `["@MrBeast", "@Veritasium"]`)

**Algorithm:**
1. Construct prompt asking for `num_channels` relevant YouTube channels
2. Send to Gemini API
3. Parse response (JSON array or regex extraction)
4. Clean handles (ensure '@' prefix)
5. Return list (or fallback if AI fails)

**Fallback Channels:**
```python
["@MrBeast", "@Veritasium", "@ThePrimeagen", "@mkbhd",
 "@LinusTechTips", "@3Blue1Brown", "@vsauce", "@CGPGrey",
 "@TomScottGo", "@Fireship"]
```

**Error Handling:** Returns fallback channels if API fails.

---

### 9.2 YouTubeService (`app/services/youtube_service.py`)

**Purpose:** Fetch video data from YouTube Data API v3.

#### Method: `get_videos_for_channels(channel_data: List[Dict], videos_per_channel: int) → List[VideoData]`

**Input:**
- `channel_data`: List of `{"channel_id": "UC...", "handle": "@..."}`
- `videos_per_channel`: Number of videos per channel (default: 2)

**Output:**
- List of `VideoData` objects

**Algorithm:**
1. For each channel, call YouTube API: `search` endpoint
2. Get most recent `videos_per_channel` video IDs
3. Call `videos` endpoint to get metadata (duration, views, etc.)
4. Parse response into `VideoData` objects
5. Return combined list

**API Quota Usage:**
- `search`: 100 units per call
- `videos`: 1 unit per call
- Total: ~10 channels × 100 = 1000 units per test

---

### 9.3 AuthService (`app/services/auth_service.py`)

**Purpose:** Handle user authentication with Supabase.

#### Key Methods:

1. `get_google_oauth_url(redirect_to: str) → str`
   - Generates Google OAuth URL

2. `exchange_code_for_session(code: str) → Dict`
   - Exchanges OAuth code for session tokens

3. `can_create_test(user_id: str) → bool`
   - Checks if user can create a new test (quota check)

4. `increment_test_usage(user_id: str) → bool`
   - Increments monthly test counter

5. `get_or_create_profile(user_id: str) → Dict`
   - Gets existing profile or creates new one

---

### 9.4 StripeService (`app/services/stripe_service.py`)

**Purpose:** Handle Stripe payment processing.

#### Key Methods:

1. `create_checkout_session(user_id, user_email, price_id, success_url, cancel_url) → Dict`
   - Creates Stripe checkout session
   - Returns `{"checkout_url": "https://checkout.stripe.com/..."}`

2. `handle_webhook_event(payload: bytes, signature: str) → Dict`
   - Verifies webhook signature
   - Processes event (subscription created/updated/deleted)
   - Updates user profile in database

3. `create_customer_portal_session(user_id: str, return_url: str) → str`
   - Creates Stripe customer portal link

**Webhook Event Handlers:**
- `checkout.session.completed`: Upgrade user to 'pro'
- `customer.subscription.updated`: Update subscription status
- `customer.subscription.deleted`: Downgrade user to 'free'

---

### 9.5 DataService (`app/services/data_service.py`)

**Purpose:** Log video data to CSV for analytics.

#### Method: `log_videos_to_csv(videos: List[VideoData], persona: str, channel_handles: Dict) → int`

**Input:**
- `videos`: List of fetched videos
- `persona`: Target viewer persona
- `channel_handles`: Mapping of channel_id → handle

**Output:**
- Number of videos logged

**CSV Columns:**
```
timestamp, persona, channel_handle, channel_id, video_id,
title, views, published_at, thumbnail_url, duration_seconds
```

**Purpose:** Long-term data collection for future analytics features.

---

### 9.6 CleanupService (`app/services/cleanup_service.py`)

**Purpose:** Delete expired thumbnail files (24h after upload).

**Status:** Background job (not yet automated, needs cron/scheduler).

**Algorithm:**
1. Query `thumbnail_tests` where `thumbnail_expires_at < NOW()`
2. Delete thumbnail and avatar files from filesystem
3. Update database records (or keep as-is)

---

## 10. Authentication & Authorization

### 10.1 Authentication Flow

**Provider:** Google OAuth 2.0 (via Supabase Auth)

**Flow:**
1. User clicks "Sign In with Google"
2. Redirects to Google OAuth consent screen
3. User grants permission
4. Google redirects to `/auth/callback?code=...`
5. Backend exchanges code for session (access + refresh tokens)
6. Tokens stored in HTTP-only cookie
7. User redirected to dashboard

### 10.2 Session Management

**Storage:** HTTP-only cookies

**Cookie Name:** `sb-auth-token` (Supabase default)

**Cookie Attributes:**
- `HttpOnly`: Prevents JavaScript access
- `Secure`: HTTPS only (production)
- `SameSite=Lax`: CSRF protection

**Token Expiry:**
- Access token: 1 hour
- Refresh token: Auto-refreshed by Supabase client

### 10.3 Authorization Middleware

**Location:** `app/middleware/auth.py`

#### `require_auth()` Dependency
- Decorator for protected routes
- Checks for valid session token
- Returns `user_id` if authenticated
- Raises 401 if not

#### `optional_auth()` Dependency
- Returns `user_id` if authenticated, else `None`
- Doesn't block unauthenticated requests

**Usage:**
```python
@router.get("/dashboard")
async def dashboard(request: Request, user_id: str = Depends(require_auth())):
    # user_id is guaranteed to exist
    ...
```

### 10.4 Row-Level Security (RLS)

**Enabled on Supabase tables:**
- Users can only access their own data
- Policies enforce `user_id = auth.uid()`

**Example Policy:**
```sql
CREATE POLICY "Users can view own tests"
ON thumbnail_tests
FOR SELECT
USING (auth.uid() = user_id);
```

---

## 11. Payment & Billing System

### 11.1 Subscription Tiers

| Tier | Price | Tests/Month | Features |
|------|-------|-------------|----------|
| Free | $0 | 5 | Basic thumbnail testing |
| Pro | $10/month | Unlimited | All features, priority support |

### 11.2 Usage Limits

**Free Tier:**
- 5 tests per month
- Counter resets on `billing_cycle_start` (monthly)
- Enforced by `can_create_test()` function

**Pro Tier:**
- Unlimited tests
- No quota checks

### 11.3 Stripe Integration

**Products:**
- Product: "Pro Plan"
- Price: $10/month (recurring)
- Price ID: Stored in `settings.stripe_price_id_pro`

**Customer Lifecycle:**
1. User upgrades → Create Stripe checkout session
2. User completes payment → Stripe sends webhook
3. Webhook updates database (`subscription_tier = 'pro'`)
4. User can manage subscription via Stripe Customer Portal

**Webhooks:**
- `checkout.session.completed`: New subscription
- `customer.subscription.updated`: Plan change
- `customer.subscription.deleted`: Cancellation

**Webhook Security:**
- Signature verification using `stripe_webhook_secret`
- Prevents replay attacks

---

## 12. Configuration & Environment

### 12.1 Environment Variables (.env)

```bash
# App Info
DEBUG=True

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=eyJxxx...
SUPABASE_SECRET_KEY=eyJxxx...

# Google API Keys
GOOGLE_API_KEY=AIzaSyxxx...
GEMINI_API_KEY=AIzaSyxxx...  # Optional if using same key

# Google OAuth
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPxxx...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Stripe
STRIPE_SECRET_KEY=sk_test_xxx...
STRIPE_PUBLISHABLE_KEY=pk_test_xxx...
STRIPE_PRICE_ID_PRO=price_xxx...
STRIPE_WEBHOOK_SECRET=whsec_xxx...  # Optional for local dev

# Gemini Model
GEMINI_MODEL=gemini-2.0-flash-exp

# Processing Settings
MAX_CHANNELS=10
VIDEOS_PER_CHANNEL=2
MAX_WORKERS=10
SHORTS_DURATION_THRESHOLD=60

# Server
HOST=127.0.0.1
PORT=8000
```

### 12.2 Settings Management

**Location:** `app/config.py`

**Pattern:** Pydantic Settings (type-safe, auto-validated)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "YouTube Context Engine"
    debug: bool = True
    supabase_url: str
    # ... all other settings

    class Config:
        env_file = ".env"
```

**Usage:**
```python
from app.config import get_settings

settings = get_settings()  # Cached singleton
print(settings.google_api_key)
```

---

## 13. Data Flow & Processing Pipeline

### 13.1 Complete Test Generation Flow

```
USER INPUT
  ↓
1. Persona → Gemini AI → Channel Handles
   Example: "25yo dev" → ["@ThePrimeagen", "@Fireship", ...]
  ↓
2. Channel Handles → Web Scraping → Channel IDs
   Example: "@ThePrimeagen" → "UCEBb1b_L6zDS3xTUrIALZOw"
   (Parallel processing using ThreadPoolExecutor)
  ↓
3. Channel IDs → YouTube API → Video Metadata
   Example: "UC..." → [{video_id, title, views, ...}, ...]
   (2 videos per channel × 10 channels = 20 videos)
  ↓
4. Videos → Database Cache (youtube_videos, youtube_channels)
   (Upsert to avoid duplicates)
  ↓
5. Videos → CSV Logger (data/competitor_data.csv)
   (All videos including Shorts)
  ↓
6. Videos → Filter Shorts (<60s)
   (For display only, kept in database)
  ↓
7. Competitor Videos → Shuffle
  ↓
8. User Video → Inject at Random Position (top 2/3)
  ↓
9. Combined List → Database (test_videos with position)
  ↓
10. Render HTML Grid → Return to User
```

### 13.2 Channel Resolution Algorithm

**Problem:** YouTube handles (@username) are not IDs (UC...). We need IDs for API calls.

**Solution:** HTML scraping (YouTube Data API doesn't support handle→ID conversion).

**Function:** `get_channel_id_from_html(channel_input: str)`

**Location:** `app/utils/channel_resolver.py`

**Algorithm:**
```python
def get_channel_id_from_html(channel_input):
    # 1. Clean input (ensure @ prefix)
    clean_input = f"@{channel_input}" if not channel_input.startswith("@") else channel_input

    # 2. Fetch channel page HTML
    url = f"https://www.youtube.com/{clean_input}"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})

    # 3. Extract channel ID using regex
    # Strategy A: Look for /channel/UC... pattern
    match = re.search(r'youtube\.com/channel/(UC[\w-]{22})', response.text)
    if match:
        return match.group(1)

    # Strategy B: Look for "externalId":"UC..." in JSON blob
    match = re.search(r'"externalId":"(UC[\w-]{22})"', response.text)
    if match:
        return match.group(1)

    return None  # Failed to resolve
```

**Optimization:** Parallel resolution using `ThreadPoolExecutor` (10 channels in ~2-3 seconds instead of 10+ seconds sequentially).

---

### 13.3 Video Shuffling Logic

**Goal:** Randomize competitor videos, inject user video in "natural" position.

**Algorithm:**
```python
def shuffle_and_inject(competitor_videos, user_video):
    # 1. Shuffle competitor videos
    random.shuffle(competitor_videos)

    # 2. Calculate injection position (top 2/3)
    total_videos = len(competitor_videos) + 1
    top_two_thirds = int(total_videos * 2 / 3)
    user_position = random.randint(0, max(0, top_two_thirds - 1))

    # 3. Insert user video
    final_list = (
        competitor_videos[:user_position] +
        [user_video] +
        competitor_videos[user_position:]
    )

    return final_list
```

**Why Top 2/3?**
- Simulates realistic YouTube algorithm behavior
- Avoids always placing user video at top (unrealistic)
- Avoids bottom (where users might not scroll)

---

## 14. Error Handling & Edge Cases

### 14.1 API Failures

#### Google Gemini AI Failure
- **Fallback:** Use pre-defined list of popular channels
- **Log:** Warning message
- **User Impact:** None (transparent fallback)

#### YouTube API Quota Exceeded
- **Error:** `quotaExceeded` from YouTube API
- **Response:** Show user error message: "API quota exceeded. Try again in 24 hours or upgrade to Pro."
- **Mitigation:** Database caching reduces API calls

#### Channel Resolution Failure
- **Scenario:** Some channels don't resolve (private, deleted, etc.)
- **Handling:** Continue with successfully resolved channels
- **Minimum:** Require at least 1 successful channel resolution

### 14.2 File Upload Issues

#### Invalid File Type
- **Validation:** Only allow `.jpg`, `.jpeg`, `.png`
- **Error:** "Invalid file type. Please upload JPG or PNG."

#### File Too Large
- **Limit:** 5MB per file (configurable)
- **Error:** "File too large. Maximum size: 5MB."

#### Disk Space Full
- **Handling:** Return 500 error, log to monitoring
- **Prevention:** Automated cleanup of old files

### 14.3 Payment Failures

#### Stripe Checkout Abandoned
- **Scenario:** User starts checkout but doesn't complete
- **Handling:** No change to account (user can retry)

#### Payment Declined
- **Scenario:** Card declined, insufficient funds, etc.
- **Handling:** Stripe shows error, user can update payment method

#### Webhook Delivery Failure
- **Scenario:** Webhook endpoint down or times out
- **Handling:** Stripe retries automatically
- **Backup:** Manual reconciliation via Stripe dashboard

### 14.4 Database Issues

#### Duplicate Key Violation
- **Scenario:** Video already exists in cache
- **Handling:** Upsert (update if exists)

#### Connection Timeout
- **Handling:** Retry with exponential backoff
- **User Impact:** Show loading state, retry

#### Row-Level Security Denial
- **Scenario:** User tries to access another user's data
- **Handling:** 403 Forbidden error

---

## 15. Performance Optimizations

### 15.1 Parallel Processing

**Channel Resolution:**
- Uses `ThreadPoolExecutor` with 10 workers
- Resolves 10 channels in ~2-3 seconds (vs 10+ seconds sequentially)

**Location:** `app/utils/channel_resolver.py::resolve_channels_parallel()`

### 15.2 Database Caching

**Purpose:** Reduce YouTube API quota usage

**Strategy:**
- Cache channels forever (rarely change)
- Cache videos forever (historical data is valuable)
- Upsert pattern (insert if new, update if exists)

**Impact:**
- First test for a channel: 100 API quota units
- Subsequent tests: 0 units (cached data)

### 15.3 In-Memory Sessions

**Purpose:** Fast shuffle without database queries

**Implementation:**
```python
sessions = {}  # In-memory dictionary

# On test generation:
sessions[session_id] = {
    'videos': all_display_videos,
    'created_at': datetime.now()
}

# On shuffle:
if session_id in sessions:
    videos = sessions[session_id]['videos']
    # ... shuffle logic
```

**Limitation:** Sessions lost on server restart (fallback to database).

### 15.4 Future Optimizations

- **Redis Cache:** Replace in-memory sessions with Redis (persistent, shared across instances)
- **CDN:** Serve thumbnails from CloudFront/Cloudflare
- **Image Compression:** Auto-resize/compress uploaded thumbnails
- **Database Indexing:** Add indexes on frequently queried columns

---

## 16. Security Measures

### 16.1 Authentication Security

- ✅ HTTP-only cookies (no JavaScript access)
- ✅ HTTPS-only cookies in production
- ✅ SameSite=Lax (CSRF protection)
- ✅ OAuth state parameter validation
- ✅ Token-based session management
- ✅ Automatic token refresh

### 16.2 Authorization Security

- ✅ Row-Level Security (RLS) in Supabase
- ✅ User can only access own data
- ✅ `require_auth()` middleware on protected routes
- ✅ Test ownership verification before actions

### 16.3 Payment Security

- ✅ Webhook signature verification
- ✅ No card data stored (Stripe handles)
- ✅ Secure API keys (environment variables)
- ⚠️ Webhook endpoint needs rate limiting (future)

### 16.4 File Upload Security

- ✅ File type validation (MIME type check)
- ✅ File size limits (5MB)
- ✅ Random filenames (UUID) to prevent overwriting
- ⚠️ Image content validation needed (prevent malware)
- ⚠️ Virus scanning (future)

### 16.5 API Security

- ⚠️ Rate limiting (not implemented yet)
- ⚠️ CORS configured but needs refinement
- ⚠️ Input sanitization (basic via Pydantic, needs enhancement)
- ✅ API keys stored in environment variables
- ✅ No API keys exposed to frontend

### 16.6 Future Security Enhancements

1. **Rate Limiting:** Implement per-user rate limits (100 requests/hour)
2. **CSRF Tokens:** Add CSRF protection for form submissions
3. **Content Security Policy:** Add CSP headers
4. **Input Sanitization:** Enhanced validation for all user inputs
5. **API Key Encryption:** Encrypt API keys at rest in database
6. **Audit Logging:** Log all sensitive actions (login, payment, etc.)

---

## 17. Testing Strategy (Planned)

### 17.1 Unit Tests

**Coverage:**
- Services (AIService, YouTubeService, etc.)
- Utilities (channel_resolver, helpers)
- Data models (Pydantic schemas)

**Framework:** pytest

**Example:**
```python
def test_ai_service_parses_json_response():
    service = AIService()
    text = '["@MrBeast", "@Veritasium"]'
    channels = service._parse_channel_response(text, 10)
    assert len(channels) == 2
    assert channels[0] == "@MrBeast"
```

### 17.2 Integration Tests

**Coverage:**
- API endpoints (FastAPI TestClient)
- Database operations (Supabase interactions)
- Payment flows (Stripe test mode)

**Example:**
```python
def test_generate_preview_requires_auth(client):
    response = client.post("/generate", data={...})
    assert response.status_code == 401
```

### 17.3 End-to-End Tests

**Coverage:**
- Full user flows (sign up → test → upgrade → test again)
- Payment flows (checkout → webhook → account upgrade)

**Framework:** Playwright or Selenium

---

## 18. Deployment Guide

### 18.1 Environment Setup

**Platform:** Render.com

**Services:**
- Web Service: FastAPI app (Docker or native Python)
- PostgreSQL: Supabase (external)

**Configuration:** `render.yaml`

```yaml
services:
  - type: web
    name: youtube-intelligence-platform
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
      - key: DEBUG
        value: false
      # ... other env vars from Render dashboard
```

### 18.2 Environment Variables (Production)

**Set in Render Dashboard:**
- All API keys (Google, Gemini, Stripe)
- Supabase credentials
- `DEBUG=false`
- `HOST=0.0.0.0` (Render requirement)
- `PORT=8000` (or use Render's `$PORT`)

### 18.3 Pre-Deployment Checklist

- [ ] All environment variables set
- [ ] Database migrations run
- [ ] Stripe webhooks configured (point to production URL)
- [ ] Google OAuth redirect URI updated (production domain)
- [ ] CORS allowed origins updated (production domain)
- [ ] Static files served correctly
- [ ] Health check endpoint working
- [ ] Supabase RLS policies enabled

### 18.4 Deployment Steps

1. **Push to Git:** `git push origin main`
2. **Render Auto-Deploy:** Detects commit, builds, and deploys
3. **Health Check:** Visit `https://your-app.onrender.com/health`
4. **Test OAuth:** Sign in with Google
5. **Test Payment:** Upgrade to Pro (Stripe test mode first)
6. **Monitor Logs:** Check for errors in Render dashboard

---

## 19. Monitoring & Analytics (Planned)

### 19.1 Application Monitoring

**Tools (Recommended):**
- **Error Tracking:** Sentry
- **Performance:** Datadog or New Relic
- **Uptime:** UptimeRobot

**Metrics to Track:**
- Request latency (p50, p95, p99)
- Error rate (5xx responses)
- API quota usage (YouTube, Gemini)
- Database query performance

### 19.2 User Analytics

**Tools (Recommended):**
- **Product Analytics:** PostHog or Mixpanel
- **Web Analytics:** Google Analytics

**Events to Track:**
- User sign up
- Test created
- Shuffle clicked
- Upgrade initiated
- Payment completed
- Test shared (future feature)

### 19.3 Business Metrics

**KPIs:**
- Monthly Recurring Revenue (MRR)
- Free → Pro conversion rate
- Average tests per user
- Churn rate
- API cost per test

---

## 20. Future Roadmap (from ROADMAP.md)

### 20.1 High Priority (MVP Launch)

- [ ] **Export Functionality:** PDF/CSV export of test results
- [ ] **Share Test Results:** Generate public shareable links
- [ ] **Advanced Analytics:** CTR simulation, thumbnail scoring
- [ ] **Legal Pages:** Terms of Service, Privacy Policy
- [ ] **Email System:** Welcome emails, payment confirmations
- [ ] **Mobile Responsiveness:** Full testing and optimization
- [ ] **Security Hardening:** Rate limiting, CSRF protection

### 20.2 Medium Priority (Pro Features)

- [ ] **AI Thumbnail Analysis:** Critique thumbnails (readability, colors, etc.)
- [ ] **A/B Testing:** Compare multiple thumbnails side-by-side
- [ ] **Profile Settings:** Edit name, avatar, email preferences
- [ ] **Test Management:** Delete, search, filter tests
- [ ] **Dashboard Analytics:** Charts showing usage trends

### 20.3 Nice-to-Have (Growth Features)

- [ ] **Onboarding Flow:** Tutorial for new users
- [ ] **Competitor Tracking:** Save favorite competitors, auto-fetch updates
- [ ] **Historical Tracking:** Track same video over time
- [ ] **Team Accounts:** Multiple users per subscription
- [ ] **API Access:** Public API for integrations

---

## 21. Frequently Asked Questions (FAQ)

### For Developers

**Q: How do I add a new feature?**
A: Follow the service-oriented architecture:
1. Add route in `app/routes/`
2. Add business logic in `app/services/`
3. Add data models in `app/models/`
4. Add template in `templates/` (if UI needed)

**Q: How do I test locally?**
A:
1. Copy `.env.example` to `.env`
2. Fill in API keys
3. Run `python -m app.main`
4. Visit `http://localhost:8000`

**Q: How do I access the database?**
A: Supabase provides:
- SQL Editor (web UI)
- REST API (auto-generated)
- Python client (`supabase_client`)

**Q: How do I debug webhook issues?**
A: Use Stripe CLI for local testing:
```bash
stripe listen --forward-to localhost:8000/api/payment/webhook
```

### For Product Managers

**Q: What's the difference between Free and Pro?**
A:
- Free: 5 tests/month, resets monthly
- Pro: Unlimited tests, $10/month

**Q: How much do API calls cost?**
A:
- YouTube API: Free (10,000 quota/day)
- Gemini API: Free tier (generous)
- Cost becomes issue at scale (future: let Pro users use own keys)

**Q: Can users share test results?**
A: Not yet, but planned feature.

**Q: How long are thumbnails stored?**
A: 24 hours, then auto-deleted (test records kept forever).

---

## 22. Glossary

| Term | Definition |
|------|------------|
| **Persona** | Description of target viewer (e.g., "25yo software engineer") |
| **Channel Handle** | YouTube's @ username (e.g., @MrBeast) |
| **Channel ID** | YouTube's internal ID (e.g., UC...) |
| **Test** | One thumbnail preview generation |
| **Shorts** | YouTube short-form videos (<60 seconds) |
| **Shuffle** | Re-randomize video order in grid |
| **RLS** | Row-Level Security (database access control) |
| **OAuth** | Open Authorization (login via Google) |
| **Webhook** | Server-to-server event notification (Stripe → Our App) |
| **Quota** | API usage limit (YouTube: 10,000/day, Gemini: varies) |

---

## 23. Contact & Support

**GitHub Repository:** (Add link)

**Issues:** Report bugs via GitHub Issues

**Documentation:** See README.md for setup instructions

**Support Email:** (Add email)

---

## Appendix A: Database Schema (Full SQL)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Profiles (extends auth.users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    avatar_url TEXT,
    subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro')),
    tests_used_this_month INTEGER DEFAULT 0,
    tests_limit INTEGER DEFAULT 5,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    billing_cycle_start TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. YouTube Channels
CREATE TABLE youtube_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id TEXT UNIQUE NOT NULL,
    channel_handle TEXT,
    channel_name TEXT,
    channel_avatar_url TEXT,
    subscriber_count BIGINT,
    last_fetched_at TIMESTAMPTZ DEFAULT NOW(),
    fetch_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. YouTube Videos
CREATE TABLE youtube_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id TEXT UNIQUE NOT NULL,
    channel_id TEXT NOT NULL,
    title TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,
    view_count BIGINT,
    published_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    is_short BOOLEAN DEFAULT FALSE,
    last_fetched_at TIMESTAMPTZ DEFAULT NOW(),
    fetch_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Thumbnail Tests
CREATE TABLE thumbnail_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    persona TEXT NOT NULL,
    video_title TEXT NOT NULL,
    thumbnail_path TEXT NOT NULL,
    avatar_path TEXT,
    thumbnail_expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours'),
    status TEXT DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    channels_discovered TEXT[],
    total_videos_fetched INTEGER,
    used_user_api_key BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 5. Test Videos
CREATE TABLE test_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES thumbnail_tests(id) ON DELETE CASCADE,
    video_id UUID NOT NULL REFERENCES youtube_videos(id),
    position INTEGER NOT NULL,
    is_user_video BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. User API Keys (future feature)
CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    google_api_key_encrypted TEXT,
    key_verified BOOLEAN DEFAULT FALSE,
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_youtube_videos_channel_id ON youtube_videos(channel_id);
CREATE INDEX idx_thumbnail_tests_user_id ON thumbnail_tests(user_id);
CREATE INDEX idx_test_videos_test_id ON test_videos(test_id);

-- Functions
CREATE OR REPLACE FUNCTION can_create_test(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_tier TEXT;
    v_used INTEGER;
    v_limit INTEGER;
BEGIN
    SELECT subscription_tier, tests_used_this_month, tests_limit
    INTO v_tier, v_used, v_limit
    FROM profiles
    WHERE id = p_user_id;

    IF v_tier = 'pro' THEN
        RETURN TRUE;
    ELSE
        RETURN v_used < v_limit;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION increment_test_usage(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE profiles
    SET tests_used_this_month = tests_used_this_month + 1
    WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql;
```

---

## Appendix B: API Response Examples

### Example: Video Data
```json
{
    "video_id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "channel_name": "Rick Astley",
    "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
    "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "view_count": 1234567890,
    "published_at": "2009-10-25T06:57:33Z",
    "duration_seconds": 212,
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "is_user_video": false,
    "duration": "3:32",
    "view_text": "1.2B views",
    "time_ago": "14 years ago"
}
```

### Example: Test Response
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "persona": "25yo software engineer who loves TypeScript",
    "video_title": "My Awesome TypeScript Tutorial",
    "thumbnail_path": "static/uploads/abc123.png",
    "status": "completed",
    "channels_discovered": ["@ThePrimeagen", "@Fireship", "@BenAwad"],
    "total_videos_fetched": 20,
    "created_at": "2024-12-13T10:30:00Z",
    "completed_at": "2024-12-13T10:30:15Z"
}
```

---

**End of Specification**

This document is a living specification. As the application evolves, this spec should be updated to reflect the current state of the system.

**Last Updated:** December 13, 2024
