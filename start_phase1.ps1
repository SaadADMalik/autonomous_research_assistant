# Phase 1: Start backend with chatbot transformation

Write-Host "`n" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "   🤖 CHATBOT TRANSFORMATION - PHASE 1 STARTUP" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "`nStarting backend with:" -ForegroundColor White
Write-Host "  ⚡ Fast Mode: /chat endpoint (6-9s target, no retries)" -ForegroundColor Yellow
Write-Host "  🔬 Thorough Mode: /generate_summary endpoint (30-60s, 3 retries)" -ForegroundColor Yellow
Write-Host "`nBackend will be available at:" -ForegroundColor White
Write-Host "  📡 API: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  📚 Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "  💚 Health: http://127.0.0.1:8000/health" -ForegroundColor Green
Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "`n⏳ Starting server..." -ForegroundColor Yellow
Write-Host "`n"

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Set encoding to UTF-8 to handle emojis in logs
$env:PYTHONIOENCODING = "utf-8"

# Start server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
