@echo off
REM Quick start script for Overture Admin Boundary List Builder (Windows)

echo.
echo 🗺️  Overture Admin Boundary List Builder
echo ========================================
echo.

REM Check if Docker is available
docker --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Docker detected
    echo.
    echo Starting with Docker...
    echo.

    REM Create list_data directory if it doesn't exist
    if not exist list_data mkdir list_data

    REM Build and run
    docker-compose up --build -d

    echo.
    echo ✓ Application started successfully!
    echo.
    echo Access the app at: http://localhost:8501
    echo.
    echo To view logs: docker-compose logs -f
    echo To stop: docker-compose down
) else (
    echo Docker not found. Starting with Python...
    echo.

    REM Check for Python
    python --version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Python 3 is required but not installed.
        exit /b 1
    )

    REM Create virtual environment if it doesn't exist
    if not exist venv (
        echo Creating virtual environment...
        python -m venv venv
    )

    REM Activate virtual environment
    echo Activating virtual environment...
    call venv\Scripts\activate.bat

    REM Install dependencies
    echo Installing dependencies...
    pip install -q -r requirements.txt

    REM Create list_data directory
    if not exist list_data mkdir list_data

    REM Run the app
    echo.
    echo ✓ Starting application...
    echo.
    streamlit run app.py
)
