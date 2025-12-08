import gspread
from datetime import datetime
import json
import os
from .logger import logger

def log_quiz_result(credentials_path, spreadsheet_id, user_name, file_name, score, question_asked, question_content):
    """
    Logs the quiz result and any questions asked to Google Sheets.
    Columns: [시간, 사번(이름), 파일명, 점수, 질문한_문제, 질문_내용]
    """
    logger.info("Connecting to Google Sheets...")
    try:
        # Check if credentials file exists or if it's a JSON string
        if os.path.exists(credentials_path):
            gc = gspread.service_account(filename=credentials_path)
        else:
            # Fallback: try to parse the string directly (if env var contains json content)
            creds_dict = json.loads(credentials_path)
            gc = gspread.service_account_from_dict(creds_dict)

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

        worksheet.append_row(row)
        logger.info("Data logged to sheet successfully.")
        return True
    except Exception as e:
        logger.error("Error logging to sheet", exc_info=True)
        return False
