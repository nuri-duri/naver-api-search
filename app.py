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
    st.markdown("### 📋 데이터 수집 현황 및 프로파일링")
    
    # [사진 가이드] 상단 메트릭 카드 3종
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric("트렌드 데이터 수", f"{len(st.session_state.df_trend)}건")
    with m_col2:
        st.metric("검색/쇼핑 데이터 수", f"{len(filtered_df)}건")
    with m_col3:
        # 마지막 업데이트 시간에서 시간만 추출
        up_time = st.session_state.update_time.split(" ")[1] if " " in st.session_state.update_time else st.session_state.update_time
        st.metric("최종 업데이트", up_time)
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # [사진 가이드] 데이터 요약 섹션 (좌: 트렌드, 우: 검색/쇼핑)
    d_col1, d_col2 = st.columns([1, 1.2]) # 좌우 너비 비율 조정
    
    with d_col1:
        st.markdown("#### 📉 트렌드 데이터 요약")
        # 데이터 정리: 컬럼명 변경 및 선택
        trend_summary = st.session_state.df_trend[['period', 'keyword', 'ratio']].copy()
        trend_summary.columns = ['날짜', '키워드', '검색량']
        trend_summary['날짜'] = trend_summary['날짜'].dt.strftime('%Y-%m-%d')
        st.dataframe(trend_summary.head(100), use_container_width=True, height=450)
        
    with d_col2:
        st.markdown("#### 🛍️ 검색/쇼핑 데이터 요약")
        # 데이터 정리: 컬럼명 변경 및 선택
        search_summary = filtered_df[['search_keyword', 'category_src', 'title']].copy()
        search_summary.columns = ['키워드', '구분', '제목']
        # 제목의 HTML 태그 제거 (정리)
        search_summary['제목'] = search_summary['제목'].apply(lambda x: re.sub(r'<[^>]+>|&[^;]+;', '', str(x)))
        st.dataframe(search_summary.head(100), use_container_width=True, height=450)

# Tab 2: 트렌드 분석
with tabs[1]:
    st.markdown("### 📈 네이버 검색어 및 쇼핑 트렌드 통합 분석")
    fig_trend = px.line(st.session_state.df_trend, x='period', y='ratio', color='keyword',
                       title="일별 검색 클릭 트렌드 (상대 수치)", markers=True,
                       color_discrete_sequence=px.colors.qualitative.Bold)
    fig_trend.update_layout(plot_bgcolor="white", xaxis_gridcolor="#eee", yaxis_gridcolor="#eee",
                            xaxis_title="날짜", yaxis_title="검색량")
    st.plotly_chart(fig_trend, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # [사진 가이드] 통계 요약표 추가
    st.markdown("### [통계 요약표]")
    # 키워드별 통계 계산
    trend_stats = st.session_state.df_trend.groupby('keyword')['ratio'].agg(['mean', 'max', 'min']).reset_index()
    trend_stats.columns = ['키워드', 'mean', 'max', 'min']
    # 소수점 정리 및 인덱스 설정
    trend_stats = trend_stats.set_index('키워드')
    st.dataframe(trend_stats.style.format("{:.4f}"), use_container_width=True)
    
    st.markdown("---")
    st.write("**📊 트렌드 상세 수치**")
    st.dataframe(st.session_state.df_trend, use_container_width=True)

# Tab 3: 쇼핑 상세
with tabs[2]:
    st.markdown("### 🛍️ 쇼핑 데이터 심층 분석")
    shop_data = filtered_df[filtered_df['category_src'] == 'shop'].copy()
    
    if not shop_data.empty:
        col_c, col_d = st.columns(2)
        
        with col_c:
            # [사진 가이드] 상품 최저가 분포 (Box Plot)
            st.markdown("#### 상품 최저가 분포 (Box Plot)")
            fig_box = px.box(shop_data, x='search_keyword', y='lprice', color='search_keyword',
                            points='all', title=None,
                            labels={'search_keyword': '키워드', 'lprice': '최저가'},
                            color_discrete_sequence=px.colors.qualitative.Safe)
            fig_box.update_layout(showlegend=False, plot_bgcolor="white", yaxis_gridcolor="#eee")
            st.plotly_chart(fig_box, use_container_width=True)
            
        with col_d:
            # [사진 가이드] 상위 브랜드별 평균가 및 등록 상품 수
            st.markdown("#### 상위 브랜드별 평균가 및 등록 상품 수")
            # 브랜드별 집계 (상위 15개)
            brand_stats = shop_data.groupby('brand')['lprice'].agg(['mean', 'count']).reset_index()
            brand_stats.columns = ['브랜드', '평균가', '상품수']
            brand_stats = brand_stats.sort_values('평균가', ascending=True).tail(15)
            
            fig_brand = px.bar(brand_stats, x='평균가', y='브랜드', color='상품수',
                              orientation='h', title=None,
                              color_continuous_scale='Blues',
                              labels={'평균가': '평균 가격', '브랜드': '브랜드명', '상품수': '등록 상품 수'})
            fig_brand.update_layout(plot_bgcolor="white", xaxis_gridcolor="#eee")
            st.plotly_chart(fig_brand, use_container_width=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # [사진 가이드] 쇼핑 상세 데이터 테이블
        st.markdown("### [쇼핑 상세 데이터]")
        # 데이터 정리 및 한글 컬럼명 매핑
        shop_display = shop_data[['search_keyword', 'title', 'lprice', 'brand', 'mallName', 'category1']].copy()
        shop_display.columns = ['키워드', '제목', '최저가', '브랜드', '몰이름', '카테고리']
        # 제목 클리닝
        shop_display['제목'] = shop_display['제목'].apply(lambda x: re.sub(r'<[^>]+>|&[^;]+;', '', str(x)))
        st.dataframe(shop_display, use_container_width=True, height=500)
    else:
        st.warning("분석할 쇼핑 데이터가 존재하지 않습니다.")

# Tab 4: 소셜 인사이트
with tabs[3]:
    st.markdown("### 💬 소셜 미디어 인텔리전스 분석")
    
    # [사진 가이드] 상단 구성을 좌측 차트와 우측 리스트로 분할
    s_col1, s_col2 = st.columns([1, 1.5])
    
    # 소셜 데이터 필터링 (blog, cafe, news)
    social_df = filtered_df[filtered_df['category_src'].isin(['blog', 'cafe', 'news'])].copy()
    
    with s_col1:
        # [사진 가이드] 채널별 게시물 점유율 (도넛 차트)
        st.markdown("#### 채널별 게시물 점유율")
        if not social_df.empty:
            dist_data = social_df['category_src'].value_counts().reset_index()
            dist_data.columns = ['구분', '게시물수']
            fig_pie = px.pie(dist_data, values='게시물수', names='구분', hole=0.5,
                            color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("소셜 데이터가 부족합니다.")
            
    with s_col2:
        # [사진 가이드] 최신 소셜 콘텐츠 리스트
        st.markdown("#### 최신 소셜 콘텐츠 리스트")
        if not social_df.empty:
            # 콘텐츠 리스트 정리
            display_social = social_df[['category_src', 'search_keyword', 'title', 'postdate', 'link']].copy()
            # 네이버 API 날짜 데이터가 없으면 오늘 날짜 등으로 대체하거나 있는 컬럼명 확인 필요 (보통 postdate 또는 pubDate)
            # 여기서는 postdate가 있다고 가정하고 정리
            if 'postdate' in display_social.columns:
                display_social.columns = ['구분', '키워드', '제목', '날짜', '링크']
            elif 'pubDate' in display_social.columns:
                display_social.columns = ['구분', '키워드', '제목', '날짜', '링크']
            
            # 제목 클리닝
            display_social['제목'] = display_social['제목'].apply(lambda x: re.sub(r'<[^>]+>|&[^;]+;', '', str(x)))
            st.dataframe(display_social.head(50), use_container_width=True, height=400)
        else:
            st.info("표시할 콘텐츠가 없습니다.")

    st.markdown("---")
    
    # 기존 키워드 빈도 분석 (하단 배치 유지 및 고도화)
    st.subheader("🔤 핵심 키워드 빈도 분석 (상위 30개)")
    all_titles = " ".join(social_df['title'].astype(str).tolist())
    clean_text = re.sub(r'<[^>]+>|&[^;]+;|[^가-힣a-zA-Z0-9\s]', '', all_titles)
    words = [w for w in clean_text.split() if len(w) > 1]
    stop_ws = ["추천", "네이버", "쇼핑", "구매", "판매", "세트", "후기"] + target_keywords
    final_words = [w for w in words if w not in stop_ws]
    
    top_30 = Counter(final_words).most_common(30)
    if top_30:
        word_df = pd.DataFrame(top_30, columns=['단어', '빈도'])
        fig_bar = px.bar(word_df, x='빈도', y='단어', orientation='h', 
                        color='빈도', color_continuous_scale='Greens')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("키워드 분석을 위한 충분한 텍스트 데이터가 없습니다.")

# Tab 5: 데이터 탐색
with tabs[4]:
    st.markdown("### 📂 엑스포트용 통합 데이터 마켓")
    st.write("분석에 사용된 전체 로우 데이터를 탐색하고 외부 파일로 추출할 수 있습니다.")
    
    # Arrow 호환 타입 변환 및 정리
    display_df = filtered_df.copy()
    # 컬럼명 가독성 개선
    display_df = display_df.rename(columns={
        'category_src': '플랫폼',
        'search_keyword': '검색어',
        'title': '제목',
        'lprice': '최저가',
        'brand': '브랜드',
        'mallName': '판매처',
        'link': '링크'
    })
    
    # 제목 내 HTML 태그 제거
    display_df['제목'] = display_df['제목'].apply(lambda x: re.sub(r'<[^>]+>|&[^;]+;', '', str(x)))
    
    for col in display_df.columns:
        if display_df[col].dtype == 'object': display_df[col] = display_df[col].astype(str)
    
    # 데이터 프리뷰
    st.dataframe(display_df, height=600, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    # 다운로드 섹션 프리미엄 입히기
    d_col1, d_col2 = st.columns([1, 1])
    with d_col1:
        st.info("💡 데이터 분석을 마쳤다면 아래 버튼을 눌러 로우 데이터를 저장하세요.")
    with d_col2:
        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 엑셀용 데이터 다운로드 (CSV)",
            data=csv,
            file_name=f"naver_market_intel_full_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

st.divider()
st.caption("🍀 Naver Market Intelligence Dashboard | © 2026 Antigravity Data Lab")
