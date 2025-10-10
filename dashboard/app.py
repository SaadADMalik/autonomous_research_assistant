from flask import Flask, render_template, request
import requests
import logging
import os
from src.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Use environment variable to determine API URL (localhost for local, api for Docker)
API_URL = os.getenv("API_URL", "http://localhost:8000")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        query = request.form.get("query")
        logger.info(f"Received query from dashboard: {query}")
        try:
            response = requests.post(
                f"{API_URL}/generate_summary",
                json={"query": query},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"API response: {result}")
            return render_template("index.html", output=result.get("result", ""), progress="Completed")
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return render_template("index.html", output="", progress=f"Error: {str(e)}")
    return render_template("index.html", output="", progress="")

@app.route("/progress")
def progress():
    return {"progress": "Processing..."}