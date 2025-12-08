import requests
import json
import streamlit as st
from utils.logger import logger

def send_sos_message(webhook_url, user_name, question_title, user_answer, correct_answer, user_question):
    """
    Sends a formatted Embed message to Discord via Webhook.
    """
    logger.info(f"Preparing SOS message for user: {user_name}")
    if not webhook_url:
        logger.warning("Discord Webhook URL is missing")
        st.error("Discord Webhook URL이 설정되지 않았습니다.")
        return False

    embed = {
        "title": f"[SOS] {user_name} 사원의 질문입니다.",
        "color": 16711680,  # Red color
        "fields": [
            {
                "name": "❓ 문제",
                "value": question_title,
                "inline": False
            },
            {
                "name": "❌ 사용자의 답",
                "value": user_answer,
                "inline": True
            },
            {
                "name": "✅ 정답",
                "value": correct_answer,
                "inline": True
            },
            {
                "name": "💬 질문 내용",
                "value": user_question,
                "inline": False
            }
        ],
        "footer": {
            "text": "SOL-ution Learning Helper"
        }
    }

    payload = {
        "embeds": [embed]
    }

    try:
        logger.debug(f"Sending SOS to Discord Webhook: {webhook_url}")
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        logger.info(f"SOS message sent successfully. Status Code: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response else "Unknown"
        logger.error(f"Discord Webhook failed. Status: {status_code}, Error: {e}", exc_info=True)
        st.error(f"Discord 전송 실패: {e}")
        return False
