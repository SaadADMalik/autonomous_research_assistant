FROM python:3.11-slim

WORKDIR /app

# Copy and install Flask dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy dashboard application
COPY . .

EXPOSE 5000

# Run Flask app
CMD ["python", "app.py"]