#!/bin/bash
# Quick start script for Overture Admin Boundary List Builder

set -e

echo "🗺️  Overture Admin Boundary List Builder"
echo "========================================"
echo ""

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "✓ Docker detected"
    echo ""
    echo "Starting with Docker..."
    echo ""

    # Create list_data directory if it doesn't exist
    mkdir -p list_data

    # Build and run
    docker-compose up --build -d

    echo ""
    echo "✓ Application started successfully!"
    echo ""
    echo "Access the app at: http://localhost:8501"
    echo ""
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"

else
    echo "Docker not found. Starting with Python..."
    echo ""

    # Check for Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is required but not installed."
        exit 1
    fi

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    echo "Activating virtual environment..."
    source venv/bin/activate

    # Install dependencies
    echo "Installing dependencies..."
    pip install -q -r requirements.txt

    # Create list_data directory
    mkdir -p list_data

    # Run the app
    echo ""
    echo "✓ Starting application..."
    echo ""
    streamlit run app.py
fi
