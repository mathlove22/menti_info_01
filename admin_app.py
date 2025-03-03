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
import datetime

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
        try:
            worksheet = sheet.worksheet("질문")
            data = worksheet.get_all_records()
            return data
        except Exception as e:
            st.error(f"질문 워크시트 접근 오류: {str(e)}")
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
        try:
            worksheet = sheet.worksheet("응답")
            data = worksheet.get_all_records()
            return data
        except Exception as e:
            st.error(f"응답 워크시트 접근 오류: {str(e)}")
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
        worksheet = sheet.worksheet("질문")
        
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
            
            st.error(f"질문 ID '{question_id}'를 찾을 수 없습니다.")
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
        return None
    
    # 단어 분리 및 빈도 계산
    words = []
    for response in responses:
        # 문장을 단어로 분리 (한글, 영문, 숫자 포함)
        text_words = re.findall(r'\b[\w가-힣]+\b', response.lower())
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
        return None
    
    # 시각화용 데이터 준비
    labels = [word for word, _ in top_words]
    values = [count for _, count in top_words]
    
    return labels, values

# 차트 생성 함수
def create_chart(data, question_type):
    if not data:
        return None
    
    try:
        plt.figure(figsize=(10, 6))
        
        if question_type.lower() == "객관식":
            # 객관식 응답 차트 (막대 그래프)
            counter = Counter(data)
            labels = list(counter.keys())
            values = list(counter.values())
            
            # 한글 폰트 설정
            plt.rc('font', family='DejaVu Sans')
            
            bars = plt.bar(range(len(labels)), values, color='#5DA5DA')
            
            # 각 막대 위에 값 표시
            for i, bar in enumerate(bars):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{height}', ha='center', va='bottom')
            
            plt.ylabel('응답 수')
            plt.title('객관식 응답 결과')
            plt.xticks(range(len(labels)), labels, rotation=45, ha='right')
            plt.tight_layout()
            
        elif question_type.lower() == "단답형":
            # 단답형 응답 분석 및 시각화
            result = analyze_text_responses(data)
            if result:
                labels, values = result
                
                # 한글 폰트 설정
                plt.rc('font', family='DejaVu Sans')
                
                # 수평 막대 그래프로 표시 (빈도 높은 순)
                bars = plt.barh(range(len(labels)), values, color='#5DA5DA')
                
                # 각 막대 옆에 값 표시
                for i, bar in enumerate(bars):
                    width = bar.get_width()
                    plt.text(width + 0.1, bar.get_y() + bar.get_height()/2.,
                            f'{width}', ha='left', va='center')
                
                plt.xlabel('빈도')
                plt.title('단답형 응답 분석 결과')
                plt.yticks(range(len(labels)), labels)
                plt.tight_layout()
            else:
                plt.text(0.5, 0.5, '분석할 데이터가 충분하지 않습니다', 
                       ha='center', va='center', fontsize=12)
                plt.axis('off')
        
        return plt
    except Exception as e:
        st.error(f"차트 생성 중 오류: {str(e)}")
        return None

# 메인 앱
def main():
    st.markdown('<div class="title">실시간 투표 관리자 대시보드</div>', unsafe_allow_html=True)
    
    # 구글 시트 ID (secrets에서 가져오기)
    sheet_id = st.secrets.get("general", {}).get("sheet_id", "1DeLOnDJ4KdtZfKwEMAnYWqINTKx7vv22c3SQCu6lxQY")
    
    # 투표 앱 URL - 배포 후 실제 URL로 변경 필요
    # 예시: https://mentiinfo01-vote-jqg6tgae4s6aorcxpvvxmq.streamlit.app/
    vote_app_url = "https://your-vote-app-url.streamlit.app"  
    
    # 자동 새로고침 설정
    auto_refresh = st.sidebar.checkbox("자동 새로고침", value=True)
    refresh_interval = st.sidebar.slider("새로고침 간격(초)", min_value=3, max_value=60, value=10)
    
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
        
        # 질문 데이터 로드
        questions = load_questions(sheet_id)
        
        if not questions:
            st.warning("질문 데이터가 없습니다. 시트 초기화를 진행해주세요.")
            
            # 시트 초기화 버튼
            if st.button("시트 초기화 (샘플 질문 추가)", use_container_width=True):
                try:
                    client = get_gsheet_connection()
                    if not client:
                        st.error("구글 시트 연결에 실패했습니다.")
                        return
                        
                    sheet = client.open_by_key(sheet_id)
                    
                    # 시트1 초기화 (질문)
                    try:
                        worksheet = sheet.worksheet("질문")
                    except:
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
                    try:
                        response_ws = sheet.worksheet("응답")
                    except:
                        response_ws = sheet.add_worksheet(title="응답", rows=1, cols=6)
                    
                    response_ws.clear()
                    response_headers = ["시간", "학번", "이름", "질문ID", "응답", "세션ID"]
                    response_ws.append_row(response_headers)
                    
                    st.success("시트가 초기화되었습니다. 샘플 질문이 추가되었습니다.")
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
                    st.experimental_rerun()
            
            if st.button("모든 질문 비활성화", use_container_width=True):
                success = True
                for q in questions:
                    if q.get("활성화", "").lower() in ["y", "yes"]:
                        if not update_question_status(sheet_id, q.get("질문ID"), False):
                            success = False
                if success:
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
            question_type = active_q.get("유형", "")
            
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
                chart = create_chart(current_responses, question_type)
                if chart:
                    st.pyplot(chart)
                
                # 원시 데이터 표시
                with st.expander("원시 응답 데이터"):
                    # 응답 데이터를 테이블로 표시
                    filtered_responses = [r for r in responses if r.get("질문ID") == active_q_id]
                    df = pd.DataFrame(filtered_responses)
                    st.dataframe(df)
            else:
                st.info("아직 이 질문에 대한 응답이 없습니다.")
        
        else:
            st.warning("현재 활성화된 질문이 없습니다. 사이드바에서 질문을 활성화해주세요.")
    
    # 자동 새로고침
    if auto_refresh:
        time.sleep(refresh_interval)
        st.experimental_rerun()

if __name__ == "__main__":
    main()
