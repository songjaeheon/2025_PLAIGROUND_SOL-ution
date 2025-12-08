import os
import json
import tempfile
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader
from utils.logger import logger

class GeminiHandler:
    def __init__(self, api_key):
        self.api_key = api_key
        try:
            genai.configure(api_key=self.api_key)
            # Using gemini-flash-latest as requested for speed/efficiency, or pro.
            # Spec mentions "Gemini Pro" in text but "gemini-flash-latest" in tech stack.
            # I'll default to gemini-flash-latest for better JSON handling and speed.
            self.model = genai.GenerativeModel('gemini-flash-latest', generation_config={"response_mime_type": "application/json", "temperature": 0.3})
            logger.info("GeminiHandler initialized with model: gemini-flash-latest")
        except Exception as e:
            logger.error("Failed to initialize GeminiHandler", exc_info=True)
            raise e

    def extract_text_from_pdf(self, uploaded_file):
        """
        Saves the uploaded Streamlit file temporarily and extracts text using PyPDFLoader.
        """
        logger.info(f"Starting PDF extraction for file: {uploaded_file.name if hasattr(uploaded_file, 'name') else 'Unknown'}")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            logger.debug(f"Temporary file created at: {tmp_path}")

            loader = PyPDFLoader(tmp_path)
            pages = loader.load()
            text = "".join([p.page_content for p in pages])

            os.remove(tmp_path)
            logger.info(f"PDF extraction successful. Extracted {len(text)} characters.")
            return text
        except Exception as e:
            logger.error("Error extracting PDF", exc_info=True)
            return None

    def generate_quiz(self, text):
        """
        Sends the text to Gemini and requests a quiz in JSON format.
        """
        logger.info("Starting quiz generation via Gemini API")
        prompt = f"""
        당신은 기업 신입 사원 교육 담당자입니다.
        다음 제공되는 문서 내용을 바탕으로 신입 사원 교육용 객관식 퀴즈 5개를 만들어주세요.

        문서 내용:
        {text[:300000]}
        (내용이 너무 길 경우 앞부분 300000자만 참조합니다)

        다음 JSON 형식으로 출력해주세요:
        [
          {{
            "question": "문제 내용",
            "options": ["보기1", "보기2", "보기3", "보기4"],
            "answer": "정답 보기 (예: 보기1)",
            "explanation": "해설 내용"
          }}
        ]
        """

        try:
            logger.debug("Sending prompt to Gemini API...")
            response = self.model.generate_content(prompt)
            logger.info("Received response from Gemini API")

            # Since we set response_mime_type to json, we can just parse the text.
            quiz_data = json.loads(response.text)
            logger.info(f"Successfully parsed quiz data. Generated {len(quiz_data)} questions.")
            return quiz_data
        except json.JSONDecodeError as je:
            logger.error(f"JSON parsing failed for Gemini response: {response.text if 'response' in locals() else 'No response'}", exc_info=True)
            return None
        except Exception as e:
            logger.error("Error generating quiz", exc_info=True)
            return None
