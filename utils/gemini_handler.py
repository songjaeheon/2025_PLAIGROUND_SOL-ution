import os
import json
import tempfile
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader

class GeminiHandler:
    def __init__(self, api_key):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        # Using gemini-flash-latest as requested for speed/efficiency, or pro.
        # Spec mentions "Gemini Pro" in text but "gemini-flash-latest" in tech stack.
        # I'll default to gemini-flash-latest for better JSON handling and speed.
        self.model = genai.GenerativeModel('gemini-flash-latest', generation_config={"response_mime_type": "application/json", "temperature": 0.3})

    def extract_text_from_pdf(self, uploaded_file):
        """
        Saves the uploaded Streamlit file temporarily and extracts text using PyPDFLoader.
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            loader = PyPDFLoader(tmp_path)
            pages = loader.load()
            text = "".join([p.page_content for p in pages])

            os.remove(tmp_path)
            return text
        except Exception as e:
            print(f"Error extracting PDF: {e}")
            return None

    def generate_quiz(self, text):
        """
        Sends the text to Gemini and requests a quiz in JSON format.
        """
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
            response = self.model.generate_content(prompt)
            # Since we set response_mime_type to json, we can just parse the text.
            quiz_data = json.loads(response.text)
            return quiz_data
        except Exception as e:
            print(f"Error generating quiz: {e}")
            return None
