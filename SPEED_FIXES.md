# Speed Fix Options - CPU Bottleneck

## Current Problem
- CPU LLM inference: 20-30s (unacceptable for chatbot)
- Hardware: Intel CPU + Iris Xe GPU (2GB)
- Target: <10s response time

---

## OPTION 1: Groq Cloud API (FREE, FASTEST) ⭐⭐⭐
**Best choice for production**

### Speed
- Inference: 1-3s (vs 20-30s local)
- Total: 5-8s end-to-end ✅

### Cost
- Free tier: 30 requests/min
- Paid: $0.10 per 1M tokens (~$0.50 per 1000 queries)

### Implementation
```bash
pip install groq
```

```python
# In summarizer_agent.py
import os
from groq import Groq

class SummarizerAgent:
    def __init__(self):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = "llama-3.1-8b-instant"  # 1-2s inference
        
    async def run(self, input_data):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )
        return response.choices[0].message.content
```

**Get API key**: https://console.groq.com (free signup)

---

## OPTION 2: Disable LLM - Extractive Only (IMMEDIATE FIX)
**Best for "good enough" right now**

### Speed
- Total: 2-5s ✅
- No LLM overhead

### Quality
- Good: Extracts relevant sentences
- Trade-off: Not as natural as LLM summaries

### Implementation
```python
# In summarizer_agent.py __init__
def __init__(self):
    self.ollama = None  # Force extractive mode
    logger.info("✅ Extractive mode enabled (no LLM)")
```

**1 line change, done in 30 seconds**

---

## OPTION 3: Better Extractive (TextRank)
**Best quality without LLM**

### Speed
- Total: 3-6s ✅
- Smart sentence ranking

### Implementation
```bash
pip install nltk
```

```python
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def textrank_summarize(text, query, num_sentences=5):
    sentences = sent_tokenize(text)
    vectorizer = TfidfVectorizer()
    
    # Add query for relevance scoring
    all_text = sentences + [query]
    vectors = vectorizer.fit_transform(all_text)
    
    # Calculate similarity to query
    query_vector = vectors[-1]
    similarities = cosine_similarity(query_vector, vectors[:-1]).flatten()
    
    # Get top sentences
    top_indices = similarities.argsort()[-num_sentences:][::-1]
    summary = '. '.join([sentences[i] for i in sorted(top_indices)])
    
    return summary
```

---

## OPTION 4: Enable Intel GPU
**Your Iris Xe GPU can help!**

### Speed
- Expected: 8-12s (2x faster than CPU)
- Requires: PyTorch with GPU support

### Setup
```bash
# Install IPEX (Intel Extension for PyTorch)
pip install intel-extension-for-pytorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

**Warning**: Complex setup, may not work with Ollama

---

## OPTION 5: OpenAI/Claude API
**Most reliable, costs money**

### Speed
- Inference: 1-2s
- Total: 5-8s ✅

### Cost
- OpenAI GPT-4o-mini: $0.15 per 1M tokens
- Claude Haiku: $0.25 per 1M tokens
- ~$0.50-1.00 per 1000 queries

### Implementation
```bash
pip install openai anthropic
```

---

## RECOMMENDED PATH

### TODAY (Right Now)
**Option 2**: Disable LLM
- Change 1 line → 5s response time
- Test if extractive quality is acceptable

### THIS WEEK
**Option 1**: Switch to Groq API
- Free tier available
- 8s response time
- Better quality than local

### IF GROQ FREE TIER EXHAUSTED
**Option 5**: Paid API (OpenAI/Claude)
- ~$10/month for moderate usage
- Most reliable

---

## What do you want to do?
1. **Quick fix now** → I'll disable LLM (Option 2)
2. **Best solution** → I'll set up Groq API (Option 1)
3. **Try GPU** → I'll attempt Intel GPU setup (Option 4)
