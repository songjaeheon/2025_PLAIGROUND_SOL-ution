import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger():
    """
    Configures and returns a singleton logger for the application.
    Prevents duplicate handlers on Streamlit reruns.
    """
    logger = logging.getLogger("SOL-ution")
    logger.setLevel(logging.INFO)

    # Check if handlers are already added to avoid duplication
    if not logger.handlers:
        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(filename)s:%(funcName)s] %(message)s'
        )

        # 1. StreamHandler (Console)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # 2. RotatingFileHandler (File)
        # Ensure the log file is created in the root directory or specific path
        # Using 'app.log' in the current working directory
        log_file_path = os.path.join(os.getcwd(), 'app.log')
        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info("Logger initialized successfully.")

    return logger

# Initialize logger instance to be imported by other modules
logger = setup_logger()
