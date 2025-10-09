# Autonomous Research Assistant

An AI-powered research assistant that autonomously gathers, analyzes, and summarizes information from various sources.

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

## Setup

1. Create a virtual environment:
```bash
python -m venv .venv
```

2. Activate the virtual environment:
- Windows:
```bash
.venv\Scripts\activate
```
- Unix/MacOS:
```bash
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the environment file:
```bash
cp .env.example .env
```

## Running the Application

Start the FastAPI server:
```bash
python src/main.py
```

The API will be available at http://localhost:8000

Health check endpoint: http://localhost:8000/health
API documentation: http://localhost:8000/docs