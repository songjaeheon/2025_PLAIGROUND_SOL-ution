import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger():
    """
    Sets up the logger with StreamHandler and RotatingFileHandler.
    Ensures handlers are not added multiple times (useful for Streamlit).
    """
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(filename)s:%(funcName)s] %(message)s')

        # Console Handler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # File Handler
        # Ensure the log file is created in the current directory or specified path
        # app.log
        file_handler = RotatingFileHandler('app.log', maxBytes=5*1024*1024, backupCount=3)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()
