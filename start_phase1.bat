@echo off
REM Phase 1: Start backend with chatbot transformation

echo.
echo ================================================================================
echo    CHATBOT TRANSFORMATION - PHASE 1 STARTUP
echo ================================================================================
echo.
echo Starting backend with:
echo   - Fast Mode: /chat endpoint (6-9s target, no retries)
echo   - Thorough Mode: /generate_summary endpoint (30-60s, 3 retries)
echo.
echo Backend will be available at:
echo   - API: http://127.0.0.1:8000
echo   - Docs: http://127.0.0.1:8000/docs
echo   - Health: http://127.0.0.1:8000/health
echo.
echo ================================================================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
