# Groq API Setup Script
# Run this after getting your API key from https://console.groq.com/keys

Write-Host "`n🚀 GROQ API SETUP" -ForegroundColor Green
Write-Host "="*50 -ForegroundColor Cyan

# Check if already set
$existingKey = [System.Environment]::GetEnvironmentVariable('GROQ_API_KEY', 'User')
if ($existingKey) {
    Write-Host "`n✅ GROQ_API_KEY already set: $($existingKey.Substring(0, 10))..." -ForegroundColor Green
    $overwrite = Read-Host "`nDo you want to overwrite it? (y/N)"
    if ($overwrite -ne 'y') {
        Write-Host "`n✅ Keeping existing key" -ForegroundColor Green
        exit 0
    }
}

# Prompt for API key
Write-Host "`n📋 Get your FREE API key:" -ForegroundColor Yellow
Write-Host "   1. Visit: https://console.groq.com/keys" -ForegroundColor White
Write-Host "   2. Sign up (takes 30 seconds)" -ForegroundColor White
Write-Host "   3. Create API Key" -ForegroundColor White
Write-Host "   4. Copy your key (starts with 'gsk_')" -ForegroundColor White

Write-Host "`n" -ForegroundColor White
$apiKey = Read-Host "Paste your Groq API key here"

# Validate key format
if (-not $apiKey) {
    Write-Host "`n❌ No key provided. Exiting." -ForegroundColor Red
    exit 1
}

if (-not $apiKey.StartsWith("gsk_")) {
    Write-Host "`n⚠️  Warning: Key doesn't start with 'gsk_'. Are you sure this is correct?" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne 'y') {
        Write-Host "`n❌ Setup cancelled" -ForegroundColor Red
        exit 1
    }
}

# Set environment variable permanently
try {
    [System.Environment]::SetEnvironmentVariable('GROQ_API_KEY', $apiKey, 'User')
    
    Write-Host "`n✅ SUCCESS!" -ForegroundColor Green
    Write-Host "="*50 -ForegroundColor Cyan
    Write-Host "`n✅ GROQ_API_KEY set successfully!" -ForegroundColor Green
    Write-Host "   Key: $($apiKey.Substring(0, 15))..." -ForegroundColor Gray
    
    Write-Host "`n⚠️  IMPORTANT:" -ForegroundColor Yellow
    Write-Host "   You must RESTART your terminal or VS Code for changes to take effect" -ForegroundColor Yellow
    
    Write-Host "`n📝 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Restart VS Code or open new terminal" -ForegroundColor White
    Write-Host "   2. Run: .\.venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "   3. Run: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor White
    Write-Host "   4. Look for: '✅ SummarizerAgent initialized with Groq API'" -ForegroundColor White
    
    Write-Host "`n🎯 Expected Performance:" -ForegroundColor Cyan
    Write-Host "   Fast mode: 5-8s (vs 20-30s local) ✅" -ForegroundColor Green
    Write-Host "   LLM inference: 1-3s (vs 20-30s local) ✅" -ForegroundColor Green
    
    Write-Host "`n" -ForegroundColor White
    
} catch {
    Write-Host "`n❌ Error setting environment variable: $_" -ForegroundColor Red
    Write-Host "`nTry manually setting it:" -ForegroundColor Yellow
    Write-Host "   [System.Environment]::SetEnvironmentVariable('GROQ_API_KEY', '$apiKey', 'User')" -ForegroundColor White
    exit 1
}

# Offer to verify
Write-Host "Press any key to verify the key is set correctly..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

$verifyKey = [System.Environment]::GetEnvironmentVariable('GROQ_API_KEY', 'User')
if ($verifyKey -eq $apiKey) {
    Write-Host "`n✅ Verification successful! Key is set." -ForegroundColor Green
} else {
    Write-Host "`n⚠️  Verification failed. You may need to restart your terminal." -ForegroundColor Yellow
}
