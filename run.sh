#!/bin/bash

# YouTube Context Engine - Run Script

echo "🚀 Starting YouTube Context Engine..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python -m venv venv"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and add your API keys"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Run the application
echo "🌐 Starting FastAPI server..."
echo "📍 Access the app at: http://localhost:8000"
echo ""
python -m app.main
