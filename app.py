import streamlit as st
import os
import json
from dotenv import load_dotenv

from utils.gemini_handler import GeminiHandler
from utils.discord_sender import send_sos_message
from utils.sheet_handler import log_quiz_result

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GOOGLE_SHEET_CREDENTIALS = os.getenv("GOOGLE_SHEET_CREDENTIALS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

st.set_page_config(page_title="SOL-ution: Learning Helper", page_icon="📝")

# Initialize Session State
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = ""
if "score" not in st.session_state:
    st.session_state.score = 0
# New state variable to track if current question is checked
if "answer_checked" not in st.session_state:
    st.session_state.answer_checked = False

def reset_quiz():
    st.session_state.quiz_data = None
    st.session_state.current_q_index = 0
    st.session_state.user_answers = {}
    st.session_state.quiz_submitted = False
    st.session_state.score = 0
    st.session_state.answer_checked = False

# Sidebar
st.sidebar.title("설정 및 파일 업로드")

user_name = st.sidebar.text_input("사번 (이름)", placeholder="예: 12345 홍길동")
uploaded_file = st.sidebar.file_uploader("PDF 문서 업로드", type="pdf")

if st.sidebar.button("퀴즈 생성 시작"):
    if not user_name:
        st.sidebar.error("사번(이름)을 입력해주세요.")
    elif not uploaded_file:
        st.sidebar.error("PDF 파일을 업로드해주세요.")
    elif not GOOGLE_API_KEY:
        st.sidebar.error("Google API Key가 설정되지 않았습니다.")
    else:
        with st.spinner("문서를 분석하고 퀴즈를 생성중입니다..."):
            reset_quiz()
            st.session_state.uploaded_file_name = uploaded_file.name

            gemini = GeminiHandler(GOOGLE_API_KEY)
            text = gemini.extract_text_from_pdf(uploaded_file)

            if text:
                quiz_json = gemini.generate_quiz(text)
                if quiz_json:
                    st.session_state.quiz_data = quiz_json
                    st.success("퀴즈가 생성되었습니다!")
                else:
                    st.error("퀴즈 생성에 실패했습니다. 다시 시도해주세요.")
            else:
                st.error("PDF 텍스트 추출에 실패했습니다.")

# Helper for SOS Modal
@st.dialog("선배에게 질문하기 (SOS)")
def show_sos_dialog(question_data, user_selected_option):
    st.write("문제를 풀다가 막혔나요? 선배에게 도움을 요청해보세요.")

    st.markdown(f"**문제:** {question_data['question']}")
    st.markdown(f"**내가 고른 답:** {user_selected_option}")
    st.markdown(f"**정답:** {question_data['answer']}")

    user_question = st.text_area("질문 내용을 작성해주세요:", height=150)

    if st.button("질문 전송"):
        if not user_question:
            st.error("질문 내용을 입력해주세요.")
        else:
            with st.spinner("전송 중..."):
                # Send to Discord
                discord_success = send_sos_message(
                    DISCORD_WEBHOOK_URL,
                    user_name,
                    question_data['question'],
                    user_selected_option,
                    question_data['answer'],
                    user_question
                )

                # Log to Sheet
                sheet_success = log_quiz_result(
                    GOOGLE_SHEET_CREDENTIALS,
                    SPREADSHEET_ID,
                    user_name,
                    st.session_state.uploaded_file_name,
                    st.session_state.score,
                    question_data['question'],
                    user_question
                )

                if discord_success:
                    st.success("선배님께 질문이 전달되었습니다!")
                    st.balloons()
                else:
                    st.error("Discord 전송 실패.")

                if not sheet_success:
                    st.warning("구글 시트 기록 실패.")

# Main Quiz UI
st.title("SOL-ution 🎓")

if st.session_state.quiz_data:
    q_index = st.session_state.current_q_index
    total_q = len(st.session_state.quiz_data)

    # Progress bar
    progress = (q_index) / total_q
    st.progress(progress)

    if q_index < total_q:
        q_data = st.session_state.quiz_data[q_index]

        st.subheader(f"Q{q_index + 1}. {q_data['question']}")

        # Display options
        # Use session state to keep track of selection if we are in 'checked' state

        # If we haven't checked the answer yet, allow selection
        # If we have checked, we could disable, but keeping it enabled is fine as long as we show result based on recorded answer.
        # But to be safe, let's keep the widget key.

        choice = st.radio(
            "보기:",
            q_data['options'],
            key=f"q_{q_index}",
            index=None,
            disabled=st.session_state.answer_checked # Disable after checking to prevent changing answer
        )

        if not st.session_state.answer_checked:
            if st.button("정답 확인"):
                if not choice:
                    st.warning("보기를 선택해주세요.")
                else:
                    st.session_state.user_answers[q_index] = choice
                    st.session_state.answer_checked = True
                    # Calculate score immediately
                    if choice == q_data['answer']:
                        st.session_state.score += 20
                    st.rerun()
        else:
            # Answer is checked, show result and next buttons
            user_choice = st.session_state.user_answers.get(q_index)

            if user_choice == q_data['answer']:
                st.success("정답입니다! 🎉")
                st.markdown(f"**해설:** {q_data['explanation']}")
            else:
                st.error(f"오답입니다. 정답은 **{q_data['answer']}** 입니다.")
                st.markdown(f"**해설:** {q_data['explanation']}")

                if st.button("선배에게 물어보기 (SOS)"):
                    show_sos_dialog(q_data, user_choice)

            if st.button("다음 문제"):
                st.session_state.current_q_index += 1
                st.session_state.answer_checked = False
                st.rerun()

    else:
        st.success(f"모든 문제를 풀었습니다! 최종 점수: {st.session_state.score}점")
        if st.button("결과 저장 및 종료"):
             # Final log without specific question
             log_quiz_result(
                GOOGLE_SHEET_CREDENTIALS,
                SPREADSHEET_ID,
                user_name,
                st.session_state.uploaded_file_name,
                st.session_state.score,
                "Quiz Completed",
                "-"
            )
             st.success("기록되었습니다. 수고하셨습니다!")

else:
    st.info("왼쪽 사이드바에서 파일을 업로드하고 퀴즈 생성을 시작해주세요.")
