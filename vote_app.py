import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import uuid
import re

# 페이지 설정
st.set_page_config(
    page_title="실시간 참여",
    page_icon="📊",
    layout="centered"
)

# 커스텀 CSS
st.markdown(
    """
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .title {
        font-family: 'Helvetica', sans-serif;
        font-size: 2.2em;
        color: #3366cc;
        text-align: center;
        margin-bottom: 20px;
    }
    .question {
        font-family: 'Helvetica', sans-serif;
        font-size: 1.5em;
        color: #333;
        margin-top: 20px;
        margin-bottom: 15px;
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .option-box {
        background-color: #ffffff;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        cursor: pointer;
        transition: all 0.3s;
    }
    .option-box:hover {
        background-color: #f0f8ff;
        border-color: #3366cc;
    }
    .selected {
        background-color: #e6f0ff;
        border-color: #3366cc;
        font-weight: bold;
    }
    .stTextInput, .stTextArea {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 구글 시트 연결 설정
@st.cache_resource
def get_gsheet_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    client = gspread.authorize(credentials)
    return client

# 구글 시트에서 질문 데이터 가져오기
@st.cache_data(ttl=5)  # 5초마다 데이터 새로고침
def load_questions(sheet_id):
    client = get_gsheet_connection()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.get_worksheet(0)  # 시트1 (질문/답변)
    data = worksheet.get_all_records()
    return data

# 응답 저장 함수
def save_response(sheet_id, response_data):
    client = get_gsheet_connection()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.get_worksheet(1)  # 시트2 (학생 응답)
    worksheet.append_row(response_data)

# 세션 ID 생성 (사용자 추적용)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    
# 현재 활성화된 질문 가져오기
def get_active_question(questions):
    active_questions = [q for q in questions if q.get("활성화", "").lower() == "y" or q.get("활성화", "").lower() == "yes"]
    if active_questions:
        return active_questions[0]
    return None

# 메인 앱
def main():
    st.markdown('<div class="title">실시간 참여</div>', unsafe_allow_html=True)
    
    # 구글 시트 ID
    sheet_id = "1DeLOnDJ4KdtZfKwEMAnYWqINTKx7vv22c3SQCu6lxQY"
    
    # 학생 정보 입력
    if "student_info" not in st.session_state:
        col1, col2 = st.columns(2)
        with col1:
            student_id = st.text_input("학번")
        with col2:
            student_name = st.text_input("이름")
            
        if st.button("참여하기", use_container_width=True):
            if student_id and student_name:
                st.session_state.student_info = {
                    "id": student_id,
                    "name": student_name
                }
                st.experimental_rerun()
            else:
                st.error("학번과 이름을 모두 입력해주세요.")
    
    # 참여 후 질문 표시
    else:
        questions = load_questions(sheet_id)
        active_question = get_active_question(questions)
        
        if active_question:
            # 이미 응답했는지 확인
            if f"answered_{active_question.get('질문ID', '')}" not in st.session_state:
                st.markdown(f'<div class="question">{active_question.get("질문", "")}</div>', unsafe_allow_html=True)
                
                question_type = active_question.get("유형", "").lower()
                
                # 객관식 질문
                if question_type == "객관식":
                    options = []
                    for i in range(1, 6):  # 최대 5개 옵션 지원
                        option_key = f"선택지{i}"
                        if option_key in active_question and active_question[option_key]:
                            options.append(active_question[option_key])
                    
                    if "selected_option" not in st.session_state:
                        st.session_state.selected_option = None
                        
                    for i, option in enumerate(options):
                        option_class = "option-box selected" if st.session_state.selected_option == i else "option-box"
                        option_html = f'<div class="{option_class}" id="option_{i}" onclick="this.classList.toggle(\'selected\');">{option}</div>'
                        
                        if st.button(option, key=f"option_{i}", use_container_width=True):
                            st.session_state.selected_option = i
                            st.experimental_rerun()
                    
                    if st.button("제출하기", use_container_width=True, disabled=st.session_state.selected_option is None):
                        # 응답 저장
                        response = [
                            time.strftime("%Y-%m-%d %H:%M:%S"),  # 시간
                            st.session_state.student_info["id"],  # 학번
                            st.session_state.student_info["name"],  # 이름
                            active_question.get("질문ID", ""),  # 질문 ID
                            options[st.session_state.selected_option],  # 선택한 옵션
                            st.session_state.session_id  # 세션 ID
                        ]
                        save_response(sheet_id, response)
                        st.session_state[f"answered_{active_question.get('질문ID', '')}"] = True
                        st.success("응답이 제출되었습니다!")
                        time.sleep(1)
                        st.experimental_rerun()
                
                # 단답형 질문
                elif question_type == "단답형":
                    answer = st.text_area("답변을 입력하세요", height=100)
                    
                    if st.button("제출하기", use_container_width=True, disabled=not answer.strip()):
                        # 응답 저장
                        response = [
                            time.strftime("%Y-%m-%d %H:%M:%S"),  # 시간
                            st.session_state.student_info["id"],  # 학번
                            st.session_state.student_info["name"],  # 이름
                            active_question.get("질문ID", ""),  # 질문 ID
                            answer.strip(),  # 입력한 답변
                            st.session_state.session_id  # 세션 ID
                        ]
                        save_response(sheet_id, response)
                        st.session_state[f"answered_{active_question.get('질문ID', '')}"] = True
                        st.success("응답이 제출되었습니다!")
                        time.sleep(1)
                        st.experimental_rerun()
            
            else:
                st.success("이 질문에 이미 응답하셨습니다.")
                st.markdown(f'<div class="question">{active_question.get("질문", "")}</div>', unsafe_allow_html=True)
                st.info("다음 질문을 기다려주세요.")
                
                # 5초마다 새로고침
                time.sleep(5)
                st.experimental_rerun()
        
        else:
            st.info("현재 활성화된 질문이 없습니다. 잠시 후 다시 확인해주세요.")
            # 5초마다 새로고침
            time.sleep(5)
            st.experimental_rerun()
            
        # 로그아웃 버튼
        if st.button("다른 계정으로 참여하기", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.experimental_rerun()

if __name__ == "__main__":
    main()
