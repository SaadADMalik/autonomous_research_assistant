"""
Flask dashboard for the Autonomous AI Research Assistant.
Chatbot-style interface with conversation memory and follow-up support.
"""
from flask import Flask, render_template, request, jsonify
import requests
import logging
import os
import uuid


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use 127.0.0.1 instead of localhost to avoid Windows DNS resolution issues
API_BASE_URL = os.getenv('BACKEND_API_URL', 'http://127.0.0.1:8000')


@app.route('/')
def index():
    """Render the chatbot interface."""
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """
    Handle chat requests with conversation memory support.
    
    Expects JSON: {"query": "research question", "session_id": "uuid"}
    Returns: JSON with answer and session info
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        session_id = data.get('session_id') or str(uuid.uuid4())
        
        if not query:
            return jsonify({
                "error": "Query is required",
                "message": "Please enter a question"
            }), 400
        
        if len(query) < 3:
            return jsonify({
                "error": "Query too short",
                "message": "Please enter at least 3 characters"
            }), 400
        
        logger.info(f"Chat request: '{query}' [session: {session_id[:8]}...]")
        
        # Call FAST chat endpoint (optimized for conversation)
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "query": query, 
                "session_id": session_id,
                "max_results": 5
            },
            timeout=30  # Fast mode should respond in 5-10s
        )
        
        if response.status_code == 200:
            result = response.json()
            metadata = result.get('metadata', {})
            performance = metadata.get('performance', {})
            sources = metadata.get('sources_info', {})
            
            processing_time = performance.get('total_time', 0)
            logger.info(f"Response received in {processing_time:.1f}s")
            
            return jsonify({
                "answer": result.get('result', ''),  # Backend returns 'result', not 'answer'
                "confidence": result.get('confidence', 0),
                "session_id": result.get('session_id', session_id),
                "is_follow_up": result.get('is_follow_up', False),  # At root level, not in metadata
                "papers_used": sources.get('total_documents', 0),  # Correct path to document count
                "processing_time": processing_time  # From metadata.performance.total_time
            })
        else:
            # Backend returned an error
            try:
                error_data = response.json()
                error_message = error_data.get('message') or error_data.get('detail', 'Unknown error')
            except:
                error_message = f"Backend error (HTTP {response.status_code})"
            
            logger.error(f"API error {response.status_code}: {error_message}")
            
            # User-friendly error messages based on status code
            if response.status_code == 400:
                user_message = "Invalid query. Please rephrase and try again."
            elif response.status_code == 500:
                user_message = "The system encountered an error. Please try again in a moment."
            elif response.status_code == 504:
                user_message = "The request took too long. Try a simpler question."
            else:
                user_message = error_message
            
            return jsonify({
                "error": "Request Failed",
                "message": user_message
            }), response.status_code
            
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        return jsonify({
            "error": "Timeout",
            "message": "The request took too long. Please try a shorter or simpler question."
        }), 504
        
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to API")
        return jsonify({
            "error": "Connection Error",
            "message": "Cannot connect to the backend. The service may be starting up. Please wait a moment and try again."
        }), 503
        
    except Exception as e:
        # 🛡️ PRODUCTION: Never show raw errors to users
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Internal Error",
            "message": "An unexpected error occurred. Please try again or refresh the page."
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