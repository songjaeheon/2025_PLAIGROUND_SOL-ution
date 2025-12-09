import streamlit as st
import os
import base64
from PIL import Image
from dotenv import load_dotenv

from utils.gemini_handler import GeminiHandler
from utils.discord_sender import send_sos_message
from utils.sheet_handler import save_score, save_wrong_answer, save_mentoring_log
from utils.logger import logger

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GOOGLE_SHEET_CREDENTIALS = os.getenv("GOOGLE_SHEET_CREDENTIALS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Favicon Setup
favicon_path = "assets/Logo_SOL-ution_favicon.ico"
page_icon = "📝" # Default fallback

try:
    if os.path.exists(favicon_path):
        page_icon = Image.open(favicon_path)
except Exception:
    pass # Keep default

st.set_page_config(page_title="SOL-ution: Learning Helper", page_icon=page_icon, layout="wide")

# --- Asset Management ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    img_light = get_base64_of_bin_file("assets/Logo_SOL-ution.png")
    img_dark = get_base64_of_bin_file("assets/Logo_SOL-ution_transparent.png")
except FileNotFoundError:
    logger.error("Logo assets not found. Please ensure 'assets/Logo_SOL-ution.png' and 'assets/Logo_SOL-ution_transparent.png' exist.")
    img_light = ""
    img_dark = ""

# --- CSS Styling ---
# Logo switching via media query
# Custom styling for buttons and layout
st.markdown(
    f"""
    <style>
    /* Logo Classes */
    .logo-container {{
        display: flex;
        justify_content: center;
        margin-bottom: 20px;
    }}
    .logo-img {{
        max_width: 100%;
        height: auto;
    }}

    /* Default (Light Mode) */
    .logo-light {{
        display: block;
    }}
    .logo-dark {{
        display: none;
    }}

    /* Light Mode Background */
    @media (prefers-color-scheme: light) {{
        .stApp {{
            background-color: #fcfcfb;
        }}
    }}

    /* Dark Mode Override */
    @media (prefers-color-scheme: dark) {{
        .logo-light {{
            display: none !important;
        }}
        .logo-dark {{
            display: block !important;
        }}
    }}

    /* Brand Styling */
    .stButton > button {{
        background-color: #0046FF !important;
        color: white !important;
        border-radius: 8px;
        font-weight: bold;
    }}
    .stButton > button:hover {{
        background-color: #0033CC !important;
        color: white !important;
    }}

    /* Header Emphasis */
    h1, h2, h3 {{
        color: #0046FF;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Session State Initialization ---
if "page" not in st.session_state:
    st.session_state.page = "home"
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
if "answer_checked" not in st.session_state:
    st.session_state.answer_checked = False

# --- Helper Functions ---

def reset_quiz():
    st.session_state.quiz_data = None
    st.session_state.current_q_index = 0
    st.session_state.user_answers = {}
    st.session_state.quiz_submitted = False
    st.session_state.score = 0
    st.session_state.answer_checked = False

def render_logo(width="300px", fixed_transparent=False):
    if fixed_transparent:
        html = f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{img_dark}" class="logo-img" style="width: {width};">
        </div>
        """
    else:
        html = f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{img_light}" class="logo-img logo-light" style="width: {width};">
            <img src="data:image/png;base64,{img_dark}" class="logo-img logo-dark" style="width: {width};">
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)

@st.dialog("선배에게 질문하기 (SOS)")
def show_sos_dialog(question_data, user_selected_option, user_name):
    st.write("문제를 풀다가 막혔나요? 선배에게 도움을 요청해보세요.")

    st.markdown(f"**문제:** {question_data['question']}")
    st.markdown(f"**내가 고른 답:** {user_selected_option}")
    st.markdown(f"**정답:** {question_data['answer']}")

    user_question = st.text_area("질문 내용을 작성해주세요:", height=150)

    if st.button("질문 전송"):
        logger.info("SOS 'Send Question' button clicked")
        if not user_question:
            st.error("질문 내용을 입력해주세요.")
            logger.warning("User attempted to send SOS without question content")
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
                sheet_success = save_mentoring_log(
                    GOOGLE_SHEET_CREDENTIALS,
                    SPREADSHEET_ID,
                    user_name,
                    question_data['question'],
                    question_data['answer'],
                    user_selected_option,
                    user_question
                )

                if discord_success:
                    st.success("선배님께 질문이 전달되었습니다!")
                    st.balloons()
                else:
                    st.error("Discord 전송 실패.")

                if not sheet_success:
                    st.warning("구글 시트 기록 실패.")

def generate_quiz_logic(user_name, uploaded_file):
    logger.info("Quiz generation triggered")
    if not user_name:
        st.error("사번(이름)을 입력해주세요.")
        logger.warning("User attempted to generate quiz without providing name/ID")
        return False
    elif not uploaded_file:
        st.error("PDF 파일을 업로드해주세요.")
        logger.warning("User attempted to generate quiz without uploading file")
        return False
    elif not GOOGLE_API_KEY:
        st.error("Google API Key가 설정되지 않았습니다.")
        logger.error("GOOGLE_API_KEY is missing from environment variables")
        return False
    else:
        logger.info(f"Processing quiz generation for user: {user_name}, file: {uploaded_file.name}")
        with st.spinner("문서를 분석하고 퀴즈를 생성중입니다..."):
            reset_quiz()
            st.session_state.uploaded_file_name = uploaded_file.name

            try:
                gemini = GeminiHandler(GOOGLE_API_KEY)
                text = gemini.extract_text_from_pdf(uploaded_file)

                if text:
                    quiz_json = gemini.generate_quiz(text)
                    if quiz_json:
                        st.session_state.quiz_data = quiz_json
                        st.success("퀴즈가 생성되었습니다!")
                        logger.info("Quiz successfully generated and stored in session state")
                        return True
                    else:
                        st.error("퀴즈 생성에 실패했습니다. 다시 시도해주세요.")
                        logger.error("Quiz generation returned None")
                        return False
                else:
                    st.error("PDF 텍스트 추출에 실패했습니다.")
                    logger.error("PDF text extraction returned None")
                    return False
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
                logger.error(f"Unexpected error during quiz generation process: {e}", exc_info=True)
                return False

# --- Page Functions ---

def home_page(user_name, uploaded_file):
    # Center Logo
    render_logo(width="400px")

    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 50px;">
            <h1>SOL-ution</h1>
            <h3>신입, 전입 직원을 위한 자기주도 학습 서비스</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Centered CTA Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("학습 시작하기", use_container_width=True):
            if generate_quiz_logic(user_name, uploaded_file):
                st.session_state.page = "quiz"
                st.rerun()

def quiz_page(user_name):
    # Quiz UI
    # Header: File Name and User Name
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(st.session_state.uploaded_file_name if st.session_state.uploaded_file_name else "SOL-ution 🎓")
    with col2:
        st.markdown(f"<div style='text-align: right; padding-top: 20px; font-size: 1.2em; font-weight: bold; color: #0046FF;'>👤 {user_name}</div>", unsafe_allow_html=True)

    if st.session_state.quiz_data:
        q_index = st.session_state.current_q_index
        total_q = len(st.session_state.quiz_data)

        # Progress bar with stage info
        progress = (q_index) / total_q
        st.progress(progress)
        st.caption(f"진행 상황: {q_index}/{total_q} 단계 ({int(progress * 100)}%)")

        if q_index < total_q:
            q_data = st.session_state.quiz_data[q_index]

            st.subheader(f"Q{q_index + 1}. {q_data['question']}")

            # Display options
            choice = st.radio(
                "보기:",
                q_data['options'],
                key=f"q_{q_index}",
                index=None,
                disabled=st.session_state.answer_checked
            )

            if not st.session_state.answer_checked:
                if st.button("정답 확인"):
                    if not choice:
                        st.warning("보기를 선택해주세요.")
                    else:
                        st.session_state.user_answers[q_index] = choice
                        st.session_state.answer_checked = True

                        if choice == q_data['answer']:
                            st.session_state.score += 20
                        else:
                            # Log wrong answer
                            question_info = {
                                "question": q_data['question'],
                                "options": q_data['options']
                            }
                            save_wrong_answer(
                                GOOGLE_SHEET_CREDENTIALS,
                                SPREADSHEET_ID,
                                user_name,
                                st.session_state.uploaded_file_name,
                                question_info,
                                q_data['answer'],
                                choice
                            )
                        st.rerun()
            else:
                # Result View
                user_choice = st.session_state.user_answers.get(q_index)

                if user_choice == q_data['answer']:
                    st.success("정답입니다! 🎉")
                    st.markdown(f"**해설:** {q_data['explanation']}")
                else:
                    st.error(f"오답입니다. 정답은 **{q_data['answer']}** 입니다.")
                    st.markdown(f"**해설:** {q_data['explanation']}")

                    if st.button("선배에게 물어보기 (SOS)"):
                        show_sos_dialog(q_data, user_choice, user_name)

                if st.button("다음 문제"):
                    st.session_state.current_q_index += 1
                    st.session_state.answer_checked = False
                    st.rerun()

        else:
            # Quiz Completed
            st.success(f"모든 문제를 풀었습니다! 최종 점수: {st.session_state.score}점")
            if st.button("결과 저장 및 홈으로"):
                 save_score(
                    GOOGLE_SHEET_CREDENTIALS,
                    SPREADSHEET_ID,
                    user_name,
                    st.session_state.uploaded_file_name,
                    st.session_state.score
                )
                 st.success("기록되었습니다. 수고하셨습니다!")
                 st.session_state.page = "home"
                 reset_quiz()
                 st.rerun()
    else:
        st.info("문제가 발생했습니다. 홈으로 돌아가주세요.")
        if st.button("홈으로 이동"):
            st.session_state.page = "home"
            st.rerun()

# --- Main Layout & Execution ---

# Sidebar is common (Inputs)
with st.sidebar:
    # Render logo in sidebar ONLY if we are in quiz mode
    if st.session_state.page == "quiz":
        render_logo(width="200px", fixed_transparent=True)
        st.divider()

    st.title("설정 및 파일 업로드")

    # Inputs
    user_name_input = st.text_input("사번 (이름)", placeholder="예: 12345 홍길동")
    uploaded_file_input = st.file_uploader("PDF 문서 업로드", type="pdf")

    # Optional: Sidebar Generate Button (for quick access or if user prefers)
    # Only show if in Quiz mode to allow restarting, OR if user wants to use sidebar to start.
    # But to keep UX clean as requested (Home screen separation), we might keep it minimal.
    # However, if user is in Quiz mode and wants to change file, they need a way to restart.
    if st.session_state.page == "quiz":
        st.divider()
        if st.button("새 퀴즈 생성"):
             if generate_quiz_logic(user_name_input, uploaded_file_input):
                 # generate_quiz_logic resets quiz, so we just stay on quiz page (or reload it)
                 st.rerun()

# Router
if st.session_state.page == "home":
    home_page(user_name_input, uploaded_file_input)
elif st.session_state.page == "quiz":
    quiz_page(user_name_input)
