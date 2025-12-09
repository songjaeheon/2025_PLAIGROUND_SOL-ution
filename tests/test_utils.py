import unittest
from unittest.mock import MagicMock, patch
import json
import os
from utils.discord_sender import send_sos_message
from utils.gemini_handler import GeminiHandler
from utils.sheet_handler import save_score

class TestUtils(unittest.TestCase):

    @patch('utils.discord_sender.requests.post')
    def test_send_sos_message(self, mock_post):
        # Setup mock
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test data
        webhook_url = "http://fake.webhook"
        user_name = "TestUser"
        question_title = "What is X?"
        user_answer = "Y"
        correct_answer = "X"
        user_question = "Why not Y?"

        # Execute
        result = send_sos_message(webhook_url, user_name, question_title, user_answer, correct_answer, user_question)

        # Assert
        self.assertTrue(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], webhook_url)
        self.assertIn("embeds", kwargs['json'])
        self.assertEqual(kwargs['json']['embeds'][0]['title'], "[SOS] TestUser 사원의 질문입니다.")

    @patch('utils.gemini_handler.genai.GenerativeModel')
    @patch('utils.gemini_handler.PyPDFLoader')
    def test_gemini_handler(self, mock_loader, mock_model_cls):
        # Setup Mocks
        mock_model_instance = MagicMock()
        mock_model_cls.return_value = mock_model_instance

        expected_json = [
            {
                "question": "Q1",
                "options": ["A", "B"],
                "answer": "A",
                "explanation": "Exp"
            }
        ]

        mock_response = MagicMock()
        mock_response.text = json.dumps(expected_json)
        mock_model_instance.generate_content.return_value = mock_response

        # Mock PDF Loader
        mock_loader_instance = MagicMock()
        mock_page = MagicMock()
        mock_page.page_content = "PDF Content"
        mock_loader_instance.load.return_value = [mock_page]
        mock_loader.return_value = mock_loader_instance

        # Execute
        handler = GeminiHandler("fake_key")

        # Mock uploaded file
        mock_file = MagicMock()
        mock_file.getvalue.return_value = b"fake pdf content"

        text = handler.extract_text_from_pdf(mock_file)
        self.assertEqual(text, "PDF Content")

        quiz = handler.generate_quiz(text)
        self.assertEqual(quiz, expected_json)

    @patch('utils.sheet_handler.os.path.exists')
    @patch('utils.sheet_handler.gspread.service_account')
    def test_sheet_handler(self, mock_service_account, mock_exists):
        # Setup Mock
        mock_exists.return_value = True  # Pretend file exists
        mock_gc = MagicMock()
        mock_sh = MagicMock()
        mock_ws = MagicMock()

        mock_service_account.return_value = mock_gc
        mock_gc.open_by_key.return_value = mock_sh
        # save_score looks for 'log_scores' worksheet
        mock_sh.worksheet.return_value = mock_ws

        # Execute
        result = save_score("fake_creds.json", "fake_id", "User", "File", 100)

        # Assert
        self.assertTrue(result)
        mock_ws.append_row.assert_called_once()
        args, _ = mock_ws.append_row.call_args
        row = args[0]
        self.assertEqual(row[1], "User")
        # index 3 is Score (0=Time, 1=ID, 2=Doc, 3=Score)
        self.assertEqual(row[3], 100)

if __name__ == '__main__':
    unittest.main()
