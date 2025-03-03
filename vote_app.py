import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import uuid
import datetime

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
    .option-button {
        width: 100%;
        margin-bottom: 10px;
        padding: 10px;
        border-radius: 5px;
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        transition: all 0.3s;
    }
    .option-button:hover {
        background-color: #e6f0ff;
        border-color: #3366cc;
    }
    .selected {
        background-color: #e6f0ff;
        border-color: #3366cc;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 구글 시트 연결 설정
@st.cache_resource
def get_gsheet_connection():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"인증 오류: {str(e)}")
        return None

# 구글 시트에서 질문 데이터 가져오기
@st.cache_data(ttl=5)  # 5초마다 데이터 새로고침
def load_questions(sheet_id):
    try:
        client = get_gsheet_connection()
        if not client:
            return []
            
        sheet = client.open_by_key(sheet_id)
        worksheets = sheet.worksheets()
        
        for ws in worksheets:
            if ws.title == "질문":
                data = ws.get_all_records()
                return data
        
        # 질문 워크시트가 없는 경우
        return []
    except Exception as e:
        st.error(f"질문 데이터 로드 오류: {str(e)}")
        return []

# 응답 저장 함수
def save_response(sheet_id, response_data):
    try:
        client = get_gsheet_connection()
        if not client:
            return False
            
        sheet = client.open_by_key(sheet_id)
        worksheet = None
        
        for ws in sheet.worksheets():
            if ws.title == "응답":
                worksheet = ws
                break
        
        if not worksheet:
            st.error("응답 워크시트를 찾을 수 없습니다.")
            return False
            
        worksheet.append_row(response_data)
        return True
    except Exception as e:
        st.error(f"응답 저장 오류: {str(e)}")
        return False

# 현재 활성화된 질문 가져오기
def get_active_question(questions):
    active_questions = [q for q in questions if q.get("활성화", "").lower() in ["y", "yes"]]
    if active_questions:
        return active_questions[0]
    return None

# 세션 ID 생성 (사용자 추적용)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# 메인 앱
def main():
    st.markdown('<div class="title">실시간 참여</div>', unsafe_allow_html=True)
    
    # 구글 시트 ID (secrets에서 가져오기)
    sheet_id = st.secrets.get("general", {}).get("sheet_id", "1DeLOnDJ4KdtZfKwEMAnYWqINTKx7vv22c3SQCu6lxQY")
    
    # 자동 새로고침 설정
    auto_refresh = st.sidebar.checkbox("자동 새로고침", value=False)
    if auto_refresh:
        refresh_interval = st.sidebar.slider("새로고침 간격(초)", min_value=3, max_value=30, value=5)
    
    # 학생 정보 입력
    if "student_info" not in st.session_state:
        st.subheader("학생 정보 입력")
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
                st.rerun()  # 페이지 새로고침
            else:
                st.error("학번과 이름을 모두 입력해주세요.")
    
    # 참여 후 질문 표시
    else:
        try:
            questions = load_questions(sheet_id)
            active_question = get_active_question(questions)
            
            if active_question:
                question_id = active_question.get("질문ID", "")
                
                # 이미 응답했는지 확인
                if f"answered_{question_id}" not in st.session_state:
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
                            if st.button(option, key=f"option_{i}", use_container_width=True):
                                st.session_state.selected_option = i
                                st.rerun()  # 페이지 새로고침
                        
                        if st.session_state.selected_option is not None:
                            selected_option = options[st.session_state.selected_option]
                            st.success(f"선택한 옵션: {selected_option}")
                            
                            if st.button("제출하기", use_container_width=True):
                                # 응답 저장
                                response = [
                                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 시간
                                    st.session_state.student_info["id"],  # 학번
                                    st.session_state.student_info["name"],  # 이름
                                    question_id,  # 질문 ID
                                    selected_option,  # 선택한 옵션
                                    st.session_state.session_id  # 세션 ID
                                ]
                                if save_response(sheet_id, response):
                                    st.session_state[f"answered_{question_id}"] = True
                                    st.success("응답이 제출되었습니다!")
                                    time.sleep(1)
                                    st.rerun()  # 페이지 새로고침
                                else:
                                    st.error("응답 제출 중 오류가 발생했습니다. 다시 시도해주세요.")
                    
                    # 단답형 질문
                    elif question_type == "단답형":
                        answer = st.text_area("답변을 입력하세요", height=100)
                        
                        if st.button("제출하기", use_container_width=True, disabled=not answer.strip()):
                            # 응답 저장
                            response = [
                                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 시간
                                st.session_state.student_info["id"],  # 학번
                                st.session_state.student_info["name"],  # 이름
                                question_id,  # 질문 ID
                                answer.strip(),  # 입력한 답변
                                st.session_state.session_id  # 세션 ID
                            ]
                            if save_response(sheet_id, response):
                                st.session_state[f"answered_{question_id}"] = True
                                st.success("응답이 제출되었습니다!")
                                time.sleep(1)
                                st.rerun()  # 페이지 새로고침
                            else:
                                st.error("응답 제출 중 오류가 발생했습니다. 다시 시도해주세요.")
                
                else:
                    st.success("이 질문에 이미 응답하셨습니다.")
                    st.markdown(f'<div class="question">{active_question.get("질문", "")}</div>', unsafe_allow_html=True)
                    st.info("다음 질문을 기다려주세요.")
            
            else:
                st.info("현재 활성화된 질문이 없습니다. 잠시 후 다시 확인해주세요.")
                
            # 로그아웃 버튼
            if st.button("다른 계정으로 참여하기", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()  # 페이지 새로고침
                
        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            st.info("페이지를 새로고침하거나 나중에 다시 시도해주세요.")
        
    # 자동 새로고침
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()  # 페이지 새로고침

if __name__ == "__main__":
    main()
