import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import qrcode
from io import BytesIO
import base64
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import re
import matplotlib as mpl
import os

# 페이지 설정
st.set_page_config(
    page_title="실시간 투표 관리자",
    page_icon="📊",
    layout="wide"
)

# 한글 폰트 설정 (Streamlit Cloud에서 사용 가능한 폰트)
plt.rcParams['axes.unicode_minus'] = False
# DejaVu Sans는 기본적으로 설치되어 있어 한글 표시 가능
plt.rcParams['font.family'] = 'DejaVu Sans'

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
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .qr-large {
        width: 300px;
    }
    .qr-small {
        width: 200px;
    }
    .dashboard-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
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

# 구글 시트에서 응답 데이터 가져오기
@st.cache_data(ttl=3)  # 3초마다 데이터 새로고침
def load_responses(sheet_id):
    try:
        client = get_gsheet_connection()
        if not client:
            return []
            
        sheet = client.open_by_key(sheet_id)
        worksheets = sheet.worksheets()
        
        for ws in worksheets:
            if ws.title == "응답":
                data = ws.get_all_records()
                return data
        
        # 응답 워크시트가 없는 경우
        return []
    except Exception as e:
        st.error(f"응답 데이터 로드 오류: {str(e)}")
        return []

# 질문 활성화/비활성화 함수
def update_question_status(sheet_id, question_id, active_status):
    try:
        client = get_gsheet_connection()
        if not client:
            return False
            
        sheet = client.open_by_key(sheet_id)
        worksheet = None
        
        for ws in sheet.worksheets():
            if ws.title == "질문":
                worksheet = ws
                break
        
        if not worksheet:
            st.error("질문 워크시트를 찾을 수 없습니다.")
            return False
        
        # 모든 질문 비활성화
        if active_status:
            all_data = worksheet.get_all_records()
            for idx, row in enumerate(all_data):
                if row.get("활성화", "").lower() in ["y", "yes"]:
                    worksheet.update_cell(idx + 2, worksheet.find("활성화").col, "N")
        
        # 선택한 질문 활성화
        try:
            # 질문ID 열 찾기
            id_col = worksheet.find("질문ID").col
            # 활성화 열 찾기
            active_col = worksheet.find("활성화").col
            
            # 해당 질문ID를 가진 행 찾기
            cell_list = worksheet.findall(question_id)
            for cell in cell_list:
                if cell.col == id_col:  # 질문ID 열에서 찾은 경우만
                    worksheet.update_cell(cell.row, active_col, "Y" if active_status else "N")
                    return True
            
            st.warning(f"질문 ID '{question_id}'를 찾을 수 없습니다.")
            return False
        except Exception as e:
            st.error(f"질문 상태 업데이트 중 오류: {str(e)}")
            return False
    except Exception as e:
        st.error(f"질문 상태 업데이트 중 오류: {str(e)}")
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

# 텍스트 분석 함수 (단답형 응답용)
def analyze_text_responses(responses, max_items=10):
    if not responses:
        return None, None
    
    # 단어 분리 및 빈도 계산
    words = []
    for response in responses:
        # 문장을 단어로 분리 (한글, 영문, 숫자 포함)
        text_words = re.findall(r'\b[\w가-힣]+\b', str(response).lower())
        words.extend(text_words)
    
    # 불용어 제거 (필요시 확장)
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                 '이', '그', '저', '이것', '그것', '저것', '이런', '그런', '저런'}
    
    filtered_words = [word for word in words if word not in stopwords and len(word) > 1]
    
    # 단어 빈도 계산
    word_counts = Counter(filtered_words)
    
    # 가장 빈도가 높은 단어 선택
    top_words = word_counts.most_common(max_items)
    
    if not top_words:
        return None, None
    
    # 시각화용 데이터 준비
    labels = [word for word, _ in top_words]
    values = [count for _, count in top_words]
    
    return labels, values

# 차트 생성 함수
def create_chart(data, question_type):
    if not data:
        return None
    
    try:
        # 한글 지원을 위한 폰트 설정
        plt.figure(figsize=(10, 6))
        
        if question_type.lower() == "객관식":
            # 객관식 응답 차트 (막대 그래프)
            counter = Counter(data)
            labels = list(counter.keys())
            values = list(counter.values())
            
            # 영문 레이블로 먼저 그래프 생성
            temp_labels = [f"Option {i+1}" for i in range(len(labels))]
            bars = plt.bar(temp_labels, values, color='#5DA5DA')
            
            # 각 막대 위에 값 표시
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{height}', ha='center', va='bottom')
            
            plt.ylabel('Number of Responses')
            plt.title('Multiple Choice Results')
            plt.xticks(rotation=45, ha='right')
            
            # 실제 레이블 표시
            for i, (bar, label) in enumerate(zip(bars, labels)):
                plt.text(bar.get_x() + bar.get_width()/2., -0.5, 
                       label, ha='center', va='top', rotation=45)
            
            plt.tight_layout()
            
        elif question_type.lower() == "단답형":
            # 단답형 응답 분석 및 시각화
            labels, values = analyze_text_responses(data)
            if labels and values:
                # 영문 레이블로 먼저 그래프 생성
                temp_labels = [f"Word {i+1}" for i in range(len(labels))]
                bars = plt.barh(temp_labels, values, color='#5DA5DA')
                
                # 각 막대 옆에 값 표시
                for bar in bars:
                    width = bar.get_width()
                    plt.text(width + 0.1, bar.get_y() + bar.get_height()/2.,
                            f'{width}', ha='left', va='center')
                
                # 실제 레이블 표시
                for i, (bar, label) in enumerate(zip(bars, labels)):
                    plt.text(0, bar.get_y() + bar.get_height()/2., 
                           label, ha='right', va='center')
                
                plt.xlabel('Frequency')
                plt.title('Text Response Analysis')
                plt.tight_layout()
            else:
                plt.text(0.5, 0.5, 'Not enough data to analyze', 
                       ha='center', va='center', fontsize=12)
                plt.axis('off')
        
        return plt
    except Exception as e:
        st.error(f"차트 생성 중 오류: {str(e)}")
        return None

# 시트 초기화 함수
def initialize_sheets(sheet_id):
    try:
        client = get_gsheet_connection()
        if not client:
            st.error("구글 시트 연결에 실패했습니다.")
            return False
            
        sheet = client.open_by_key(sheet_id)
        
        # 시트1 초기화 (질문)
        worksheet = None
        for ws in sheet.worksheets():
            if ws.title == "질문":
                worksheet = ws
                break
        
        if not worksheet:
            worksheet = sheet.add_worksheet(title="질문", rows=1, cols=10)
        
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
        response_ws = None
        for ws in sheet.worksheets():
            if ws.title == "응답":
                response_ws = ws
                break
        
        if not response_ws:
            response_ws = sheet.add_worksheet(title="응답", rows=1, cols=6)
        
        response_ws.clear()
        response_headers = ["시간", "학번", "이름", "질문ID", "응답", "세션ID"]
        response_ws.append_row(response_headers)
        
        return True
    except Exception as e:
        st.error(f"시트 초기화 중 오류 발생: {str(e)}")
        return False

# 메인 앱
def main():
    st.markdown('<div class="title">실시간 투표 관리자 대시보드</div>', unsafe_allow_html=True)
    
    # 구글 시트 ID (secrets에서 가져오기)
    sheet_id = st.secrets.get("general", {}).get("sheet_id", "1DeLOnDJ4KdtZfKwEMAnYWqINTKx7vv22c3SQCu6lxQY")
    
    # 투표 앱 URL - 배포 후 실제 URL로 변경 필요
    # 예시: https://mentiinfo01-vote-jqg6tgae4s6aorcxpvvxmq.streamlit.app/
    vote_app_url = "https://your-vote-app-url.streamlit.app"  
    
    # QR 코드 크기 상태 관리
    if "qr_large" not in st.session_state:
        st.session_state.qr_large = False
    
    # 사이드바: QR 코드 및 관리 옵션
    with st.sidebar:
        st.markdown("### 투표 참여 QR 코드")
        qr_img = generate_qr_code(vote_app_url)
        if qr_img:
            # QR 코드 크기에 따라 클래스 설정
            qr_class = "qr-large" if st.session_state.qr_large else "qr-small"
            
            # QR 코드 표시
            st.markdown(
                f'<div class="qr-container">'
                f'<img src="data:image/png;base64,{qr_img}" class="{qr_class}">'
                f'<p>QR 코드를 스캔하여 참여하세요</p>'
                f'</div>',
                unsafe_allow_html=True
            )
            
            # QR 코드 크기 토글 버튼
            if st.button("QR 코드 크기 변경"):
                st.session_state.qr_large = not st.session_state.qr_large
                st.rerun()
        
        st.markdown("---")
        
        # 수동 새로고침 버튼
        if st.button("데이터 새로고침", use_container_width=True):
            st.cache_data.clear()  # 캐시 지우기
            st.success("데이터가 새로고침되었습니다.")
            time.sleep(1)
            st.rerun()
        
        st.markdown("---")
        
        # 질문 관리
        st.markdown("### 질문 관리")
        
        # 질문 데이터 로드
        questions = load_questions(sheet_id)
        
        if not questions:
            st.warning("질문 데이터가 없습니다. 시트 초기화를 진행해주세요.")
            
            # 시트 초기화 버튼
            if st.button("시트 초기화 (샘플 질문 추가)", use_container_width=True):
                if initialize_sheets(sheet_id):
                    st.success("시트가 초기화되었습니다. 샘플 질문이 추가되었습니다.")
                    st.cache_data.clear()  # 캐시 지우기
                    time.sleep(1)
                    st.rerun()  # 페이지 새로고침
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
                    st.cache_data.clear()  # 캐시 지우기
                    time.sleep(1)
                    st.rerun()  # 페이지 새로고침
            
            if st.button("모든 질문 비활성화", use_container_width=True):
                success = True
                for q in questions:
                    if q.get("활성화", "").lower() in ["y", "yes"]:
                        if not update_question_status(sheet_id, q.get("질문ID"), False):
                            success = False
                if success:
                    st.success("모든 질문이 비활성화되었습니다.")
                    st.cache_data.clear()  # 캐시 지우기
                    time.sleep(1)
                    st.rerun()  # 페이지 새로고침
    
    # 메인 컨텐츠: 결과 대시보드
    responses = load_responses(sheet_id)
    
    if not responses:
        st.info("아직 응답 데이터가 없습니다.")
    else:
        # 활성화된 질문이 있는지 확인
        if active_questions:
            active_q = active_questions[0]
            active_q_id = active_q.get("질문ID")
            question_type = active_q.get("유형", "")
            
            # 현재 질문에 대한 응답만 필터링
            current_responses = [r.get("응답", "") for r in responses if r.get("질문ID") == active_q_id]
            
            # 대시보드 헤더
            st.markdown(f"## 현재 질문: {active_q.get('질문', '')}")
            
            # 결과 차트
            st.markdown("### 응답 결과")
            
            if current_responses:
                chart = create_chart(current_responses, question_type)
                if chart:
                    st.pyplot(chart)
                
                # 원시 데이터 표시
                with st.expander("원시 응답 데이터"):
                    # 응답 데이터를 테이블로 표시
                    filtered_responses = [r for r in responses if r.get("질문ID") == active_q_id]
                    
                    # 한글 표시를 위한 데이터프레임 설정
                    df = pd.DataFrame(filtered_responses)
                    
                    # 한글 인코딩 문제 해결을 위한 설정
                    st.dataframe(
                        df,
                        column_config={
                            "시간": st.column_config.TextColumn("시간"),
                            "학번": st.column_config.TextColumn("학번"),
                            "이름": st.column_config.TextColumn("이름", width="medium"),
                            "질문ID": st.column_config.TextColumn("질문ID"),
                            "응답": st.column_config.TextColumn("응답", width="large"),
                            "세션ID": st.column_config.TextColumn("세션ID", width="small")
                        },
                        use_container_width=True
                    )
            else:
                st.info("아직 이 질문에 대한 응답이 없습니다.")
        
        else:
            st.warning("현재 활성화된 질문이 없습니다. 사이드바에서 질문을 활성화해주세요.")

if __name__ == "__main__":
    main()
