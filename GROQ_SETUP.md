# Groq API Setup Guide

## ✅ Step 1: Get Your FREE Groq API Key

1. **Visit**: https://console.groq.com
2. **Sign up** with GitHub or email (takes 30 seconds)
3. **Go to API Keys**: https://console.groq.com/keys
4. **Click "Create API Key"**
5. **Copy your key** (starts with `gsk_...`)

---

## ✅ Step 2: Set Environment Variable

### Option A: Quick Test (Temporary - Current Terminal Only)
```powershell
$env:GROQ_API_KEY = "gsk_your_key_here"
```

### Option B: Permanent Setup (Recommended)
```powershell
# Set system-wide environment variable
[System.Environment]::SetEnvironmentVariable('GROQ_API_KEY', 'gsk_your_key_here', 'User')

# Verify it's set
[System.Environment]::GetEnvironmentVariable('GROQ_API_KEY', 'User')
```

**Note**: After Option B, restart your terminal/VS Code for it to take effect.

---

## ✅ Step 3: Start the Backend

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
✅ SummarizerAgent initialized with Groq API (llama-3.1-8b-instant)
```

---

## ✅ Step 4: Test Performance

Expected results:
- **Fast mode (/chat)**: 5-8s total ✅
- **Thorough mode (/generate_summary)**: 8-12s total ✅
- **LLM inference**: 1-3s (vs 20-30s local) ✅

---

## 🎯 Free Tier Limits

- **30 requests per minute** (plenty for development)
- **14,400 tokens per minute**
- **No credit card required**

If you exceed limits, upgrade to paid tier (~$0.10 per 1M tokens = $0.50 per 1000 queries)

---

## 🔧 Troubleshooting

### "GROQ_API_KEY not set" error
**Solution**: Check if environment variable is set:
```powershell
$env:GROQ_API_KEY
```
If empty, go back to Step 2.

### "401 Unauthorized" error
**Solution**: Your API key is invalid. Get a new one from https://console.groq.com/keys

### "429 Rate Limit" error
**Solution**: You exceeded 30 requests/min. Wait 60 seconds or upgrade to paid tier.

---

## 📊 Performance Comparison

| Mode | Local (Ollama) | Groq API |
|------|---------------|----------|
| Fast mode | 20-30s ❌ | 5-8s ✅ |
| Thorough mode | 40-60s ❌ | 8-12s ✅ |
| LLM inference | 20-30s | 1-3s |
| Quality | Good | Better |
| Cost | $0 (hardware) | $0 (free tier) |

---

## 🚀 Quick Setup Script

Run this after getting your API key:

```powershell
# Replace with your actual key
$apiKey = "gsk_your_key_here"

# Set permanently
[System.Environment]::SetEnvironmentVariable('GROQ_API_KEY', $apiKey, 'User')

Write-Host "✅ GROQ_API_KEY set successfully!" -ForegroundColor Green
Write-Host "⚠️  Restart your terminal/VS Code for changes to take effect" -ForegroundColor Yellow
```
