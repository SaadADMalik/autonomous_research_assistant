import logging
import os
import sys

def setup_logging():
    logger = logging.getLogger()
    
    # ✅ Prevent duplicate handlers
    if logger.handlers:
        return  # Already configured
    
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Console handler with UTF-8 encoding (Windows emoji fix)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.stream.reconfigure(encoding='utf-8') if hasattr(console_handler.stream, 'reconfigure') else None
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with UTF-8 encoding
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/pipeline.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)