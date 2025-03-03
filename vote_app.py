import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import uuid

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

# 세션 ID 생성 (사용자 추적용)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# 메인 앱
def main():
    st.markdown('<div class="title">실시간 참여</div>', unsafe_allow_html=True)
    
    # 구글 시트 ID (secrets에서 가져오기)
    sheet_id = st.secrets.get("general", {}).get("sheet_id", "1DeLOnDJ4KdtZfKwEMAnYWqINTKx7vv22c3SQCu6lxQY")
    
    # 연결 테스트
    if st.button("구글 시트 연결 테스트"):
        try:
            client = get_gsheet_connection()
            if not client:
                st.error("구글 시트 연결에 실패했습니다.")
                return
                
            sheet = client.open_by_key(sheet_id)
            
            # 워크시트 목록 가져오기 (worksheet_count 대신 worksheets() 메서드 사용)
            worksheets = sheet.worksheets()
            worksheet_names = [ws.title for ws in worksheets]
            
            st.success(f"연결 성공! 시트 수: {len(worksheets)}")
            st.write(f"워크시트 목록: {', '.join(worksheet_names)}")
            
            # 서비스 계정 정보 확인
            service_account_email = st.secrets["gcp_service_account"]["client_email"]
            st.info(f"사용 중인 서비스 계정: {service_account_email}")
        except Exception as e:
            st.error(f"연결 실패: {str(e)}")
    
    # 학생 정보 입력
    st.subheader("학생 정보")
    col1, col2 = st.columns(2)
    with col1:
        student_id = st.text_input("학번")
    with col2:
        student_name = st.text_input("이름")
    
    st.info("이 앱은 실시간 투표 참여를 위한 앱입니다. 현재 기본 기능만 구현되어 있습니다.")

if __name__ == "__main__":
    main()
