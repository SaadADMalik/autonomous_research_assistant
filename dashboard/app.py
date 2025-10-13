"""
Flask dashboard for the Autonomous AI Research Assistant.
Provides a user-friendly interface for generating research summaries.
"""
from flask import Flask, render_template, request, jsonify
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI backend configuration
API_BASE_URL = "http://localhost:8000"


@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate_summary():
    """
    Handle summary generation requests.
    
    Expects JSON: {"query": "research topic", "max_results": 5}
    Returns: JSON with summary or error
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        max_results = data.get('max_results', 5)
        
        if not query:
            return jsonify({
                "error": "Query is required",
                "message": "Please enter a research topic"
            }), 400
        
        if len(query) < 3:
            return jsonify({
                "error": "Query too short",
                "message": "Please enter at least 3 characters"
            }), 400
        
        logger.info(f"Received query from dashboard: {query}")
        
        # Call FastAPI backend
        response = requests.post(
            f"{API_BASE_URL}/generate_summary",
            json={"query": query, "max_results": max_results},
            timeout=60  # 60 second timeout for processing
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("API response received successfully")
            logger.debug(f"API response: {result}")
            return jsonify(result)
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            logger.error(f"API error: {error_detail}")
            return jsonify({
                "error": "API Error",
                "message": str(error_detail)
            }), response.status_code
            
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        return jsonify({
            "error": "Timeout",
            "message": "Request took too long to process. Please try again with a simpler query."
        }), 504
        
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to API")
        return jsonify({
            "error": "Connection Error",
            "message": "Could not connect to the API server. Please ensure it's running on http://localhost:8000"
        }), 503
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Internal Error",
            "message": str(e)
        }), 500


@app.route('/health')
def health():
    """Check if the dashboard and API are healthy."""
    try:
        # Check API health
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        api_status = response.json() if response.status_code == 200 else {"status": "unhealthy"}
        
        return jsonify({
            "dashboard": "healthy",
            "api": api_status
        })
    except Exception as e:
        return jsonify({
            "dashboard": "healthy",
            "api": {"status": "unhealthy", "error": str(e)}
        }), 503


@app.route('/progress')
def progress():
    """Get processing progress (for future use with websockets)."""
    try:
        response = requests.get(f"{API_BASE_URL}/status", timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"progress": "unknown", "error": str(e)}), 503


if __name__ == '__main__':
    logger.info("Starting Flask dashboard on http://localhost:5000")
    logger.info("Make sure FastAPI server is running on http://localhost:8000")
    app.run(host='0.0.0.0', port=5000, debug=True)