# Why Educational Fallback is Triggering & How to Fix It

## 🔍 Root Cause Analysis

Your system has **4 APIs** available:
1. **Semantic Scholar** - 200M+ papers (PRIMARY)
2. **OpenAlex** - 200M+ papers  
3. **Wikipedia** - Encyclopedia articles
4. **arXiv** - Physics/CS preprints (SLOW, skipped in fast mode)

### Why All APIs Are Returning 0 Results:

**Issue #1: No Semantic Scholar API Key** ❌
- **Current**: No API key configured
- **Result**: Rate limited to 1 request/second, burst limits enforced
- **Impact**: Most queries get blocked immediately

**Issue #2: Rate Limiting in Fast Mode**
- Fast mode (default in chat): 8-second timeout window
- All 3 APIs race simultaneously (OpenAlex, Semantic Scholar, Wikipedia)
- If Semantic Scholar is rate-limited, other APIs may not find matches
- Educational fallback kicks in when ALL return 0 results

**Issue #3: Query Specificity**
- Some queries are too specific/don't match paper titles
- Wikipedia only has encyclopedia articles (not research papers)
- OpenAlex search may not find matches for certain topics

---

## ✅ Solution Implemented

### Frontend Transparency (DONE)
Added warning badge showing when educational fallback is active:

```
Before: Confidence: 91%  2 papers  5.7s

After:  Confidence: 91%  ⚠️ 2 educational papers (APIs returned 0 results)  5.7s
```

- **Yellow badge** with warning icon
- Clear message that APIs failed
- Helps users understand content source

---

## 🔧 How to Fix API Issues

### Option 1: Add Semantic Scholar API Key (RECOMMENDED)

**Benefits:**
- 10x higher rate limits
- Priority access during peak hours
- 100% free

**Steps:**
1. Get free API key: https://www.semanticscholar.org/product/api#api-key
2. Add to your environment:

```powershell
# Windows PowerShell
$env:SEMANTIC_SCHOLAR_API_KEY = "your-key-here"

# Or add permanently to system environment variables
[Environment]::SetEnvironmentVariable("SEMANTIC_SCHOLAR_API_KEY", "your-key-here", "User")
```

3. Restart backend:

```powershell
Get-Process python* | Stop-Process -Force
.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Option 2: Use Thorough Mode for Specific Queries

- Thorough mode gives 15s timeout (vs 8s in fast mode)
- Uses all 4 APIs including arXiv  
- Higher success rate but slower (~15-25s)

**Implementation**: Already available via `/generate_summary` endpoint (not chat)

### Option 3: Increase Timeout in Fast Mode

Edit [src/data_fetcher.py](src/data_fetcher.py) line 213:

```python
# Current
timeout_window = 8.0  # 8s window

# Increase to:
timeout_window = 12.0  # 12s window - more time for APIs to respond
```

---

## 📊 Current System Behavior

### FAST Mode (Chat Endpoint) - 8s Timeout
```
Launch: OpenAlex + Semantic Scholar + Wikipedia (parallel)
         ↓ (8 seconds max)
Results: Collect whoever responds
         ↓
Filter:  Remove irrelevant papers
         ↓
Fallback: If 0 papers → Educational content
```

### Rate Limit Status:
- **Semantic Scholar**: ❌ Rate limited (no API key)
- **OpenAlex**: ⚠️ Sometimes returns 0 (query-dependent)
- **Wikipedia**: ⚠️ Encyclopedia only (not research papers)
- **arXiv**: ⏭️ Skipped (too slow for chat)

---

## 🎯 Recommended Action

1. **Get Semantic Scholar API key** (5 min, free)
2. **Test with the same queries** - should see real papers
3. **Monitor frontend badges** - warning should disappear

Example after fix:
```
Before: ⚠️ 3 educational papers (APIs returned 0 results)
After:  5 papers  ✅ From Semantic Scholar + OpenAlex
```

---

## 📝 Files Modified

- `dashboard/app.py` - Added educational_fallback detection
- `dashboard/templates/index.html` - Added warning badge styling + logic
- Frontend now shows: `⚠️ N educational papers (APIs returned 0 results)`

---

## 🧪 Testing After API Key Added

Run this to verify APIs are working:

```powershell
.\.venv\Scripts\python.exe test_api_failures.py
```

**Expected output:**
```
✅ GOOD: All real papers, no educational fallback

SOURCE BREAKDOWN:
{
  "semantic_scholar": 3,
  "openalex": 2,
  "educational": 0  # Should be 0 now
}
```
