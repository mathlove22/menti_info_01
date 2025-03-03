import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import time
import qrcode
from io import BytesIO
from collections import Counter
from wordcloud import WordCloud
import base64
import os
import random
import uuid
import matplotlib as mpl

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
mpl.rcParams['font.family'] = ['Malgun Gothic', 'sans-serif']

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
    client = get_gsheet_connection()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.get_worksheet(0)  # 시트1 (질문/답변)
    data = worksheet.get_all_records()
    return data

# 구글 시트에서 응답 데이터 가져오기
@st.cache_data(ttl=3)  # 3초마다 데이터 새로고침
def load_responses(sheet_id):
    client = get_gsheet_connection()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.get_worksheet(1)  # 시트2 (학생 응답)
    data = worksheet.get_all_records()
    return data

# 질문 활성화/비활성화 함수
def update_question_status(sheet_id, question_id, active_status):
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

# QR 코드 생성 함수
def generate_qr_code(url):
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

# 워드 클라우드 생성 함수
def generate_wordcloud(responses):
    if not responses:
        return None
        
    text = ' '.join(responses)
    wordcloud = WordCloud(
        font_path='malgun', # 한글 폰트 경로 (필요시 수정)
        width=800, 
        height=400, 
        background_color='white',
        max_words=100
    ).generate(text)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    return fig

# 차트 생성 함수
def create_chart(data, question_type):
    if not data:
        return None
        
    if question_type == "객관식":
        # 객관식 응답 차트 (막대 그래프)
        counter = Counter(data)
        labels = list(counter.keys())
        values = list(counter.values())
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(labels, values, color='#5DA5DA')
        
        # 각 막대 위에 값 표시
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        ax.set_ylabel('응답 수')
        ax.set_title('객관식 응답 결과')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        return fig
    
    elif question_type == "단답형":
        # 단답형은 워드 클라우드 생성
        return generate_wordcloud(data)
    
    return None

# 메인 앱
def main():
    st.markdown('<div class="title">실시간 투표 관리자 대시보드</div>', unsafe_allow_html=True)
    
    # 구글 시트 ID
    sheet_id = "1DeLOnDJ4KdtZfKwEMAnYWqINTKx7vv22c3SQCu6lxQY"
    
    # 투표 앱 URL
    vote_app_url = "https://your-vote-app-url.streamlit.app"  # 투표 앱 배포 URL로 변경
    
    # 사이드바: QR 코드 및 관리 옵션
    with st.sidebar:
        st.markdown("### 투표 참여 QR 코드")
        qr_img = generate_qr_code(vote_app_url)
        st.markdown(
            f'<div class="qr-container"><img src="data:image/png;base64,{qr_img}" width="250"><p>QR 코드를 스캔하여 참여하세요</p></div>',
            unsafe_allow_html=True
        )
        
        st.markdown("---")
        
        # 질문 관리
        st.markdown("### 질문 관리")
        questions = load_questions(sheet_id)
        
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
            update_question_status(sheet_id, selected_question, True)
            st.success(f"질문 '{question_options[selected_question]}'이(가) 활성화되었습니다.")
            st.experimental_rerun()
        
        if st.button("모든 질문 비활성화", use_container_width=True):
            for q in questions:
                if q.get("활성화", "").lower() in ["y", "yes"]:
                    update_question_status(sheet_id, q.get("질문ID"), False)
            st.success("모든 질문이 비활성화되었습니다.")
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
    
    # 자동 새로고침
    time.sleep(3)
    st.experimental_rerun()

if __name__ == "__main__":
    main()
