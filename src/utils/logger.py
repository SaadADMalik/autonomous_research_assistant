import logging
import os

def setup_logging(log_dir: str = "logs", log_file: str = "pipeline.log"):
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(log_dir, log_file),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )