# 🚀 Phase 1 Quick Start Guide

Get the chatbot transformation running in 3 minutes!

## Prerequisites
- Backend dependencies installed: `pip install -r requirements.txt`
- Virtual environment: `.venv` folder exists

---

## Step 1: Start the Backend (30 seconds)

### Option A: PowerShell (Recommended)
```powershell
.\start_phase1.ps1
```

### Option B: Batch file
```cmd
start_phase1.bat
```

### Option C: Manual
```powershell
.\.venv\Scripts\Activate.ps1
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Wait for**: `Application startup complete` message

---

## Step 2: Quick Smoke Test (1 minute)

Open a new terminal:

```powershell
python test_chat_endpoint.py
```

**Expected Result:**
```
✅ SUCCESS
⏱️  Latency: 6-8s (fast mode)
⏱️  Latency: 30-40s (thorough mode)
📊 Speedup: 4-5x faster
✅ PASSED (< 10s target)
```

---

## Step 3: Load Test (2 minutes)

Test with 10 concurrent users:

```powershell
python test_chatbot_load.py
```

**Expected Result:**
```
📊 STATISTICS: FAST MODE
Success Rate: 10/10 (100.0%)
⏱️  Latency:
  - Mean:    7.5s
  - Median:  7.3s
✅ Within target: 8/10 (80%)
```

---

## 🎯 Quick API Tests

### Fast Mode (New!)
```bash
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"query\": \"quantum computing\", \"max_results\": 5}"
```

### Thorough Mode (Original)
```bash
curl -X POST http://127.0.0.1:8000/generate_summary -H "Content-Type: application/json" -d "{\"query\": \"quantum computing\", \"max_results\": 5}"
```

---

## ✅ Success Criteria Checklist

- [ ] Backend starts without errors
- [ ] `/health` endpoint returns 200 OK
- [ ] Fast mode completes in < 10s
- [ ] Load test shows 80%+ success rate
- [ ] Fast mode is 3-5x faster than thorough mode

---

## 🐛 Troubleshooting

### Backend won't start
```powershell
# Reinstall dependencies
pip install -r requirements.txt

# Check for errors
python -c "from src.main import app; print('OK')"
```

### Slow response times
- First request is always slower (model loading)
- Check internet connection (APIs may be slow)
- Look at `metadata.performance_breakdown` in response

### Test script errors
```powershell
# Make sure backend is running
curl http://127.0.0.1:8000/health

# Check Python packages
pip install requests aiohttp
```

---

## 📚 Next Steps

1. ✅ **Phase 1 Complete** - Performance foundation working
2. 🔜 **Phase 2** - Add conversation memory and context
3. 🔜 **Phase 3** - Implement streaming responses
4. 🔜 **Phase 4** - Add inline citations

See `CHATBOT_TRANSFORMATION_PLAN.md` for full roadmap.

---

## 🎓 What Changed?

### New Endpoints
- `POST /chat` - Fast mode (no retries, 6-9s target)
- `POST /generate_summary` - Thorough mode (3 retries, 30-60s)

### New Features
- Performance profiling at every stage
- Detailed timing breakdowns in response metadata
- Mode-aware processing (fast vs thorough)

### Files Added
- `test_chat_endpoint.py` - Quick single-query test
- `test_chatbot_load.py` - 10 concurrent user test
- `start_phase1.ps1` - Easy startup script
- `PHASE1_IMPLEMENTATION.md` - Detailed docs

### Files Modified
- `src/main.py` - Split endpoints, added timing
- `src/pipelines/orchestrator.py` - Added performance metrics

---

**Ready to go!** Start with Step 1 above. 🚀
