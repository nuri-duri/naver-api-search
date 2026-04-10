import streamlit as st  # Streamlit 라이브러리 임포트
import pandas as pd  # 데이터 분석을 위한 Pandas 임포트
import plotly.express as px  # 시각화를 위한 Plotly Express 임포트
import plotly.graph_objects as go  # 상세 그래프 설정을 위한 Plotly Graph Objects 임포트
import os  # 운영체제 환경 변수 접근을 위한 os 임포트
import json  # JSON 데이터 처리를 위한 json 임포트
import urllib.request  # API 호출을 위한 urllib 임포트
import urllib.parse  # URL 인코딩을 위한 urllib.parse 임포트
from dotenv import load_dotenv  # .env 파일 로드를 위한 load_dotenv 임포트
from datetime import datetime, timedelta  # 날짜 처리를 위한 datetime 모듈 임포트
import re  # 정규표현식 처리를 위한 re 임포트
from collections import Counter  # 단어 빈도 계산을 위한 Counter 임포트
import io  # 입출력 처리를 위한 io 임포트

# 1. 환경 설정 및 API 클라이언트 정의
st.set_page_config(page_title="Naver 통합 분석 대시보드", layout="wide")  # 대시보드 페이지 설정 (와이드 레이아웃)
load_dotenv(dotenv_path="naver-api-search/.env")  # .env 파일에서 환경 변수 로드

NAVER_GREEN = "#03C75A"  # 네이버 브랜드 컬러 정의 (그린)

# API 인증 정보 로드 (Streamlit Secrets 우선, 로컬 환경변수/env 후순위)
# 배포 시 share.streamlit.io의 Settings > Secrets 메뉴에 아래 키값들을 입력해야 합니다.
CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID", os.environ.get("NAVER_CLIENT_ID"))  # 네이버 API Client ID 
CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET", os.environ.get("NAVER_CLIENT_SECRET"))  # 네이버 API Client Secret 

class RealtimeNaverCollector:  # 네이버 데이터 실시간 수집 클래스 정의
    def __init__(self, client_id, client_secret):  # 객체 생성 시 인증 정보 초기화
        self.client_id = client_id  # Client ID 저장
        self.client_secret = client_secret  # Client Secret 저장
        self.headers = {  # API 호출에 필요한 공통 헤더 설정
            "X-Naver-Client-Id": self.client_id,  # 인증용 ID 헤더
            "X-Naver-Client-Secret": self.client_secret,  # 인증용 Secret 헤더
            "Content-Type": "application/json"  # 데이터 타입 지정
        }

    def _call_api(self, url, method="GET", body=None):  # API 호출 공통 메서드
        request = urllib.request.Request(url)  # API 요청 객체 생성
        for key, value in self.headers.items():  # 헤더 정보 추가
            request.add_header(key, value)  # 헤더 한 줄씩 추가
        
        try:
            if method == "POST":  # POST 방식일 경우 처리
                data = json.dumps(body).encode("utf-8")  # 바디 데이터를 JSON 바이트로 변환
                response = urllib.request.urlopen(request, data=data)  # POST 요청 실행
            else:  # GET 방식일 경우 처리
                response = urllib.request.urlopen(request)  # GET 요청 실행
            
            rescode = response.getcode()  # 응답 코드 확인
            if rescode == 200:  # 성공(200)일 경우 처리
                return json.loads(response.read().decode('utf-8'))  # JSON 데이터 파싱 후 반환
            return None  # 실패 시 None 반환
        except Exception as e:  # 호출 중 오류 발생 시 처리
            st.error(f"API 호출 오류 ({url}): {e}")  # 화면에 에러 메시지 출력
            return None  # 에러 시 None 반환

    def fetch_trend(self, keywords, start_date, end_date):  # 통합 검색어 트렌드 수집 메서드
        """통합검색어 트렌드 수집"""
        url = "https://openapi.naver.com/v1/datalab/search"  # 데이터랩 검색 URL
        body = {  # API 요청 바디 구성
            "startDate": start_date, "endDate": end_date, "timeUnit": "date",  # 기간 및 일 단위 설정
            "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords]  # 키워드 그룹 설정
        }
        res = self._call_api(url, "POST", body)  # API 호출 (POST)
        if res:  # 결과가 있을 경우 처리
            dfs = []  # 데이터프레임 리스트 초기화
            for res_group in res['results']:  # 검색 그룹별 반복
                title = res_group['title']  # 키워드 그룹명
                if not res_group['data']: continue  # 데이터가 없으면 건너뜀
                df = pd.DataFrame(res_group['data'])  # 날짜별 수치 데이터프레임 생성
                df['keyword'] = title  # 키워드 컬럼 추가
                dfs.append(df)  # 리스트에 추가
            if dfs:  # 수집된 데이터가 있으면
                full_df = pd.concat(dfs, ignore_index=True)  # 모든 데이터프레임 합치기
                full_df['period'] = pd.to_datetime(full_df['period'])  # 날짜 형식 변환
                return full_df  # 결과 반환
        return pd.DataFrame()  # 결과 없으면 빈 데이터프레임 반환

    def fetch_shopping_insight(self, category_id, start_date, end_date):  # 쇼핑 인사이트 수집 메서드
        """쇼핑 인사이트 카테고리 클릭 트렌드 수집"""
        url = "https://openapi.naver.com/v1/datalab/shopping/categories"  # 쇼핑 카테고리 URL
        body = {  # API 요청 바디 구성
            "startDate": start_date, "endDate": end_date, "timeUnit": "date",  # 기간 및 일 단위 설정
            "category": [{"name": "디지털/가전", "param": [category_id]}]  # 분석 대상 카테고리 ID (리스트 형태 필수)
        }
        res = self._call_api(url, "POST", body)  # API 호출 (POST)
        if res:  # 결과가 있을 경우 처리
            dfs = []  # 데이터프레임 리스트 초기화
            for res_group in res['results']:  # 카테고리별 반복
                title = res_group['title']  # 카테고리명
                if not res_group['data']: continue  # 데이터가 없으면 건너뜀
                df = pd.DataFrame(res_group['data'])  # 날짜별 수치 데이터프레임 생성
                df['category_name'] = title  # 카테고리 컬럼 추가
                dfs.append(df)  # 리스트에 추가
            if dfs:  # 수집된 데이터가 있으면
                full_df = pd.concat(dfs, ignore_index=True)  # 모든 데이터프레임 합치기
                full_df['period'] = pd.to_datetime(full_df['period'])  # 날짜 형식 변환
                return full_df  # 결과 반환
        return pd.DataFrame()  # 결과 없으면 빈 데이터프레임 반환

    def fetch_search(self, keywords, categories, display=50):  # 통합 검색 결과 수집 메서드
        """통합 검색 결과 수집 (쇼핑, 블로그, 카페, 뉴스)"""
        results = []  # 결과 저장용 리스트 초기화
        for kw in keywords:  # 각 키워드별 반복
            for cat in categories:  # 각 카테고리(쇼핑, 블로그 등)별 반복
                if cat == 'shop': url = f"https://openapi.naver.com/v1/search/shop.json?query={urllib.parse.quote(kw)}&display={display}"  # 쇼핑 검색 URL
                elif cat == 'blog': url = f"https://openapi.naver.com/v1/search/blog.json?query={urllib.parse.quote(kw)}&display={display}"  # 블로그 검색 URL
                elif cat == 'cafe': url = f"https://openapi.naver.com/v1/search/cafearticle.json?query={urllib.parse.quote(kw)}&display={display}"  # 카페 검색 URL
                elif cat == 'news': url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(kw)}&display={display}"  # 뉴스 검색 URL
                
                res = self._call_api(url)  # API 호출 (GET)
                if res and 'items' in res:  # 결과 항목이 있으면
                    for item in res['items']:  # 각 항목 반복
                        item['category'] = cat  # 데이터 소스 구분 (shop, blog 등)
                        item['search_keyword'] = kw  # 검색한 키워드 태깅
                        results.append(item)  # 리스트에 추가
        return pd.DataFrame(results)  # 전체 결과를 데이터프레임으로 변환하여 반환

# 2. 사이드바 구성 및 필터 로직
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/0/09/Naver_Line_Logo.svg", width=50)  # 네이버 로고 표시
st.sidebar.title("🔍 실시간 분석 제어")  # 사이드바 제목

if not CLIENT_ID or not CLIENT_SECRET:  # API 키가 없을 경우 처리
    st.sidebar.error("API 키 미설정 (.env 파일을 확인하세요)")  # 에러 메시지 출력
    st.stop()  # 앱 실행 중지

# 키워드 및 기간 설정
kw_input = st.sidebar.text_input("분석 키워드 (쉼표 구분)", value="선풍기, 핫팩")  # 키워드 입력 필드
target_keywords = [k.strip() for k in kw_input.split(",") if k.strip()]  # 입력된 키워드 리스트화
date_range = st.sidebar.date_input("분석 기간", value=(datetime.now().date() - timedelta(days=90), datetime.now().date()))  # 날짜 범위 선택 위젯

# 분석 실행 버튼
if st.sidebar.button("실시간 분석 실행 🚀", use_container_width=True):  # 분석 시작 버튼
    with st.spinner("데이터를 수집하고 있습니다..."):  # 로딩 중 표시
        collector = RealtimeNaverCollector(CLIENT_ID, CLIENT_SECRET)  # 수집 엔진 초기화
        start_s, end_s = date_range[0].strftime("%Y-%m-%d"), date_range[1].strftime("%Y-%m-%d")  # 날짜 문자열 변환
        
        st.session_state.df_trend = collector.fetch_trend(target_keywords, start_s, end_s)  # 검색 트렌드 수집 및 세션 저장
        st.session_state.df_shop_trend = collector.fetch_shopping_insight("50000003", start_s, end_s) # 디지털/가전 카테고리 쇼핑 인사이트 수집
        st.session_state.df_search = collector.fetch_search(target_keywords, ['shop', 'blog', 'cafe', 'news'], display=50)  # 통합 검색 결과 수집
        st.session_state.update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 수집 완료 시간 기록

# 데이터 로드 확인
if 'df_trend' not in st.session_state or st.session_state.df_trend.empty:  # 데이터가 아직 수집되지 않았을 경우
    st.info("사이드바에서 키워드를 입력하고 분석을 실행해 주세요.")  # 안내 메시지 출력
    st.stop()  # 앱 실행 중지

# 보조 필터링 (사이드바 하단)
st.sidebar.divider()  # 구분선 추가
st.sidebar.subheader("🎯 데이터 세부 필터")  # 서브 헤더 추가
df_search_raw = st.session_state.df_search.copy()  # 수집된 원본 데이터 복사

# [핵심 수정] 가격(lprice) 컬럼을 수집 직후 전체 숫자형으로 일괄 변환 (TypeError 방지)
df_search_raw['lprice'] = pd.to_numeric(df_search_raw['lprice'], errors='coerce').fillna(0)

# 쇼핑 데이터 특화 필터
shop_full = df_search_raw[df_search_raw['category'] == 'shop'].copy()  # 쇼핑 카테고리만 별도 추출 (이미 lprice는 숫자형)
if not shop_full.empty:  # 쇼핑 데이터가 있을 경우
    max_p = int(shop_full['lprice'].max())  # 수집된 최고가 산출
    p_range = st.sidebar.slider("쇼핑 가격 필터 (원)", 0, max_p, (0, max_p))  # 가격 범위 슬라이더 제공
    brands = st.sidebar.multiselect("주요 브랜드 필터", options=shop_full['brand'].unique().tolist())  # 브랜드 선택 필터
    
    # 필터 적용용 데이터프레임 (이미 lprice가 숫자형이므로 .loc 할당 불필요)
    filtered_search = df_search_raw.copy()  
    
    # 필터링 조건 설정 (쇼핑 외 데이터는 유지하거나 가격/브랜드 필터링 적용)
    condition = (filtered_search['category'] != 'shop') | \
                ((filtered_search['lprice'] >= p_range[0]) & (filtered_search['lprice'] <= p_range[1]))  # 가격 조건
    if brands:  # 브랜드가 선택되었을 경우
        condition &= (filtered_search['category'] != 'shop') | (filtered_search['brand'].isin(brands))  # 브랜드 조건 추가
    filtered_search = filtered_search[condition]  # 최종 필터링된 데이터
else:  # 쇼핑 데이터가 없을 경우
    filtered_search = df_search_raw  # 원본 데이터 그대로 사용

# 3. 메인 콘텐츠 렌더링
st.title("🍀 Naver 실시간 통합 EDA 대시보드")  # 메인 제목
st.caption(f"⏱️ 마지막 분석 시간: {st.session_state.update_time}")  # 분석 시간 캡션 표시
st.markdown("---")  # 구분선

# 상단 핵심 메트릭 (주요 지표 요약 요약)
m1, m2, m3, m4 = st.columns(4)  # 4단 컬럼 구성
m1.metric("분석 키워드 수", f"{len(target_keywords)}개")  # 선택된 키워드 개수
m2.metric("검색 데이터 수", f"{len(st.session_state.df_trend)}건")  # 수집된 트렌드 데이터 수
m3.metric("콘텐츠 총계", f"{len(filtered_search)}건")  # 필터링된 총 콘텐츠 수
if not shop_full.empty:  # 쇼핑 데이터가 있는 경우 평균 가격 표시
    m4.metric("쇼핑 평균가", f"{filtered_search[filtered_search['category']=='shop']['lprice'].mean():,.0f}원")

# 탭 구성 (분석 주제별 6개 탭)
tabs = st.tabs(["📊 프로파일링", "📉 검색 트렌드", "🛍️ 쇼핑 인사이트", "🗺️ 범주 분석", "🔤 단어 분석", "📑 전체 데이터"])

# Tab 1: 데이터 프로파일링
with tabs[0]:  # 첫 번째 탭 섹션
    st.subheader("📋 실시간 수집 데이터 현황")  # 서브 헤더
    col1, col2 = st.columns(2)  # 2단 레이아웃
    with col1:  # 왼쪽 영역
        st.write("**수치형 데이터 통계**")  # 제목
        st.write(filtered_search.describe().T)  # 기술 통계량 출력 (행/열 전치)
    with col2:  # 오른쪽 영역
        st.write("**결측치 분석**")  # 제목
        null_df = filtered_search.isnull().sum().reset_index()  # 결측치 합계 계산
        null_df.columns = ['column', 'count']  # 컬럼명 재지정
        fig_null = px.bar(null_df[null_df['count']>0], x='column', y='count', color_discrete_sequence=[NAVER_GREEN])  # 결측치 바 차트
        st.plotly_chart(fig_null, use_container_width=True)  # 차트 렌더링
    
    st.markdown("---")  # 구분선
    st.write("**원본 데이터 미리보기**")  # 안내 문구
    st.dataframe(filtered_search.head(50), use_container_width=True)  # 상위 50개 데이터 조회용 테이블

# Tab 2: 통합검색 트렌드
with tabs[1]:  # 두 번째 탭 섹션
    st.subheader("📉 검색어 트렌드 분석")  # 제목
    fig_line = px.line(st.session_state.df_trend, x='period', y='ratio', color='keyword', 
                       title="일별 검색 점유율 추이", color_discrete_sequence=px.colors.qualitative.Safe)  # 검색 트렌드 라인 차트
    st.plotly_chart(fig_line, use_container_width=True)  # 차워 렌더링
    
    st.write("**트렌드 데이터 상세**")  # 데이터 테이블 제목
    st.dataframe(st.session_state.df_trend, use_container_width=True)  # 트렌드 원본 데이터 테이블

# Tab 3: 쇼핑 인사이트
with tabs[2]:  # 세 번째 탭 섹션
    st.subheader("🛍️ 쇼핑 클릭 트렌드 (디지털/가전)")  # 제목
    if not st.session_state.df_shop_trend.empty:  # 데이터가 있을 경우
        fig_shop = px.line(st.session_state.df_shop_trend, x='period', y='ratio', color='category_name',
                           title="카테고리 내 클릭 트렌드", color_discrete_sequence=[NAVER_GREEN])  # 쇼핑 인사이트 차트
        st.plotly_chart(fig_shop, use_container_width=True)  # 차트 렌더링
        st.write("**쇼핑 트렌드 데이터 상세**")  # 제목
        st.dataframe(st.session_state.df_shop_trend, use_container_width=True)  # 데이터 테이블 출력
    else:  # 데이터가 없을 경우
        st.warning("쇼핑 트렌드 데이터를 수집할 수 없습니다.")  # 경고 메시지

# Tab 4: 플랫폼/카테고리 분석 (TreeMap/Sunburst)
with tabs[3]:  # 네 번째 탭 섹션
    st.subheader("🗺️ 범주형 계층 분석")  # 제목
    col3, col4 = st.columns(2)  # 2단 레이아웃
    shop_data = filtered_search[filtered_search['category'] == 'shop'].copy()  # 쇼핑 데이터만 복제
    
    with col3:  # 왼쪽 영역 (TreeMap)
        st.write("**쇼핑 카테고리 트리맵 (TreeMap)**")  # 제목
        if not shop_data.empty:  # 쇼핑 데이터가 있을 경우
            fig_tree = px.treemap(shop_data, path=['search_keyword', 'category1', 'category2'], values='lprice',
                                 color='category1', color_discrete_sequence=px.colors.qualitative.Pastel)  # 트리맵 생성
            st.plotly_chart(fig_tree, use_container_width=True)  # 차트 렌더링
        else: st.info("쇼핑 데이터가 필터링되었습니다.")  # 안내 문구
        
    with col4:  # 오른쪽 영역 (Sunburst)
        st.write("**플랫폼 점유율 선버스트 (Sunburst)**")  # 제목
        fig_sun = px.sunburst(filtered_search, path=['category', 'search_keyword'], 
                             color='category', color_discrete_sequence=px.colors.qualitative.Set3)  # 선버스트 차트 생성
        st.plotly_chart(fig_sun, use_container_width=True)  # 차트 렌더링
        
    st.write("**플랫폼/카테고리 요약 데이터**")  # 요약 테이블 제목
    st.dataframe(filtered_search[['category', 'search_keyword', 'category1', 'category2']].value_counts().reset_index(), use_container_width=True)  # 통계 테이블 출력

# Tab 5: 핵심 키워드 분석
with tabs[4]:  # 다섯 번째 탭 섹션
    st.subheader("🔤 제목 데이터 빈도 분석 (상위 30개)")  # 제목
    all_titles = " ".join(filtered_search['title'].astype(str).tolist())  # 모든 제목 텍스트 결합
    clean_text = re.sub(r'<[^>]+>|&[^;]+;|[^가-힣a-zA-Z0-9\s]', '', all_titles)  # HTML 태그 및 특수문자 제거 정칙화
    words = [w for w in clean_text.split() if len(w) > 1]  # 두 글자 이상 단어만 추출
    stop_ws = ["추천", "구매", "판매", "공구", "후기", "네이버", "쇼핑", "기획", "세트"] + target_keywords  # 무의미한 불용어 도는 검색어 제거
    final_words = [w for w in words if w not in stop_ws]  # 불용어 필터링 적용된 최종 단어 리스트
    
    top_30 = Counter(final_words).most_common(30)  # 상위 30개 단어 빈도 산출
    if top_30:  # 분석된 데이터가 있으면
        word_df = pd.DataFrame(top_30, columns=['단어', '빈도'])  # 데이터프레임 생성
        fig_word = px.bar(word_df, x='빈도', y='단어', orientation='h', color='빈도', color_continuous_scale='Greens')  # 수평 바 차트
        fig_word.update_layout(yaxis={'categoryorder':'total ascending'})  # 빈도수 순 정렬
        st.plotly_chart(fig_word, use_container_width=True)  # 차트 렌더링
        st.write("**키워드 빈도 데이터 상세**")  # 제목
        st.dataframe(word_df, use_container_width=True)  # 통계 테이블 출력
    else: st.warning("분석할 텍스트가 부족합니다.")  # 경고 메시지

# Tab 6: 전체 데이터 조회
with tabs[5]:  # 여섯 번째 탭 섹션
    st.subheader("📑 필터링된 전체 데이터")  # 제목
    # pyarrow 호환을 위한 타입 변환 (렌더링 에러 방지)
    display_df = filtered_search.copy()  # 표시용 데이터 복사
    for col in display_df.columns:  # 각 컬럼 반복
        if display_df[col].dtype == 'object': display_df[col] = display_df[col].astype(str)  # 객체 타입 컬럼을 명확하게 문자열로 변환
        
    st.dataframe(display_df, height=600, use_container_width=True)  # 전체 필터링 데이터 조회용 테이블 출력
    st.download_button("📥 데이터 다운로드 (CSV)", data=display_df.to_csv(index=False, encoding='utf-8-sig'), 
                       file_name=f"naver_eda_{datetime.now().strftime('%Y%j%H%M')}.csv", mime="text/csv")  # CSV 다운로드 버튼 제공

st.markdown("---")  # 구분선
st.caption("© 2026 Antigravity Data Lab | Naver Open API 기반 분석 도구")  # 대시보드 저작권 정보 캡션
