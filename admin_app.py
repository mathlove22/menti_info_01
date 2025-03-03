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
import numpy as np
import matplotlib.font_manager as fm
from PIL import Image, ImageDraw, ImageFont
import io

# 페이지 설정
st.set_page_config(
    page_title="실시간 투표 관리자",
    page_icon="📊",
    layout="wide"
)

# 한글 폰트 문제 해결을 위한 웹 폰트 설정
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
    """,
    unsafe_allow_html=True
)

# 커스텀 CSS
st.markdown(
    """
    <style>
    * {
        font-family: 'Noto Sans KR', sans-serif;
    }
    .main {
        background-color: #f8f9fa;
    }
    .title {
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 2.5em;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 20px;
        font-weight: 700;
    }
    .qr-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        margin-bottom: 20px;
    }
    .qr-image {
        width: 100%; 
        max-width: 600px;
        margin: 0 auto;
        display: block;
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
def generate_qr_code(url, size=10):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,  # 크기 조절
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

# PIL을 사용하여 한글 텍스트가 있는 이미지 생성
def create_image_with_korean_text(data, question_type, width=1200, height=800):
    # 배경 이미지 생성
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    try:
        # 기본 폰트 설정 (한글 지원 필요)
        # 폰트 파일 경로는 환경에 따라 다를 수 있음
        try:
            # 일반적인 리눅스 시스템의 폰트 경로
            font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
            title_font = ImageFont.truetype(font_path, 36)
            normal_font = ImageFont.truetype(font_path, 24)
            small_font = ImageFont.truetype(font_path, 18)
        except:
            # 폰트를 찾을 수 없는 경우 기본 폰트 사용
            title_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # 타이틀 그리기
        title = "객관식 응답 결과" if question_type.lower() == "객관식" else "단답형 응답 분석 결과"
        draw.text((width//2, 50), title, fill=(33, 33, 33), font=title_font, anchor="mm")
        
        if question_type.lower() == "객관식":
            # 객관식 응답 차트 (막대 그래프)
            counter = Counter(data)
            labels = list(counter.keys())
            values = list(counter.values())
            
            # 색상 설정
            colors = [(255, 99, 132), (54, 162, 235), (255, 206, 86), (75, 192, 192), (153, 102, 255)]
            
            # 막대 그래프 그리기
            max_value = max(values) if values else 0
            bar_width = 80
            bar_spacing = 40
            left_margin = 100
            bottom_margin = 100
            
            for i, (label, value) in enumerate(zip(labels, values)):
                # 막대 위치 계산
                x = left_margin + i * (bar_width + bar_spacing)
                bar_height = (value / max_value) * (height - 200) if max_value > 0 else 0
                y = height - bottom_margin - bar_height
                
                # 막대 그리기
                color = colors[i % len(colors)]
                draw.rectangle([x, y, x + bar_width, height - bottom_margin], fill=color)
                
                # 레이블 그리기
                draw.text((x + bar_width//2, height - bottom_margin + 20), label, fill=(33, 33, 33), font=normal_font, anchor="mt")
                
                # 값 그리기
                draw.text((x + bar_width//2, y - 10), str(value), fill=(33, 33, 33), font=normal_font, anchor="mb")
        
        elif question_type.lower() == "단답형":
            # 단답형 응답 분석
            labels, values = analyze_text_responses(data)
            
            if labels and values:
                # 막대 그래프 그리기 (수평)
                max_value = max(values)
                bar_height = 40
                bar_spacing = 20
                left_margin = 200
                top_margin = 150
                
                for i, (label, value) in enumerate(zip(labels, values)):
                    # 막대 위치 계산
                    y = top_margin + i * (bar_height + bar_spacing)
                    bar_width = (value / max_value) * (width - 300) if max_value > 0 else 0
                    
                    # 막대 그리기
                    color_value = 100 + (155 * i // len(labels))
                    color = (color_value, 100, 255 - color_value)
                    draw.rectangle([left_margin, y, left_margin + bar_width, y + bar_height], fill=color)
                    
                    # 레이블 그리기
                    draw.text((left_margin - 10, y + bar_height//2), label, fill=(33, 33, 33), font=normal_font, anchor="rm")
                    
                    # 값 그리기
                    draw.text((left_margin + bar_width + 10, y + bar_height//2), str(value), fill=(33, 33, 33), font=normal_font, anchor="lm")
            else:
                draw.text((width//2, height//2), "분석할 데이터가 충분하지 않습니다", fill=(100, 100, 100), font=normal_font, anchor="mm")
    
    except Exception as e:
        # 오류 메시지
        draw.text((width//2, height//2), f"차트 생성 오류: {str(e)}", fill=(255, 0, 0), font=normal_font, anchor="mm")
    
    # 이미지를 바이트 스트림으로 변환
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr

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
    
    # 레이아웃: 사이드바와 메인 컨텐츠
    col1, col2 = st.columns([1, 2])  # 1:2 비율로 분할
    
    # 왼쪽 컬럼: QR 코드 및 관리 옵션
    with col1:
        st.markdown("### 투표 참여 QR 코드")
        # QR 코드 크기 조절 슬라이더
        qr_size = st.slider("QR 코드 크기", min_value=5, max_value=20, value=15, step=1)
        
        qr_img = generate_qr_code(vote_app_url, qr_size)
        if qr_img:
            # QR 코드 표시 (크기 조절된)
            st.markdown(
                f'<div class="qr-container">'
                f'<img src="data:image/png;base64,{qr_img}" class="qr-image">'
                f'<p>QR 코드를 스캔하여 참여하세요</p>'
                f'</div>',
                unsafe_allow_html=True
            )
        
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
    
    # 오른쪽 컬럼: 결과 대시보드
    with col2:
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
                    # PIL로 이미지 생성 (한글 지원)
                    img_bytes = create_image_with_korean_text(current_responses, question_type)
                    st.image(img_bytes, use_column_width=True)
                    
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
                st.warning("현재 활성화된 질문이 없습니다. 왼쪽 패널에서 질문을 활성화해주세요.")

if __name__ == "__main__":
    main()
