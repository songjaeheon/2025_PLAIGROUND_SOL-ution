# SOL-ution: Learning Helper 🎓

사내 운영 문서를 퀴즈로 변환하고, 멘토링 SOS 기능을 제공하는 학습용 웹앱입니다.

## 기능
1. **문서 업로드**: PDF 문서를 업로드하면 자동으로 텍스트를 추출합니다.
2. **퀴즈 생성**: Google Gemini AI를 활용하여 객관식 퀴즈 5개를 생성합니다.
3. **퀴즈 풀이 및 피드백**: 즉시 정답 여부를 확인하고 해설을 볼 수 있습니다.
4. **멘토링 SOS (Discord)**: 문제를 틀렸을 때 선배에게 질문을 전송할 수 있습니다.
5. **학습 기록 (Google Sheet)**: 학습 결과와 질문 내용이 자동으로 기록됩니다.

## 설치 방법 (Installation)

1. 저장소를 클론합니다.
2. 필요한 패키지를 설치합니다.
   ```bash
   pip install -r requirements.txt
   ```

## 설정 (Configuration)

`.env` 파일을 프로젝트 루트에 생성하고 다음 변수들을 설정해주세요.

```bash
GOOGLE_API_KEY=your_google_api_key
DISCORD_WEBHOOK_URL=your_discord_webhook_url
GOOGLE_SHEET_CREDENTIALS=path/to/your/service_account.json
SPREADSHEET_ID=your_spreadsheet_id
```

## 실행 방법 (Run)

```bash
streamlit run app.py
```

## 🛠️ 트러블슈팅 및 로그 확인

운영 중 발생하는 에러와 시스템 상태는 로그 파일에서 확인할 수 있습니다.

1. **로그 파일 위치**: 프로젝트 루트 디렉토리의 `./app.log` 파일에 저장됩니다.
2. **실시간 로그 확인**: 터미널에서 다음 명령어로 실시간 로그를 모니터링할 수 있습니다.
   ```bash
   tail -f app.log
   ```
3. **주요 로그 메시지 예시**:
   - **정상 작동**:
     - `[INFO] [gemini_handler.py:generate_quiz] Quiz successfully generated...`
     - `[INFO] [discord_sender.py:send_sos_message] SOS message sent successfully.`
   - **에러 발생**:
     - `[ERROR] [gemini_handler.py:extract_text_from_pdf] Error extracting PDF` (PDF 추출 실패)
     - `[ERROR] [sheet_handler.py:log_quiz_result] Error logging to sheet` (구글 시트 연동 실패)
