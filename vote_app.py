import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import uuid
import datetime
import random

# 페이지 설정
st.set_page_config(
    page_title="실시간 참여",
    page_icon="📊",
    layout="centered"
)

# 랜덤 닉네임 생성을 위한 단어 목록
ANIMALS = ["판다", "호랑이", "사자", "코끼리", "기린", "코알라", "캥거루", "토끼", "거북이", "소라게", 
           "여우", "늑대", "곰", "펭귄", "고래", "돌고래", "독수리", "참새", "까마귀", "앵무새", 
           "뱀", "악어", "고양이", "강아지", "햄스터", "다람쥐", "원숭이", "고릴라", "치타", "표범"]

ADJECTIVES = ["행복한", "즐거운", "신나는", "용감한", "지혜로운", "친절한", "재미있는", "귀여운", "멋진", 
              "활발한", "조용한", "신비로운", "익살스러운", "날렵한", "느긋한", "부지런한", "창의적인", 
              "엉뚱한", "호기심많은", "다정한", "열정적인", "사려깊은", "영리한", "우아한", "대담한"]

# 랜덤 닉네임 생성 함수
def generate_random_nickname():
    adj = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    return f"{adj} {animal}"

# 커스텀 CSS (모바일 최적화)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    
    * {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    .main {
        background-color: #f5f7fa;
    }
    
    .title {
        font-size: 2em;
        color: #1e88e5;
        text-align: center;
        margin-bottom: 15px;
        padding: 10px;
    }
    
    .subtitle {
        font-size: 1.2em;
        color: #424242;
        text-align: center;
        margin-bottom: 20px;
    }
    
    .question-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-left: 5px solid #1e88e5;
    }
    
    .question-text {
        font-size: 1.3em;
        color: #212121;
        margin-bottom: 15px;
        line-height: 1.4;
    }
    
    .option-button {
        background-color: #f5f7fa;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px 15px;
        margin-bottom: 10px;
        font-size: 1.1em;
        color: #424242;
        text-align: left;
        transition: all 0.2s;
        width: 100%;
    }
    
    .option-button:hover {
        background-color: #e3f2fd;
        border-color: #1e88e5;
    }
    
    .selected-option {
        background-color: #e3f2fd;
        border-color: #1e88e5;
        font-weight: bold;
    }
    
    .stTextInput > div > div > input {
        font-size: 1.1em;
        padding: 12px 15px;
        border-radius: 8px;
        border: 2px solid #e0e0e0;
    }
    
    .stTextArea > div > div > textarea {
        font-size: 1.1em;
        padding: 12px 15px;
        border-radius: 8px;
        border: 2px solid #e0e0e0;
    }
    
    .submit-button {
        background-color: #1e88e5;
        color: white;
        font-size: 1.1em;
        padding: 12px 20px;
        border-radius: 8px;
        border: none;
        width: 100%;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .submit-button:hover {
        background-color: #1565c0;
    }
    
    .nickname-container {
        display: flex;
        align-items: center;
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    .nickname-text {
        flex-grow: 1;
        font-size: 1.1em;
        color: #424242;
    }
    
    .nickname-button {
        background-color: #f5f7fa;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 0.9em;
        color: #424242;
        cursor: pointer;
        margin-left: 10px;
    }
    
    /* 모바일 최적화 */
    @media (max-width: 768px) {
        .title {
            font-size: 1.8em;
            padding: 5px;
        }
        
        .question-card {
            padding: 15px;
        }
        
        .question-text {
            font-size: 1.2em;
        }
        
        .option-button {
            padding: 15px;
            font-size: 1em;
        }
        
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            font-size: 1em;
            padding: 15px;
        }
        
        .submit-button {
            padding: 15px;
        }
    }
    
    /* 대기 메시지 스타일 */
    .waiting-container {
        text-align: center;
        padding: 30px;
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin: 20px 0;
    }
    
    .waiting-icon {
        font-size: 3em;
        color: #1e88e5;
        margin-bottom: 15px;
    }
    
    .waiting-text {
        font-size: 1.2em;
        color: #424242;
        margin-bottom: 10px;
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

# 랜덤 닉네임 생성
if "nickname" not in st.session_state:
    st.session_state.nickname = generate_random_nickname()

# 메인 앱
def main():
    st.markdown('<div class="title">실시간 투표 참여</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">의견을 자유롭게 표현해보세요!</div>', unsafe_allow_html=True)
    
    # 구글 시트 ID (secrets에서 가져오기)
    sheet_id = st.secrets.get("general", {}).get("sheet_id", "1DeLOnDJ4KdtZfKwEMAnYWqINTKx7vv22c3SQCu6lxQY")
    
    # 닉네임 표시 및 변경 기능
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"<div class='nickname-text'>닉네임: <b>{st.session_state.nickname}</b></div>", unsafe_allow_html=True)
    with col2:
        if st.button("변경", key="change_nickname"):
            st.session_state.show_nickname_editor = True
    
    # 닉네임 수정 폼
    if st.session_state.get("show_nickname_editor", False):
        with st.form(key="nickname_form"):
            new_nickname = st.text_input("새 닉네임", value=st.session_state.nickname)
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.form_submit_button("저장"):
                    if new_nickname.strip():
                        st.session_state.nickname = new_nickname
                        st.session_state.show_nickname_editor = False
                        st.rerun()
            with col2:
                if st.form_submit_button("랜덤 생성"):
                    st.session_state.nickname = generate_random_nickname()
                    st.session_state.show_nickname_editor = False
                    st.rerun()
    
    try:
        questions = load_questions(sheet_id)
        active_question = get_active_question(questions)
        
        if active_question:
            question_id = active_question.get("질문ID", "")
            
            # 이미 응답했는지 확인
            if f"answered_{question_id}" not in st.session_state:
                st.markdown(
                    f"""
                    <div class="question-card">
                        <div class="question-text">{active_question.get("질문", "")}</div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
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
                        
                    # 옵션 버튼 표시
                    for i, option in enumerate(options):
                        button_class = "option-button"
                        if st.session_state.selected_option == i:
                            button_class += " selected-option"
                        
                        if st.button(
                            option, 
                            key=f"option_{i}", 
                            use_container_width=True,
                            help=f"옵션 {i+1} 선택"
                        ):
                            st.session_state.selected_option = i
                            st.rerun()
                    
                    # 선택한 옵션이 있으면 제출 버튼 표시
                    if st.session_state.selected_option is not None:
                        selected_option = options[st.session_state.selected_option]
                        st.success(f"선택: {selected_option}")
                        
                        if st.button("제출하기", use_container_width=True, type="primary"):
                            # 응답 저장
                            response = [
                                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 시간
                                "",  # 학번 대신 빈 값
                                st.session_state.nickname,  # 닉네임
                                question_id,  # 질문 ID
                                selected_option,  # 선택한 옵션
                                st.session_state.session_id  # 세션 ID
                            ]
                            if save_response(sheet_id, response):
                                st.session_state[f"answered_{question_id}"] = True
                                st.balloons()  # 성공 시 풍선 효과
                                st.success("응답이 제출되었습니다!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("응답 제출 중 오류가 발생했습니다. 다시 시도해주세요.")
                
                # 단답형 질문
                elif question_type == "단답형":
                    answer = st.text_area("답변을 입력하세요", height=120)
                    
                    submit_disabled = not answer.strip()
                    if st.button(
                        "제출하기", 
                        use_container_width=True, 
                        disabled=submit_disabled,
                        type="primary"
                    ):
                        # 응답 저장
                        response = [
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 시간
                            "",  # 학번 대신 빈 값
                            st.session_state.nickname,  # 닉네임
                            question_id,  # 질문 ID
                            answer.strip(),  # 입력한 답변
                            st.session_state.session_id  # 세션 ID
                        ]
                        if save_response(sheet_id, response):
                            st.session_state[f"answered_{question_id}"] = True
                            st.balloons()  # 성공 시 풍선 효과
                            st.success("응답이 제출되었습니다!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("응답 제출 중 오류가 발생했습니다. 다시 시도해주세요.")
            
            else:
                # 이미 응답한 경우 대기 화면 표시
                st.markdown(
                    f"""
                    <div class="waiting-container">
                        <div class="waiting-icon">✓</div>
                        <div class="waiting-text">이 질문에 이미 응답하셨습니다</div>
                        <div class="question-text">{active_question.get("질문", "")}</div>
                        <p>다음 질문이 활성화되면 자동으로 표시됩니다</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                # 5초마다 자동으로 새 질문 확인 (사용자에게 표시되지 않음)
                if "last_check_time" not in st.session_state:
                    st.session_state.last_check_time = time.time()
                
                current_time = time.time()
                if current_time - st.session_state.last_check_time > 5:
                    st.session_state.last_check_time = current_time
                    st.rerun()  # 5초마다 조용히 새로고침
        
        else:
            # 활성화된 질문이 없는 경우 대기 화면 표시
            st.markdown(
                """
                <div class="waiting-container">
                    <div class="waiting-icon">⏳</div>
                    <div class="waiting-text">현재 활성화된 질문이 없습니다</div>
                    <p>질문이 활성화되면 자동으로 표시됩니다</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # 5초마다 자동으로 새 질문 확인 (사용자에게 표시되지 않음)
            if "last_check_time" not in st.session_state:
                st.session_state.last_check_time = time.time()
            
            current_time = time.time()
            if current_time - st.session_state.last_check_time > 5:
                st.session_state.last_check_time = current_time
                st.rerun()  # 5초마다 조용히 새로고침
            
        # 새 닉네임으로 참여하기 버튼 코드 수정
        if st.button("새 닉네임으로 참여하기", use_container_width=True):
            # 1. 응답 기록 초기화 - 응답 관련 세션 변수만 삭제
            for key in list(st.session_state.keys()):
                if key.startswith("answered_") or key == "selected_option":
                    del st.session_state[key]
    
            # 2. 새 세션 ID 생성
            st.session_state.session_id = str(uuid.uuid4())
    
            # 3. 새 닉네임 생성
            st.session_state.nickname = generate_random_nickname()
    
            # 4. 성공 메시지 표시 후 페이지 새로고침
            st.success("새 닉네임으로 참여합니다!")
            time.sleep(1)
            st.rerun()
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        st.info("페이지를 새로고침하거나 나중에 다시 시도해주세요.")

if __name__ == "__main__":
    main()
