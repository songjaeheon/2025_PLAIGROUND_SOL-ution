import gspread
from datetime import datetime
import json
import os
from utils.logger import logger

# Helper: Get GSpread Client
def _get_gspread_client(credentials_path):
    """
    Authenticates and returns the gspread client.
    Handles both file path and JSON string credentials.
    """
    if os.path.exists(credentials_path):
        logger.debug(f"Loading credentials from file: {credentials_path}")
        return gspread.service_account(filename=credentials_path)
    else:
        # Fallback: try to parse the string directly
        logger.debug("Loading credentials from JSON string")
        creds_dict = json.loads(credentials_path)
        return gspread.service_account_from_dict(creds_dict)

# Helper: Get or Create Worksheet with Headers
def _get_or_create_worksheet(sh, title, headers):
    """
    Tries to open a worksheet by title.
    If not found, creates it.
    If empty, appends headers.
    """
    try:
        worksheet = sh.worksheet(title)
        logger.debug(f"Found existing worksheet: {title}")
    except Exception:
        logger.info(f"Worksheet '{title}' not found. Creating new one.")
        # Create worksheet (rows, cols defaults are fine, or we can specify)
        worksheet = sh.add_worksheet(title=title, rows=1000, cols=20)

    # Check if empty (no headers)
    # get_all_values() returns a list of lists. If empty, it's [].
    # Or checking first row specifically.
    existing_data = worksheet.get_all_values()
    if not existing_data:
        logger.info(f"Worksheet '{title}' is empty. Adding headers.")
        worksheet.append_row(headers)

    return worksheet

def save_score(credentials_path, spreadsheet_id, employee_id, doc_name, score):
    """
    Logs the user's score to 'log_scores' sheet.
    Headers: ['Timestamp', 'Employee_ID', 'Doc_Name', 'Score']
    """
    logger.info(f"Saving score for {employee_id}")
    try:
        gc = _get_gspread_client(credentials_path)
        sh = gc.open_by_key(spreadsheet_id)

        headers = ['Timestamp', 'Employee_ID', 'Doc_Name', 'Score']
        worksheet = _get_or_create_worksheet(sh, 'log_scores', headers)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, str(employee_id), str(doc_name), int(score)]

        worksheet.append_row(row)
        logger.info("Score saved successfully")
        return True
    except Exception as e:
        logger.error("Error saving score", exc_info=True)
        return False

def save_wrong_answer(credentials_path, spreadsheet_id, employee_id, doc_name, question_info_dict, correct_answer, user_selected_answer):
    """
    Logs wrong answers to 'log_wrong_answers' sheet.
    Headers: ['Timestamp', 'Employee_ID', 'Doc_Name', 'Question_Info', 'Correct_Answer', 'User_Selected_Answer']
    Question_Info is stored as JSON string.
    """
    logger.info(f"Saving wrong answer for {employee_id}")
    try:
        gc = _get_gspread_client(credentials_path)
        sh = gc.open_by_key(spreadsheet_id)

        headers = ['Timestamp', 'Employee_ID', 'Doc_Name', 'Question_Info', 'Correct_Answer', 'User_Selected_Answer']
        worksheet = _get_or_create_worksheet(sh, 'log_wrong_answers', headers)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Convert question_info_dict to JSON string
        q_info_json = json.dumps(question_info_dict, ensure_ascii=False)

        row = [
            timestamp,
            str(employee_id),
            str(doc_name),
            q_info_json,
            str(correct_answer),
            str(user_selected_answer)
        ]

        worksheet.append_row(row)
        logger.info("Wrong answer saved successfully")
        return True
    except Exception as e:
        logger.error("Error saving wrong answer", exc_info=True)
        return False

def save_mentoring_log(credentials_path, spreadsheet_id, employee_id, question_text, correct_answer, user_selected_answer, user_question_detail):
    """
    Logs SOS requests to 'log_mentoring' sheet.
    Headers: ['Timestamp', 'Employee_ID', 'Question_Text', 'Correct_Answer', 'User_Selected_Answer', 'User_Question_Detail']
    """
    logger.info(f"Saving mentoring log for {employee_id}")
    try:
        gc = _get_gspread_client(credentials_path)
        sh = gc.open_by_key(spreadsheet_id)

        headers = ['Timestamp', 'Employee_ID', 'Question_Text', 'Correct_Answer', 'User_Selected_Answer', 'User_Question_Detail']
        worksheet = _get_or_create_worksheet(sh, 'log_mentoring', headers)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            timestamp,
            str(employee_id),
            str(question_text),
            str(correct_answer),
            str(user_selected_answer),
            str(user_question_detail)
        ]

        worksheet.append_row(row)
        logger.info("Mentoring log saved successfully")
        return True
    except Exception as e:
        logger.error("Error saving mentoring log", exc_info=True)
        return False

def get_wrong_answers(credentials_path, spreadsheet_id, employee_id):
    """
    Fetches wrong answer logs for a specific employee_id from 'log_wrong_answers'.
    Returns a list of dictionaries with keys:
    ['Timestamp', 'Doc_Name', 'Question_Text', 'Options', 'Correct_Answer', 'User_Selected_Answer']
    """
    logger.info(f"Fetching wrong answers for {employee_id}")
    try:
        gc = _get_gspread_client(credentials_path)
        sh = gc.open_by_key(spreadsheet_id)

        try:
            worksheet = sh.worksheet('log_wrong_answers')
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("Worksheet 'log_wrong_answers' not found.")
            return []

        data = worksheet.get_all_records()

        results = []
        for row in data:
            # Check for exact match on Employee_ID (converting to string to be safe)
            if str(row.get('Employee_ID', '')).strip() == str(employee_id).strip():
                # Parse Question_Info JSON
                q_info_str = row.get('Question_Info', '{}')
                try:
                    q_info = json.loads(q_info_str)
                    question_text = q_info.get('question', 'Unknown Question')
                    options = q_info.get('options', [])
                except json.JSONDecodeError:
                    question_text = "Error parsing question info"
                    options = []

                results.append({
                    'Timestamp': row.get('Timestamp'),
                    'Doc_Name': row.get('Doc_Name'),
                    'Question_Text': question_text,
                    'Options': options,
                    'Correct_Answer': row.get('Correct_Answer'),
                    'User_Selected_Answer': row.get('User_Selected_Answer')
                })

        # Sort by Timestamp descending (optional but good for UX)
        results.sort(key=lambda x: x['Timestamp'], reverse=True)

        return results

    except Exception as e:
        logger.error("Error fetching wrong answers", exc_info=True)
        return []
