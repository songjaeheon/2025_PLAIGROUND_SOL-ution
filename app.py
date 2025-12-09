import streamlit as st
import os
import base64
from PIL import Image
from dotenv import load_dotenv

from utils.gemini_handler import GeminiHandler
from utils.discord_sender import send_sos_message
from utils.sheet_handler import save_score, save_wrong_answer, save_mentoring_log, get_wrong_answers
from utils.ranking_handler import get_all_scores, get_unique_doc_names, calculate_ranking
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
# Sidebar CSS
sidebar_css = """
    /* Sidebar Button Styling */
    div[data-testid="stSidebarUserContent"] .stButton button {
        width: 100%;
        border-radius: 5px;
        padding-top: 15px;
        padding-bottom: 15px;
        border: 1px solid transparent; /* Tab-like feel */
        margin-bottom: 5px;
        transition: all 0.3s ease;
    }

    /* Force Secondary Buttons to be transparent/white by default to fix Blue-everywhere issue */
    div[data-testid="stSidebarUserContent"] .stButton button[kind="secondary"] {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        color: inherit !important;
    }

    /* Inactive Button Hover Effect */
    div[data-testid="stSidebarUserContent"] .stButton button[kind="secondary"]:hover {
        background-color: #f0f2f6 !important;
        border: 1px solid #dcdcdc !important;
        color: #0046FF !important;
    }
"""

st.markdown(
    f"""
    <style>
    /* Logo Classes */
    .logo-container {{
        display: flex;
        justify-content: center;
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

    /* Brand Styling for Primary Buttons (Main Content) */
    .stButton > button[kind="primary"] {{
        background-color: #0046FF !important;
        color: white !important;
        border-radius: 8px;
        font-weight: bold;
    }}
    .stButton > button[kind="primary"]:hover {{
        background-color: #0033CC !important;
        color: white !important;
    }}

    /* Header Emphasis */
    h1, h2, h3 {{
        color: #0046FF;
    }}

    /* Sidebar Custom CSS */
    {sidebar_css}
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
if "ranking_doc_selected" not in st.session_state:
    st.session_state.ranking_doc_selected = None
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False

# --- Helper Functions ---

def reset_quiz():
    st.session_state.quiz_data = None
    st.session_state.current_q_index = 0
    st.session_state.user_answers = {}
    st.session_state.quiz_submitted = False
    st.session_state.score = 0
    st.session_state.answer_checked = False
    st.session_state.quiz_active = False

def render_logo(width="300px", fixed_transparent=False, clickable=False):
    logo_html = ""
    if fixed_transparent:
        logo_html = f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{img_dark}" class="logo-img" style="width: {width};">
        </div>
        """
    else:
        logo_html = f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{img_light}" class="logo-img logo-light" style="width: {width};">
            <img src="data:image/png;base64,{img_dark}" class="logo-img logo-dark" style="width: {width};">
        </div>
        """

    # For clickable, we'll let Streamlit's sidebar radio handle navigation mainly,
    # but we can keep this for decorative purposes.
    # If clickable=True, clicking usually resets to home.
    # We can't easily inject a Streamlit rerun via raw HTML click.
    # So we'll skip the clickable link wrapper if it interferes with state.
    # But since it's just a visual, it's fine.

    st.markdown(logo_html, unsafe_allow_html=True)

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
        st.error("행번을 입력해주세요.")
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
            # Reset quiz state, but keep user_name and filename
            st.session_state.quiz_data = None
            st.session_state.current_q_index = 0
            st.session_state.user_answers = {}
            st.session_state.quiz_submitted = False
            st.session_state.score = 0
            st.session_state.answer_checked = False

            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.user_name = user_name # Store name in session

            try:
                gemini = GeminiHandler(GOOGLE_API_KEY)
                text = gemini.extract_text_from_pdf(uploaded_file)

                if text:
                    quiz_json = gemini.generate_quiz(text)
                    if quiz_json:
                        st.session_state.quiz_data = quiz_json
                        st.session_state.quiz_active = True # Set quiz active
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

def home_page():
    # If quiz is active, show quiz interface instead of setup
    if st.session_state.quiz_active:
        quiz_page(st.session_state.user_name)
        return

    # Center Logo
    render_logo(width="400px")

    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 30px;">
            <h3>신입, 전입 직원을 위한 퀴즈형 자기주도 학습 서비스</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Main Content: Setup Form
    st.markdown("#### 학습 설정")

    col1, col2 = st.columns([1, 2])

    # Inputs moved from Sidebar to Main Content
    user_name_input = st.text_input("행번을 입력하세요",
                                    value=st.session_state.user_name if st.session_state.user_name else "",
                                    placeholder="예: 12345 홍길동")

    uploaded_file_input = st.file_uploader("학습할 PDF 문서를 업로드하세요", type="pdf")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("퀴즈 생성 (Start Quiz)", use_container_width=True, type="primary"):
        # Store user name immediately
        st.session_state.user_name = user_name_input
        if generate_quiz_logic(user_name_input, uploaded_file_input):
            st.rerun()

def ranking_page():
    st.title("🏆 명예의 전당 (Leaderboard)")

    with st.spinner("순위 데이터를 불러오는 중입니다..."):
        df_all = get_all_scores(GOOGLE_SHEET_CREDENTIALS, SPREADSHEET_ID)

    if df_all.empty:
        st.info("아직 등록된 점수 데이터가 없습니다.")
        return

    # Document Selection
    doc_options = get_unique_doc_names(df_all)

    # Determine default index
    default_index = 0
    if st.session_state.ranking_doc_selected in doc_options:
        default_index = doc_options.index(st.session_state.ranking_doc_selected)

    selected_doc = st.selectbox("순위를 확인할 문서를 선택하세요:", doc_options, index=default_index)

    if selected_doc:
        # Filter and Rank
        df_filtered = df_all[df_all['Doc_Name'] == selected_doc].copy()
        df_ranked = calculate_ranking(df_filtered)

        # Formatting for Display
        # Add Emojis to Rank
        def format_rank(rank):
            if rank == 1: return "🥇 1"
            elif rank == 2: return "🥈 2"
            elif rank == 3: return "🥉 3"
            else: return str(rank)

        df_ranked['Rank'] = df_ranked['Rank'].apply(format_rank)

        # Rename columns for display
        df_display = df_ranked.rename(columns={
            'Rank': '순위',
            'Employee_ID': '행번',
            'Score': '점수',
            'Timestamp': '날짜'
        })

        st.dataframe(
            df_display,
            column_config={
                "순위": st.column_config.TextColumn("순위", width="medium"),
                "점수": st.column_config.NumberColumn("점수", format="%d점"),
            },
            use_container_width=True,
            hide_index=True
        )

def wrong_answers_page():
    st.title("📝 오답노트 (Wrong Answer Note)")

    col1, col2 = st.columns([3, 1])
    with col1:
        # Prefill if available in session state
        search_id = st.text_input("조회할 행번을 입력하세요:",
                                  value=st.session_state.user_name if st.session_state.user_name else "")
    with col2:
        # Align button with input
        st.write("")
        st.write("")
        search_btn = st.button("조회하기", use_container_width=True)

    if search_btn and search_id:
        st.session_state.user_name = search_id # Sync session state
        with st.spinner("오답 기록을 불러오는 중입니다..."):
            wrong_answers = get_wrong_answers(GOOGLE_SHEET_CREDENTIALS, SPREADSHEET_ID, search_id)

        if not wrong_answers:
            st.info("틀린 문제가 없습니다. (혹은 행번을 확인해주세요)")
        else:
            for idx, item in enumerate(wrong_answers):
                # Header format: [Date] [File] Question...
                header_text = f"[{item['Timestamp']}] [{item['Doc_Name']}] {item['Question_Text'][:50]}..."

                with st.expander(header_text):
                    st.markdown(f"**문제:** {item['Question_Text']}")

                    st.markdown("---")
                    st.markdown(f"**❌ 내가 고른 답:** {item['User_Selected_Answer']}")
                    st.markdown(f"**✅ 정답:** {item['Correct_Answer']}")

                    if item.get('Options'):
                        st.markdown("---")
                        st.markdown("**보기:**")
                        for opt in item['Options']:
                            st.text(f"- {opt}")
    elif search_btn and not search_id:
        st.warning("행번을 입력해주세요.")

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

            col1, col2 = st.columns(2)
            with col1:
                if st.button("결과 저장 및 홈으로"):
                     save_score(
                        GOOGLE_SHEET_CREDENTIALS,
                        SPREADSHEET_ID,
                        user_name,
                        st.session_state.uploaded_file_name,
                        st.session_state.score
                    )
                     st.success("기록되었습니다. 수고하셨습니다!")
                     # Reset quiz and go back to Setup
                     reset_quiz()
                     st.rerun()
            with col2:
                 if st.button("내 순위 확인하기"):
                     save_score(
                        GOOGLE_SHEET_CREDENTIALS,
                        SPREADSHEET_ID,
                        user_name,
                        st.session_state.uploaded_file_name,
                        st.session_state.score
                    )
                     st.success("점수가 저장되었습니다.")
                     # Go to ranking page
                     # To switch page, we need to update the sidebar state if possible,
                     # but st.sidebar.radio controls the state.
                     # We can change st.session_state.page, but the radio widget needs to match.
                     # Since we can't easily programmatically change the widget value without 'key' session state trickery.
                     # We will use st.session_state['sidebar_nav'] = '...' if we key the radio.
                     st.session_state.ranking_doc_selected = st.session_state.uploaded_file_name
                     reset_quiz()
                     st.session_state.page = "ranking" # Will be handled by the radio key sync
                     st.rerun()

    else:
        st.info("문제가 발생했습니다. 다시 시작해주세요.")
        if st.button("처음으로"):
            reset_quiz()
            st.rerun()

# --- Main Layout & Execution ---

# Sidebar Navigation
with st.sidebar:
    # Logo
    render_logo(width="200px", fixed_transparent=True)
    st.divider()

    # Menu items mapping
    menu_items = {
        "학습 시작하기": "home",
        "명예의 전당": "ranking",
        "오답노트": "wrong_answers"
    }

    # Render Buttons
    for label, page_key in menu_items.items():
        # Determine button type (primary if active, secondary if not)
        btn_type = "primary" if st.session_state.page == page_key else "secondary"

        if st.button(label, key=f"nav_{page_key}", type=btn_type, use_container_width=True):
            # Check if we need to reset the quiz
            # Case 1: Switching to a different page
            # Case 2: Clicking "Start Learning" while a quiz is active (Reset to Setup)
            should_reset = st.session_state.quiz_active

            if st.session_state.page != page_key or (page_key == 'home' and should_reset):
                st.session_state.page = page_key
                if should_reset:
                    reset_quiz()
                st.rerun()

# Router
if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "ranking":
    ranking_page()
elif st.session_state.page == "wrong_answers":
    wrong_answers_page()
