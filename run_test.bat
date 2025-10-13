@echo off
REM Test runner for Autonomous AI Research Assistant
REM Run this to verify all fixes are working

echo ================================================================================
echo   AUTONOMOUS AI RESEARCH ASSISTANT - TEST RUNNER
echo ================================================================================
echo.

REM [1/4] Activate virtual environment
echo [1/4] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment
    echo Please ensure .venv exists at D:\autonomous_research_assistant\.venv
    pause
    exit /b 1
)
echo ✓ Virtual environment activated
echo.

REM [2/4] Check Python version
echo [2/4] Checking Python version...
python --version
echo.

REM [3/4] Check dependencies
echo [3/4] Checking dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
)
echo ✓ Dependencies checked
echo.

REM [4/4] Run tests from project root using pytest (so src/ is visible)
echo [4/4] Running pipeline tests...
echo.
cd /d "%~dp0"
python -m pytest tests -v

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo   TESTS FAILED - Please review errors above
    echo ================================================================================
    pause
    exit /b 1
) else (
    echo.
    echo ================================================================================
    echo   ALL TESTS PASSED!
    echo ================================================================================
    echo.
    echo Next steps:
    echo   1. Start API:       start_api.bat
    echo   2. Start Dashboard: start_dashboard.bat
    echo   3. Open browser:    http://localhost:5000
    echo.
    pause
)
