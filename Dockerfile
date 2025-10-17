# ✅ Using a lightweight and modern Python image
FROM python:3.11-slim

# ✅ Sets working directory
WORKDIR /app

# ✅ Copy requirements first (for caching)
COPY requirements.txt .

# ✅ Install system deps and Python libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ✅ Copy rest of your project files
COPY . .

# ✅ Expose port 8000 (FastAPI default)
EXPOSE 8000

# ✅ Run your FastAPI app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
