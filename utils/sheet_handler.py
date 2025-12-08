import gspread
from datetime import datetime
import json
import os
from utils.logger import logger

def log_quiz_result(credentials_path, spreadsheet_id, user_name, file_name, score, question_asked, question_content):
    """
    Logs the quiz result and any questions asked to Google Sheets.
    Columns: [시간, 사번(이름), 파일명, 점수, 질문한_문제, 질문_내용]
    """
    logger.info(f"Starting to log quiz result for user: {user_name}")
    try:
        # Check if credentials file exists or if it's a JSON string
        if os.path.exists(credentials_path):
            logger.debug(f"Loading credentials from file: {credentials_path}")
            gc = gspread.service_account(filename=credentials_path)
        else:
            # Fallback: try to parse the string directly (if env var contains json content)
            logger.debug("Loading credentials from JSON string")
            creds_dict = json.loads(credentials_path)
            gc = gspread.service_account_from_dict(creds_dict)

        logger.debug(f"Opening spreadsheet with ID: {spreadsheet_id}")
        sh = gc.open_by_key(spreadsheet_id)
        # Assuming the first sheet is the target
        worksheet = sh.sheet1

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Row data
        row = [
            timestamp,
            user_name,
            file_name,
            score,
            question_asked,
            question_content
        ]

        logger.info(f"Appending row to sheet: {row}")
        worksheet.append_row(row)
        logger.info("Successfully logged result to Google Sheets")
        return True
    except Exception as e:
        logger.error("Error logging to sheet", exc_info=True)
        return False
