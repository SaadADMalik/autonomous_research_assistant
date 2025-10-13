@echo off
REM Start Flask dashboard for Autonomous AI Research Assistant

echo ================================================================================
echo   Starting Flask Dashboard
echo ================================================================================
echo.

call .venv\Scripts\activate.bat

echo Dashboard starting on http://localhost:5000
echo.
echo IMPORTANT: Make sure FastAPI server is running on http://localhost:8000
echo            Run start_api.bat in another terminal if not started
echo.
echo Press Ctrl+C to stop the dashboard
echo.

python dashboard\app.py