import pandas as pd
import gspread
from utils.sheet_handler import _get_gspread_client
from utils.logger import logger

def get_all_scores(credentials_path, spreadsheet_id):
    """
    Fetches all scores from 'log_scores' worksheet.
    Returns a DataFrame with columns: ['Employee_ID', 'Doc_Name', 'Score', 'Timestamp']
    Applies deduplication (Max Score) per Employee per Document.
    """
    try:
        gc = _get_gspread_client(credentials_path)
        sh = gc.open_by_key(spreadsheet_id)

        # Try to open 'log_scores'
        try:
            worksheet = sh.worksheet('log_scores')
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("Worksheet 'log_scores' not found.")
            return pd.DataFrame()

        data = worksheet.get_all_records()

        if not data:
            logger.info("No data found in 'log_scores'.")
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Validate columns
        required_cols = {'Employee_ID', 'Doc_Name', 'Score', 'Timestamp'}
        if not required_cols.issubset(df.columns):
            logger.error(f"Missing columns in log_scores. Expected {required_cols}, got {df.columns}")
            return pd.DataFrame()

        # Convert Score to numeric, coercing errors to NaN then dropping
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce')
        df = df.dropna(subset=['Score'])

        # Deduplication: Keep Max Score per (Employee_ID, Doc_Name)
        # Sort by Score descending so drop_duplicates keeps the first (highest) one
        df = df.sort_values(by=['Score', 'Timestamp'], ascending=[False, False])
        df = df.drop_duplicates(subset=['Employee_ID', 'Doc_Name'], keep='first')

        return df

    except Exception as e:
        logger.error(f"Error fetching scores: {e}", exc_info=True)
        return pd.DataFrame()

def get_unique_doc_names(df):
    """
    Returns a sorted list of unique document names from the DataFrame.
    """
    if df.empty or 'Doc_Name' not in df.columns:
        return []
    return sorted(df['Doc_Name'].unique().tolist())

def calculate_ranking(df):
    """
    Given a filtered DataFrame (e.g. for a specific doc), calculate ranks.
    Logic: Sort by Score (Desc) -> Timestamp (Desc) -> Rank (Min method).
    """
    if df.empty:
        return df

    # Ensure sorted by Score (Desc), then Timestamp (Desc) (Newer is better tie-breaker? Or Older? Requirement said Timestamp Desc)
    df = df.sort_values(by=['Score', 'Timestamp'], ascending=[False, False])

    # Calculate Rank
    # method='min' means if two people have rank 1, the next is rank 3.
    df['Rank'] = df['Score'].rank(method='min', ascending=False).astype(int)

    # Reorder columns
    cols = ['Rank', 'Employee_ID', 'Score', 'Timestamp']

    return df[cols]
