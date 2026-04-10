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
st.set_page_config(page_title="Naver Market Intel Dashboard", layout="wide", page_icon="🍀")
load_dotenv(dotenv_path="naver-api-search/.env")

# 디자인 시스템 상수 정의
NAVER_GREEN = "#2DB400"  # 네이버 브랜드 그린 (분석 결과 반영)
BG_COLOR = "#F0F2F6"      # 스트림릿 기본 배경색

# API 인증 정보 로드 (Streamlit Secrets 우선, 로컬 환경변수/env 후순위)
CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID", os.environ.get("NAVER_CLIENT_ID"))
CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET", os.environ.get("NAVER_CLIENT_SECRET"))

# --- 커스텀 CSS 주입 (Premium UI) ---
st.markdown(f"""
    <style>
    /* 메인 배경 및 레이아웃 */
    .stApp {{
        background-color: white;
    }}
    /* 사이드바 커스텀 헤더 */
    [data-testid="stSidebar"] {{
        background-color: #f8f9fa;
    }}
    .sidebar-header {{
        background-color: {NAVER_GREEN};
        padding: 20px;
        border-radius: 0 0 15px 15px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        font-weight: bold;
        font-size: 1.2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    /* 메트릭 카드 디자인 */
    div[data-testid="stMetric"] {{
        background-color: white;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        text-align: center;
    }}
    div[data-testid="stMetricLabel"] > div {{
        color: #666 !important;
        font-size: 0.9rem !important;
        justify-content: center !important;
    }}
    div[data-testid="stMetricValue"] > div {{
        color: {NAVER_GREEN} !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }}
    /* 탭 디자인 개선 */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 45px;
        background-color: #f1f3f5;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #495057;
        font-weight: 500;
        border: none;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: white !important;
        color: {NAVER_GREEN} !important;
        border-bottom: 3px solid {NAVER_GREEN} !important;
        font-weight: 700 !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 2. 데이터 수집 클래스 (인증 및 호출 로직)
class RealtimeNaverCollector:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "Content-Type": "application/json"
        }

    def _call_api(self, url, method="GET", body=None):
        request = urllib.request.Request(url)
        for key, value in self.headers.items():
            request.add_header(key, value)
        try:
            if method == "POST":
                data = json.dumps(body).encode("utf-8")
                response = urllib.request.urlopen(request, data=data)
            else:
                response = urllib.request.urlopen(request)
            if response.getcode() == 200:
                return json.loads(response.read().decode('utf-8'))
            return None
        except Exception as e:
            st.error(f"API 호출 오류: {e}")
            return None

    def fetch_trend(self, keywords, start_date, end_date):
        url = "https://openapi.naver.com/v1/datalab/search"
        body = {
            "startDate": start_date, "endDate": end_date, "timeUnit": "date",
            "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords]
        }
        res = self._call_api(url, "POST", body)
        if res:
            dfs = []
            for res_group in res['results']:
                if not res_group['data']: continue
                df = pd.DataFrame(res_group['data'])
                df['keyword'] = res_group['title']
                dfs.append(df)
            if dfs:
                full_df = pd.concat(dfs, ignore_index=True)
                full_df['period'] = pd.to_datetime(full_df['period'])
                return full_df
        return pd.DataFrame()

    def fetch_shopping_insight(self, category_id, start_date, end_date):
        url = "https://openapi.naver.com/v1/datalab/shopping/categories"
        body = {
            "startDate": start_date, "endDate": end_date, "timeUnit": "date",
            "category": [{"name": "분석 카테고리", "param": [category_id]}]
        }
        res = self._call_api(url, "POST", body)
        if res:
            dfs = []
            for res_group in res['results']:
                if not res_group['data']: continue
                df = pd.DataFrame(res_group['data'])
                df['category_name'] = res_group['title']
                dfs.append(df)
            if dfs:
                full_df = pd.concat(dfs, ignore_index=True)
                full_df['period'] = pd.to_datetime(full_df['period'])
                return full_df
        return pd.DataFrame()

    def fetch_search(self, keywords, categories, display=50):
        results = []
        for kw in keywords:
            for cat in categories:
                if cat == 'shop': url = f"https://openapi.naver.com/v1/search/shop.json?query={urllib.parse.quote(kw)}&display={display}"
                elif cat == 'blog': url = f"https://openapi.naver.com/v1/search/blog.json?query={urllib.parse.quote(kw)}&display={display}"
                elif cat == 'cafe': url = f"https://openapi.naver.com/v1/search/cafearticle.json?query={urllib.parse.quote(kw)}&display={display}"
                elif cat == 'news': url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(kw)}&display={display}"
                res = self._call_api(url)
                if res and 'items' in res:
                    for item in res['items']:
                        item['category_src'] = cat
                        item['search_keyword'] = kw
                        results.append(item)
        return pd.DataFrame(results)

# --- 사이드바 영역 ---
with st.sidebar:
    st.markdown('<div class="sidebar-header">🍀 NAVER Market Intel</div>', unsafe_allow_html=True)
    
    if not CLIENT_ID or not CLIENT_SECRET:
        st.error("🔒 API 키가 유효하지 않습니다.")
        st.stop()
        
    kw_input = st.text_input("🔍 분석 키워드 (쉼표 구분)", value="선풍기, 핫팩")
    target_keywords = [k.strip() for k in kw_input.split(",") if k.strip()]
    date_range = st.date_input("📅 분석 기간", value=(datetime.now().date() - timedelta(days=90), datetime.now().date()))
    
    st.markdown("---")
    if st.button("🚀 실시간 인텔리전스 분석 시작", use_container_width=True):
        with st.spinner("네이버 데이터 수집 중..."):
            collector = RealtimeNaverCollector(CLIENT_ID, CLIENT_SECRET)
            start_s, end_s = date_range[0].strftime("%Y-%m-%d"), date_range[1].strftime("%Y-%m-%d")
            
            st.session_state.df_trend = collector.fetch_trend(target_keywords, start_s, end_s)
            st.session_state.df_shop_trend = collector.fetch_shopping_insight("50000003", start_s, end_s)
            st.session_state.df_search = collector.fetch_search(target_keywords, ['shop', 'blog', 'cafe', 'news'], display=50)
            st.session_state.update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 데이터 로드 확인
if 'df_trend' not in st.session_state or st.session_state.df_trend.empty:
    st.info("👈 사이드바에서 키워드를 입력하고 분석 버튼을 클릭하세요.")
    st.stop()

# 보조 필터링
st.sidebar.subheader("🎯 상세 필터링")
df_search_raw = st.session_state.df_search.copy()
# lprice 안전 변환
df_search_raw['lprice'] = pd.to_numeric(df_search_raw['lprice'], errors='coerce').fillna(0)

shop_only = df_search_raw[df_search_raw['category_src'] == 'shop'].copy()
if not shop_only.empty:
    max_p = int(shop_only['lprice'].max())
    p_range = st.sidebar.slider("💰 쇼핑 가격 범위", 0, max_p, (0, max_p))
    brands = st.sidebar.multiselect("🏷️ 주요 브랜드 선택", options=shop_only['brand'].unique().tolist())
    
    mask = (df_search_raw['category_src'] != 'shop') | \
           ((df_search_raw['lprice'] >= p_range[0]) & (df_search_raw['lprice'] <= p_range[1]))
    if brands:
        mask &= (df_search_raw['category_src'] != 'shop') | (df_search_raw['brand'].isin(brands))
    filtered_df = df_search_raw[mask]
else:
    filtered_df = df_search_raw

# --- 메인 대시보드 영역 ---
st.title("🍀 Naver Market Intel Dashboard")
st.caption(f"Last updated: {st.session_state.update_time}")

# 상단 하이라이트 지표 카드
m1, m2, m3, m4 = st.columns(4)
m1.metric("트렌드 데이터 수", f"{len(st.session_state.df_trend)}건")
m2.metric("분석 키워드", f"{len(target_keywords)}개")
m3.metric("필터링된 콘텐츠", f"{len(filtered_df)}건")
if not shop_only.empty:
    m4.metric("쇼핑 평균가", f"{filtered_df[filtered_df['category_src']=='shop']['lprice'].mean():,.0f}원")

st.markdown("<br>", unsafe_allow_html=True)

# 참조 사이트 기반 탭 구성
tabs = st.tabs(["📉 데이터 프로파일링", "📊 트렌드 분석", "🛍️ 쇼핑 상세", "💬 소셜 인사이트", "📂 데이터 탐색"])

# Tab 1: 데이터 프로파일링
with tabs[0]:
    st.subheader("📋 수집 데이터 현황 요약")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**기초 통계량 (수치형)**")
        st.dataframe(filtered_df.describe().T, use_container_width=True)
    with col_b:
        st.write("**플랫폼별 데이터 분포**")
        df_dist = filtered_df['category_src'].value_counts().reset_index()
        df_dist.columns = ['Platform', 'Count']
        fig_dist = px.pie(df_dist, values='Count', names='Platform', hole=0.4, 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    st.markdown("---")
    st.write("**실시간 수집 샘플 (TOP 20)**")
    st.dataframe(filtered_df.head(20), use_container_width=True)

# Tab 2: 트렌드 분석
with tabs[1]:
    st.subheader("📉 검색어 트렌드 추이")
    fig_trend = px.line(st.session_state.df_trend, x='period', y='ratio', color='keyword',
                       title="일일 검색량 상대 비율", markers=True,
                       color_discrete_sequence=px.colors.qualitative.Bold)
    fig_trend.update_layout(plot_bgcolor="white", xaxis_gridcolor="#eee", yaxis_gridcolor="#eee")
    st.plotly_chart(fig_trend, use_container_width=True)
    
    st.markdown("---")
    st.write("**📊 트렌드 상세 수치**")
    st.dataframe(st.session_state.df_trend, use_container_width=True)

# Tab 3: 쇼핑 상세
with tabs[2]:
    st.subheader("🛍️ 쇼핑 카테고리 입체 분석")
    shop_data = filtered_df[filtered_df['category_src'] == 'shop'].copy()
    if not shop_data.empty:
        col_c, col_d = st.columns(2)
        with col_c:
            st.write("**계층 구조 분석 (TreeMap)**")
            fig_tree = px.treemap(shop_data, path=['search_keyword', 'category1', 'category2'], 
                                 values='lprice', color='category1',
                                 color_discrete_sequence=px.colors.qualitative.Vivid)
            st.plotly_chart(fig_tree, use_container_width=True)
        with col_d:
            st.write("**비중 상세 분석 (Sunburst)**")
            fig_sun = px.sunburst(shop_data, path=['category1', 'category2', 'search_keyword'],
                                 color='category1', color_discrete_sequence=px.colors.qualitative.Vivid)
            st.plotly_chart(fig_sun, use_container_width=True)
        
        st.markdown("---")
        st.write("**💰 쇼핑 데이터 요약**")
        shop_sum = shop_data.groupby(['search_keyword', 'brand'])['lprice'].agg(['count', 'mean', 'max']).reset_index()
        st.dataframe(shop_sum, use_container_width=True)
    else:
        st.warning("쇼핑 데이터가 존재하지 않습니다.")

# Tab 4: 소셜 인사이트
with tabs[3]:
    st.subheader("💬 제목 텍스트 마이닝 인사이트")
    all_titles = " ".join(filtered_df['title'].astype(str).tolist())
    # 정규표현식 클리닝 (HTML 태그 및 기호 제거)
    clean_text = re.sub(r'<[^>]+>|&[^;]+;|[^가-힣a-zA-Z0-9\s]', '', all_titles)
    words = [w for w in clean_text.split() if len(w) > 1]
    stop_words = ["추천", "네이버", "쇼핑", "구매", "판매", "세트", "후기"] + target_keywords
    final_words = [w for w in words if w not in stop_words]
    
    word_counts = Counter(final_words).most_common(30)
    if word_counts:
        word_df = pd.DataFrame(word_counts, columns=['Keyword', 'Frequency'])
        fig_word = px.bar(word_df, x='Frequency', y='Keyword', orientation='h',
                         color='Frequency', color_continuous_scale='Greens',
                         title="상위 30개 핵심 키워드 빈도")
        fig_word.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_word, use_container_width=True)
        
        st.markdown("---")
        st.write("**🔤 키워드 빈도 상세**")
        st.dataframe(word_df, use_container_width=True)
    else:
        st.info("분석할 결과가 부족합니다.")

# Tab 5: 데이터 탐색
with tabs[4]:
    st.subheader("📂 엑스포트용 전체 데이터")
    # Arrow 호환 타입 변환
    display_df = filtered_df.copy()
    for col in display_df.columns:
        if display_df[col].dtype == 'object': display_df[col] = display_df[col].astype(str)
    
    st.dataframe(display_df, height=600, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button("📥 전체 분석 데이터 다운로드 (CSV)", data=csv, 
                       file_name=f"naver_market_intel_{datetime.now().strftime('%Y%j%H%M')}.csv",
                       mime="text/csv", use_container_width=True)

st.divider()
st.caption("© 2026 Antigravity Data Lab | Powered by Naver Open API")
