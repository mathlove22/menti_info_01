import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import time
import qrcode
from io import BytesIO
from collections import Counter
import base64
import uuid

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
    .dashboard-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f1f8ff;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
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

# 구글 시트에서 질문 데이터 가져오기
@st.cache_data(ttl=5)  # 5초마다 데이터 새로고침
def load_questions(sheet_id):
    try:
        client = get_gsheet_connection()
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.get_worksheet(0)  # 시트1 (질문/답변)
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"질문 데이터를 불러오는 중 오류 발생: {str(e)}")
        return []

# 구글 시트에서 응답 데이터 가져오기
@st.cache_data(ttl=3)  # 3초마다 데이터 새로고침
def load_responses(sheet_id):
    try:
        client = get_gsheet_connection()
        sheet = client.open_by_key(sheet_id)
        
        # 두 번째 시트가 없으면 생성
        if sheet.worksheet_count < 2:
            sheet.add_worksheet(title="응답", rows=1, cols=6)
            worksheet = sheet.get_worksheet(1)
            worksheet.append_row(["시간", "학번", "이름", "질문ID", "응답", "세션ID"])
            return []
        
        worksheet = sheet.get_worksheet(1)  # 시트2 (학생 응답)
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"응답 데이터를 불러오는 중 오류 발생: {str(e)}")
        return []

# 질문 활성화/비활성화 함수
def update_question_status(sheet_id, question_id, active_status):
    try:
        client = get_gsheet_connection()
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.get_worksheet(0)
        
        # 모든 질문 비활성화
        if active_status:
            all_data = worksheet.get_all_records()
            for idx, row in enumerate(all_data):
                if row.get("활성화", "").lower() in ["y", "yes"]:
                    worksheet.update_cell(idx + 2, worksheet.find("활성화").col, "N")
        
        # 선택한 질문 활성화
        cell = worksheet.find(question_id)
        row_idx = cell.row
        col_idx = worksheet.find("활성화").col
        worksheet.update_cell(row_idx, col_idx, "Y" if active_status else "N")
        return True
    except Exception as e:
        st.error(f"질문 상태 업데이트 중 오류 발생: {str(e)}")
        return False

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

# 차트 생성 함수 (단순화)
def create_chart(data, question_type):
    if not data:
        return None
    
    try:
        # 객관식 응답 차트 (막대 그래프)
        counter = Counter(data)
        labels = list(counter.keys())
        values = list(counter.values())
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(range(len(labels)), values, color='#5DA5DA')
        
        # 각 막대 위에 값 표시
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        ax.set_ylabel('응답 수')
        ax.set_title('응답 결과')
        plt.xticks(range(len(labels)), labels, rotation=45, ha='right')
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"차트 생성 중 오류 발생: {str(e)}")
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
        
        # 질문 관리
        st.markdown("### 질문 관리")
        
        # 시트가 비어있는 경우 초기화 옵션 제공
        questions = load_questions(sheet_id)
        if not questions:
            if st.button("시트 초기화 (샘플 질문 추가)", use_container_width=True):
                try:
                    client = get_gsheet_connection()
                    sheet = client.open_by_key(sheet_id)
                    worksheet = sheet.get_worksheet(0)
                    
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
                    
                    # 응답 시트 초기화
                    if sheet.worksheet_count < 2:
                        sheet.add_worksheet(title="응답", rows=1, cols=6)
                    response_ws = sheet.get_worksheet(1)
                    response_headers = ["시간", "학번", "이름", "질문ID", "응답", "세션ID"]
                    response_ws.append_row(response_headers)
                    
                    st.success("시트가 초기화되었습니다. 샘플 질문이 추가되었습니다.")
                    time.sleep(1)
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"시트 초기화 중 오류 발생: {str(e)}")
        
        else:
            # 질문 선택 및 활성화
            question_options = {q.get("질문ID", f"질문_{i}"): q.get("질문", f"질문_{i}") 
                              for i, q in enumerate(questions)}
            
            selected_question = st.selectbox(
                "질문 선택",
                options=list(question_options.keys()),
                format_func=lambda x: question_options[x]
            )
            
            # 현재 활성화된 질문 확인
            active_questions = [q for q in questions if q.get("활성화", "").lower() in ["y", "yes"]]
            current_active = active_questions[0].get("질문ID") if active_questions else "없음"
            
            st.info(f"현재 활성화된 질문: {question_options.get(current_active, current_active)}")
            
            if st.button("이 질문 활성화", use_container_width=True):
                if update_question_status(sheet_id, selected_question, True):
                    st.success(f"질문 '{question_options[selected_question]}'이(가) 활성화되었습니다.")
                    time.sleep(1)
                    st.experimental_rerun()
            
            if st.button("모든 질문 비활성화", use_container_width=True):
                success = True
                for q in questions:
                    if q.get("활성화", "").lower() in ["y", "yes"]:
                        if not update_question_status(sheet_id, q.get("질문ID"), False):
                            success = False
                if success:
                    st.success("모든 질문이 비활성화되었습니다.")
                    time.sleep(1)
                    st.experimental_rerun()
    
    # 메인 컨텐츠: 결과 대시보드
    responses = load_responses(sheet_id)
    
    if not responses:
        st.info("아직 응답 데이터가 없습니다.")
    else:
        # 활성화된 질문이 있는지 확인
        if active_questions:
            active_q = active_questions[0]
            active_q_id = active_q.get("질문ID")
            question_type = active_q.get("유형", "").lower()
            
            # 현재 질문에 대한 응답만 필터링
            current_responses = [r.get("응답", "") for r in responses if r.get("질문ID") == active_q_id]
            
            # 응답자 수 계산
            unique_respondents = len(set([r.get("학번", "") for r in responses if r.get("질문ID") == active_q_id]))
            
            # 대시보드 헤더
            st.markdown(f"## 현재 질문: {active_q.get('질문', '')}")
            
            # 응답자 수 표시
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f'<div class="metric-card"><h3>응답자 수</h3><h2>{unique_respondents}</h2></div>',
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(
                    f'<div class="metric-card"><h3>총 응답 수</h3><h2>{len(current_responses)}</h2></div>',
                    unsafe_allow_html=True
                )
            
            # 결과 차트
            st.markdown("### 응답 결과")
            
            if current_responses:
                fig = create_chart(current_responses, question_type)
                if fig:
                    st.pyplot(fig)
                
                # 원시 데이터 표시
                with st.expander("원시 응답 데이터"):
                    response_df = pd.DataFrame({
                        "응답": current_responses
                    })
                    st.dataframe(response_df)
            else:
                st.info("아직 이 질문에 대한 응답이 없습니다.")
        
        else:
            st.warning("현재 활성화된 질문이 없습니다. 사이드바에서 질문을 활성화해주세요.")

if __name__ == "__main__":
    main()
