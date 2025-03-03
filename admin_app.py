import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import qrcode
from io import BytesIO
import base64

# 페이지 설정
st.set_page_config(
    page_title="실시간 투표 관리자",
    page_icon="📊",
    layout="wide"
)

# 커스텀 CSS
st.markdown(
    """
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .title {
        font-family: 'Helvetica', sans-serif;
        font-size: 2.5em;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 20px;
    }
    .qr-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
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

# QR 코드 생성 함수
def generate_qr_code(url):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    except Exception as e:
        st.error(f"QR 코드 생성 중 오류 발생: {str(e)}")
        return None

# 메인 앱
def main():
    st.markdown('<div class="title">실시간 투표 관리자 대시보드</div>', unsafe_allow_html=True)
    
    # 구글 시트 ID
    sheet_id = "1DeLOnDJ4KdtZfKwEMAnYWqINTKx7vv22c3SQCu6lxQY"
    
    # 투표 앱 URL (배포 후 수정 필요)
    vote_app_url = "https://your-vote-app-url.streamlit.app"  
    
    # 사이드바: QR 코드 및 관리 옵션
    with st.sidebar:
        st.markdown("### 투표 참여 QR 코드")
        qr_img = generate_qr_code(vote_app_url)
        if qr_img:
            st.markdown(
                f'<div class="qr-container"><img src="data:image/png;base64,{qr_img}" width="250"><p>QR 코드를 스캔하여 참여하세요</p></div>',
                unsafe_allow_html=True
            )
        
        st.markdown("---")
        
        # 시트 초기화 버튼
        if st.button("시트 초기화 (샘플 질문 추가)", use_container_width=True):
            try:
                client = get_gsheet_connection()
                sheet = client.open_by_key(sheet_id)
                
                # 시트1 초기화 (질문)
                if sheet.worksheet_count < 1:
                    sheet.add_worksheet(title="질문", rows=1, cols=10)
                worksheet = sheet.get_worksheet(0)
                worksheet.clear()
                
                # 헤더 설정
                headers = ["질문ID", "질문", "유형", "선택지1", "선택지2", "선택지3", "선택지4", "선택지5", "정답", "활성화"]
                worksheet.append_row(headers)
                
                # 샘플 질문 추가
                sample_questions = [
                    ["Q1", "가장 좋아하는 프로그래밍 언어는?", "객관식", "Python", "JavaScript", "Java", "C++", "기타", "", "N"],
                    ["Q2", "이 수업에서 가장 흥미로웠던 부분은?", "단답형", "", "", "", "", "", "", "N"]
                ]
                
                for q in sample_questions:
                    worksheet.append_row(q)
                
                # 시트2 초기화 (응답)
                if sheet.worksheet_count < 2:
                    sheet.add_worksheet(title="응답", rows=1, cols=6)
                response_ws = sheet.get_worksheet(1)
                response_ws.clear()
                response_headers = ["시간", "학번", "이름", "질문ID", "응답", "세션ID"]
                response_ws.append_row(response_headers)
                
                st.success("시트가 초기화되었습니다. 샘플 질문이 추가되었습니다.")
            except Exception as e:
                st.error(f"시트 초기화 중 오류 발생: {str(e)}")
    
    # 메인 컨텐츠: 간단한 안내 메시지
    st.info("이 앱은 구글 시트를 사용하여 실시간 투표를 관리합니다. 사이드바에서 시트를 초기화하고 QR 코드를 통해 학생들의 참여를 유도할 수 있습니다.")
    
    # 연결 테스트
    st.subheader("연결 테스트")
    if st.button("구글 시트 연결 테스트"):
        try:
            client = get_gsheet_connection()
            sheet = client.open_by_key(sheet_id)
            worksheet_count = sheet.worksheet_count
            st.success(f"연결 성공! 시트 수: {worksheet_count}")
        except Exception as e:
            st.error(f"연결 실패: {str(e)}")

if __name__ == "__main__":
    main()
