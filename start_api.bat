@echo off
REM Start FastAPI server for Autonomous AI Research Assistant
REM Created: 2025-10-13
REM Author: SaadADMalik

echo ================================================================================
echo   🚀 Autonomous AI Research Assistant - FastAPI Server
echo ================================================================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ ERROR: Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then: .venv\Scripts\activate.bat
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Load environment variables from .env file
if exist ".env" (
    echo 🔑 Loading environment variables from .env file...
    for /f "usebackq delims=" %%A in (".env") do (
        set "%%A"
    )
    echo ✅ Environment variables loaded
) else (
    echo ⚠️  Warning: .env file not found
    echo Create .env file with: SEMANTIC_SCHOLAR_API_KEY=your_key_here
)
echo.

REM Activate virtual environment
echo 🐍 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if FastAPI is installed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo ❌ ERROR: FastAPI not installed!
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo ✅ Virtual environment activated
echo.

REM Display server information
echo 🌐 Server Configuration:
echo   Host: http://localhost:8000
echo   Host (external): http://0.0.0.0:8000
echo   Mode: Development (auto-reload enabled)
echo   Environment: %SEMANTIC_SCHOLAR_API_KEY:~0,10%***
echo.

echo 📡 Available Endpoints:
echo   GET  /health                - Health check and system status
echo   POST /generate_summary      - Generate AI research summary
echo   GET  /docs                  - Interactive API documentation (Swagger UI)
echo   GET  /redoc                 - Alternative API documentation
echo   GET  /status                - Detailed system status
echo   GET  /sources               - Information about data sources
echo.

echo 🎯 Quick Test Commands:
echo   curl http://localhost:8000/health
echo   curl -X POST "http://localhost:8000/generate_summary" -H "Content-Type: application/json" -d "{\"query\":\"quantum computing\"}"
echo.

echo 🎨 Web Interface:
echo   Dashboard: http://localhost:5000 (run start_dashboard.bat)
echo.

echo 📋 Logs and Monitoring:
echo   - All requests logged to console
echo   - API documentation: http://localhost:8000/docs
echo   - Health monitoring: http://localhost:8000/health
echo.

echo ⚡ Starting FastAPI server with auto-reload...
echo Press Ctrl+C to stop the server
echo ================================================================================
echo.

REM Start the FastAPI server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

REM Handle server shutdown
echo.
echo ================================================================================
echo   🛑 FastAPI Server Stopped
echo ================================================================================
echo.
echo Server has been shut down gracefully.
echo Thank you for using the Autonomous AI Research Assistant!
echo.
pause