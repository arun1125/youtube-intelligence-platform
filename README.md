# YouTube Context Engine

A FastAPI-based web application that helps YouTubers test their thumbnails against specific competitors by simulating a YouTube homepage with real videos from channels that their target persona watches.

## Features

- 🤖 **AI-Powered Channel Discovery**: Uses Google Gemini to find 10 relevant channels based on target viewer persona
- ⚡ **Parallel Processing**: Resolves channel IDs concurrently for faster execution
- 📊 **Real YouTube Data**: Fetches actual recent videos from discovered channels via YouTube Data API
- 💾 **Complete Data Logging**: Saves all fetched videos to CSV for analysis
- 🎨 **YouTube Dark Mode UI**: Pixel-perfect recreation of YouTube's interface
- 🔀 **Shuffle Feature**: Re-randomize video order without re-fetching data
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile

## Tech Stack

- **Backend**: FastAPI (async, high-performance Python web framework)
- **Frontend**: Jinja2 templates + Tailwind CSS + HTMX
- **AI**: Google Gemini API
- **Data**: YouTube Data API v3
- **Storage**: CSV (easily upgradeable to PostgreSQL)

## Project Structure

```
/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and settings
│   ├── routes/
│   │   └── thumbnail.py     # API routes
│   ├── services/
│   │   ├── ai_service.py    # Gemini AI integration
│   │   ├── youtube_service.py  # YouTube API integration
│   │   └── data_service.py  # CSV data operations
│   ├── models/
│   │   └── schemas.py       # Pydantic data models
│   └── utils/
│       ├── channel_resolver.py  # Channel ID resolution
│       └── helpers.py       # Utility functions
├── templates/
│   ├── base.html            # Base template
│   ├── index.html           # Main page
│   └── components/
│       └── video_grid.html  # Video grid component
├── static/
│   └── uploads/             # User-uploaded files
├── data/
│   └── competitor_data.csv  # Video data log
├── old_code/                # Original scripts (archived)
├── requirements.txt
├── .env.example
└── README.md
```

## Setup Instructions

### 1. Clone and Navigate

```bash
cd /path/to/youtube-competitive-intelligence
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

**Getting API Keys:**
- **Google API Key**:
  1. Go to [Google Cloud Console](https://console.cloud.google.com/)
  2. Create a new project (or select existing)
  3. Enable YouTube Data API v3
  4. Enable Generative Language API (Gemini)
  5. Create credentials (API Key)
  6. Copy the key to your `.env` file

### 5. Run the Application

```bash
python -m app.main
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 6. Access the Application

Open your browser and navigate to:

```
http://localhost:8000
```

## Usage

1. **Enter Target Persona**: Describe your ideal viewer in detail
   - Example: "25yo Junior Developer who loves TypeScript and watches tech content during lunch breaks"

2. **Upload Thumbnail**: Your video thumbnail (recommended: 1280x720px)

3. **Enter Video Title**: The title of your video

4. **Upload Avatar** (Optional): Your channel's avatar image

5. **Generate Preview**: Click to see your video in context

6. **Shuffle**: Re-randomize the order to see different placements

## API Endpoints

- `GET /` - Main page with input form
- `POST /generate` - Generate thumbnail preview
- `POST /shuffle` - Shuffle existing results
- `GET /health` - Health check endpoint

## Data Storage

All fetched videos are logged to `data/competitor_data.csv` with the following columns:

- timestamp
- persona
- channel_handle
- channel_id
- video_id
- title
- views
- published_at
- thumbnail_url
- duration_seconds

## Architecture Highlights

### Service Layer Pattern
- Clean separation between routes, business logic, and data access
- Easy to test and swap implementations

### Type Safety
- Pydantic models for request/response validation
- Type hints throughout the codebase

### Extensibility
Ready for monetization features:
- Add authentication (JWT)
- Migrate to PostgreSQL
- Add billing (Stripe)
- Rate limiting
- Docker deployment

## Development

### Adding New Features

The modular architecture makes it easy to extend:

1. **New API endpoints**: Add to `app/routes/`
2. **Business logic**: Add to `app/services/`
3. **Data models**: Add to `app/models/schemas.py`
4. **Utilities**: Add to `app/utils/`

### Environment Variables

All configuration is managed via `app/config.py` using Pydantic Settings. Add new settings there and update `.env.example`.

## Troubleshooting

### "API Key not found"
- Ensure `.env` file exists in project root
- Check that `GOOGLE_API_KEY` is set correctly

### "Failed to resolve channel IDs"
- Some channels may be private or deleted
- The app uses fallback channels if AI fails

### "YouTube API quota exceeded"
- YouTube Data API has daily quotas
- Check your quota usage in Google Cloud Console

## License

MIT

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Google Gemini API](https://ai.google.dev/)
- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [Tailwind CSS](https://tailwindcss.com/)
- [HTMX](https://htmx.org/)
