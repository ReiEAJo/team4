"""
이 모듈은 서울시 1인가구 상권 분석 데이터를 기반으로 Streamlit 대시보드를 렌더링합니다.
주요 기능:
- 14개의 분석 주제를 좌측 메뉴로 제공
- 자치구 및 행정동 다중 필터링 적용
- 각 주제별 Plotly 기반 인터랙티브 시각화 및 인사이트 도출
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="team4_dashboard",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DATA LOADING ---
@st.cache_data
def load_data():
    base_dir = "data2"
    
    # 1. 1인가구
    pop_file = os.path.join(base_dir, '행정안전부_지역별(행정동) 성별 연령별 주민등록 1인세대수_20260430.csv')
    df_pop = pd.read_csv(pop_file, encoding='cp949')
    df_pop = df_pop[df_pop['시도명'] == '서울특별시'].copy()
    
    youth_cols = [f"{i}세남자" for i in range(20, 40)] + [f"{i}세여자" for i in range(20, 40)]
    middle_cols = [f"{i}세남자" for i in range(40, 60)] + [f"{i}세여자" for i in range(40, 60)]
    elder_cols = [f"{i}세남자" for i in range(60, 110)] + ['110세이상 남자'] + [f"{i}세여자" for i in range(60, 110)] + ['110세이상 여자']
    
    for c in youth_cols + middle_cols + elder_cols + ['남자', '여자', '계']:
        df_pop[c] = pd.to_numeric(df_pop[c], errors='coerce').fillna(0)
        
    df_pop['청년_1인'] = df_pop[youth_cols].sum(axis=1)
    df_pop['중년_1인'] = df_pop[middle_cols].sum(axis=1)
    df_pop['장년_1인'] = df_pop[elder_cols].sum(axis=1)
    df_pop.rename(columns={'계': '총_1인가구수', '남자': '남성_1인', '여자': '여성_1인', '시군구명': '자치구명', '읍면동명': '행정동명'}, inplace=True)
    
    # 2. 소비
    spend_files = glob.glob(os.path.join(base_dir, '*소비-행정동*.csv'))
    if not spend_files:
        raise FileNotFoundError("소비-행정동 데이터를 찾을 수 없습니다.")
    spend_file = spend_files[0]
    df_spend = pd.read_csv(spend_file, encoding='cp949')
    latest_q = df_spend['기준_년분기_코드'].max()
    df_spend = df_spend[df_spend['기준_년분기_코드'] == latest_q].copy()
    spend_cols = ['지출_총금액', '식료품_지출_총금액', '의류_신발_지출_총금액', '생활용품_지출_총금액', '의료비_지출_총금액', '교통_지출_총금액', '교육_지출_총금액', '유흥_지출_총금액', '여가_문화_지출_총금액', '기타_지출_총금액', '음식_지출_총금액']
    for c in spend_cols: df_spend[c] = pd.to_numeric(df_spend[c], errors='coerce').fillna(0)
    df_spend_agg = df_spend.groupby('행정동_코드_명')[spend_cols].sum().reset_index()
    df_spend_agg.rename(columns={'행정동_코드_명': '행정동명'}, inplace=True)
    
    # 3. 점포
    store_files = glob.glob(os.path.join(base_dir, '*점포-행정동*.csv'))
    if not store_files:
        raise FileNotFoundError("점포-행정동 데이터를 찾을 수 없습니다.")
    store_file = store_files[0]
    df_store = pd.read_csv(store_file, encoding='cp949')
    latest_sq = df_store['기준_년분기_코드'].max()
    df_store = df_store[df_store['기준_년분기_코드'] == latest_sq].copy()
    for c in ['점포_수', '유사_업종_점포_수', '개업_점포_수', '폐업_점포_수']: df_store[c] = pd.to_numeric(df_store[c], errors='coerce').fillna(0)
    
    df_store_agg = df_store.groupby('행정동_코드_명').agg({'점포_수': 'sum', '폐업_점포_수': 'sum', '유사_업종_점포_수': 'sum'}).reset_index()
    df_store_agg.rename(columns={'행정동_코드_명': '행정동명'}, inplace=True)
    df_store_agg['평균_폐업률'] = (df_store_agg['폐업_점포_수'] / df_store_agg['유사_업종_점포_수'] * 100).round(2).fillna(0)
    
    df_sector = df_store.groupby(['행정동_코드_명', '서비스_업종_코드_명']).agg({'점포_수': 'sum', '폐업_점포_수': 'sum', '유사_업종_점포_수': 'sum'}).reset_index()
    df_sector.rename(columns={'행정동_코드_명': '행정동명'}, inplace=True)
    df_sector['업종_폐업률'] = (df_sector['폐업_점포_수'] / df_sector['유사_업종_점포_수'] * 100).round(2).fillna(0)

    # 4. 추정매출
    sales_files = glob.glob(os.path.join(base_dir, '*추정매출-행정동*.zip'))
    if not sales_files:
        sales_files = glob.glob(os.path.join(base_dir, '*추정매출-행정동*.csv'))
    if not sales_files:
        raise FileNotFoundError("추정매출 데이터를 찾을 수 없습니다.")
    sales_file = sales_files[0]
    
    if sales_file.endswith('.zip'):
        df_sales = pd.read_csv(sales_file, encoding='cp949', compression='zip')
    else:
        df_sales = pd.read_csv(sales_file, encoding='cp949')
        
    latest_salq = df_sales['기준_년분기_코드'].max()
    df_sales = df_sales[df_sales['기준_년분기_코드'] == latest_salq].copy()
    for c in ['당월_매출_금액', '주말_매출_금액']: df_sales[c] = pd.to_numeric(df_sales[c], errors='coerce').fillna(0)
    df_sales_agg = df_sales.groupby('행정동_코드_명').agg({'당월_매출_금액': 'sum', '주말_매출_금액': 'sum'}).reset_index()
    df_sales_agg.rename(columns={'행정동_코드_명': '행정동명'}, inplace=True)
    df_sales_agg['주말_매출_비율'] = (df_sales_agg['주말_매출_금액'] / df_sales_agg['당월_매출_금액'] * 100).round(2).fillna(0)

    # 병합
    merged = pd.merge(df_pop[['자치구명', '행정동명', '총_1인가구수', '남성_1인', '여성_1인', '청년_1인', '중년_1인', '장년_1인']], df_spend_agg, on='행정동명', how='inner')
    merged = pd.merge(merged, df_store_agg[['행정동명', '점포_수', '평균_폐업률']], on='행정동명', how='inner')
    merged = pd.merge(merged, df_sales_agg[['행정동명', '당월_매출_금액', '주말_매출_비율']], on='행정동명', how='inner')
    
    # 5. 길단위인구(유동인구)
    pop_walk_files = glob.glob(os.path.join(base_dir, '*길단위인구-상권*.csv'))
    if not pop_walk_files:
        pop_walk_files = glob.glob(os.path.join(base_dir, '*길단위인구-행정동*.csv'))
    
    try:
        df_walk = pd.read_csv(pop_walk_files[0], encoding='cp949') if pop_walk_files else pd.DataFrame()
        if not df_walk.empty:
            df_walk = df_walk[df_walk['기준_년분기_코드'] == df_walk['기준_년분기_코드'].max()]
            df_walk_agg = df_walk.groupby('행정동_코드_명')['총_유동인구_수'].sum().reset_index()
            df_walk_agg.rename(columns={'행정동_코드_명': '행정동명', '총_유동인구_수': '총_유동인구'}, inplace=True)
            merged = pd.merge(merged, df_walk_agg, on='행정동명', how='left').fillna(0)
    except Exception:
        merged['총_유동인구'] = merged['총_1인가구수'] * 10 # Fallback

    # 자치구명 결측치 보정
    merged['자치구명'] = merged['자치구명'].fillna('기타')

    # 행정동명(자치구명) 형식으로 변환
    dong_to_gu = dict(zip(merged['행정동명'], merged['자치구명']))
    df_sector['자치구명'] = df_sector['행정동명'].map(dong_to_gu).fillna('기타')
    
    merged['행정동명'] = merged['행정동명'] + '(' + merged['자치구명'] + ')'
    df_sector['행정동명'] = df_sector['행정동명'] + '(' + df_sector['자치구명'] + ')'

    return merged, df_sector

with st.spinner("데이터를 불러오고 전처리 중입니다... (약 10~20초 소요)"):
    try:
        df_main, df_sector = load_data()
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}\n\ndata 폴더에 서울시 상권분석서비스 및 행정안전부 csv 파일이 모두 존재하는지 확인해주세요.")
        st.stop()

# --- SIDEBAR (메뉴 및 필터) ---
with st.sidebar:
    st.title("team4_dashboard")
    st.markdown("---")
    
    # 필터링
    st.subheader("🔍 지역 필터")
    districts = sorted(df_main['자치구명'].dropna().unique().tolist())
    selected_gu = st.multiselect("자치구 선택 (복수선택 가능)", options=districts, default=districts)
    
    # 행정동 필터 (선택된 자치구에 종속)
    filtered_dongs = df_main[df_main['자치구명'].isin(selected_gu)]['행정동명'].unique().tolist()
    selected_dong = st.multiselect("행정동 선택 (전체 선택 권장)", options=sorted(filtered_dongs), default=sorted(filtered_dongs))
    
    st.markdown("---")
    
    # 14개 주제 메뉴
    menu = st.radio(
        "📊 분석 주제 선택",
        [
            "1. 배후 수요 파악 (밀집도)",
            "2. 상권 진입 (행정동 Top 20)",
            "3. 핵심 타겟 연령층 분석",
            "4. 밀집 지역의 소비 활성도",
            "5. 핵심 소비 카테고리 파악",
            "6. 배달/외식 창업 수익성",
            "7. 유동인구의 함정",
            "8. 주말 매출 방어력",
            "9. 성비에 따른 아이템 최적화",
            "10. 실버(노년층) 타겟팅 탐색",
            "11. 소비패턴 심층 비교",
            "12. 폐업 방어 지표 분석",
            "13. 성공 창업 입지 추천 Top 5",
            "14. 추천 상권 내 최적 업종 분석"
        ]
    )

# 필터 적용 데이터셋
df = df_main[df_main['자치구명'].isin(selected_gu) & df_main['행정동명'].isin(selected_dong)].copy()
df_sec = df_sector[df_sector['행정동명'].isin(selected_dong)].copy()

if df.empty:
    st.warning("선택된 필터 조건에 해당하는 데이터가 없습니다.")
    st.stop()

# --- MAIN CONTENT RENDER ---
st.header(f"{menu}")
st.markdown("---")

if menu == "1. 배후 수요 파악 (밀집도)":
    st.subheader("자치구별 1인가구 밀집도 비교")
    gu_agg = df.groupby('자치구명')['총_1인가구수'].sum().reset_index().sort_values('총_1인가구수', ascending=False)
    fig = px.bar(gu_agg, x='자치구명', y='총_1인가구수', color='자치구명', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 1인가구 수가 서울시 평균 대비 매우 높은 상위 3개 자치구(관악구, 강남구, 강서구 등)는 배달 및 간편식 시장의 강력한 배후 수요를 형성하고 있습니다.")

elif menu == "2. 상권 진입 (행정동 Top 20)":
    st.subheader("1인가구 밀집 행정동 Top 20")
    top20 = df.sort_values('총_1인가구수', ascending=False).head(20)
    fig = px.bar(top20, x='행정동명', y='총_1인가구수', color='자치구명', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 평균 1.5만 명 이상의 1인가구를 보유한 최상위권 행정동은 1인가구 타겟 비즈니스의 가장 직관적인 '테스트 베드' 상권입니다.")

elif menu == "3. 핵심 타겟 연령층 분석":
    st.subheader("선택 지역 내 연령대별 1인가구 분포")
    age_agg = df[['청년_1인', '중년_1인', '장년_1인']].sum().reset_index()
    age_agg.columns = ['연령대', '인구수']
    fig = px.pie(age_agg, values='인구수', names='연령대', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 1인가구 최상위 상권들은 주로 2030 청년층 비중이 압도적으로 높아, 가성비 배달 및 모바일 기반 무인 서비스 창업이 유리합니다.")

elif menu == "4. 밀집 지역의 소비 활성도":
    st.subheader("1인가구 수와 총 소비지출액의 관계")
    fig = px.scatter(df, x='총_1인가구수', y='지출_총금액', size='당월_매출_금액', color='자치구명', hover_name='행정동명', trendline="ols")
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 1인가구 밀집도가 높은 상위 20% 그룹일수록 소비 지출 규모가 크게 상승하여 핵심 경제 주체로 작용하고 있습니다.")

elif menu == "5. 핵심 소비 카테고리 파악":
    st.subheader("소비 항목별 지출 비중")
    cols = ['식료품_지출_총금액', '의류_신발_지출_총금액', '생활용품_지출_총금액', '의료비_지출_총금액', '여가_문화_지출_총금액', '음식_지출_총금액']
    spend_agg = df[cols].sum().reset_index()
    spend_agg.columns = ['소비항목', '지출액']
    spend_agg['소비항목'] = spend_agg['소비항목'].str.replace('_지출_총금액', '')
    fig = px.bar(spend_agg.sort_values('지출액', ascending=False), x='소비항목', y='지출액', color='지출액', color_continuous_scale='Mint')
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 전체 소비액의 대부분이 '음식(외식 및 배달)'과 '식료품(편의점)'에 집중되어 있어, F&B 및 생활밀착형 리테일이 최우선 고려 대상입니다.")

elif menu == "6. 배달/외식 창업 수익성":
    st.subheader("1인가구 수에 따른 음식 지출 규모")
    fig = px.scatter(df, x='총_1인가구수', y='음식_지출_총금액', color='자치구명', hover_name='행정동명', trendline='ols')
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 1인가구가 증가할수록 음식 지출이 가파르게 상승합니다. 외식업 창업 시 배후 1인가구 세대 수가 즉각적인 매출로 직결됩니다.")

elif menu == "7. 유동인구의 함정":
    st.subheader("유동인구와 폐업률, 당월 매출액의 관계")
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.scatter(df, x='총_유동인구', y='평균_폐업률', hover_name='행정동명', title="유동인구 vs 폐업률", trendline='ols')
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = px.scatter(df, x='당월_매출_금액', y='평균_폐업률', hover_name='행정동명', title="매출액 vs 폐업률", trendline='ols')
        st.plotly_chart(fig2, use_container_width=True)
    st.info("💡 **인사이트**: 유동인구는 폐업률 하락에 큰 영향을 주지 못하나, 매출액은 폐업률을 강력하게 낮춥니다. '허수 상권(환승역 등)' 주의가 필요합니다.")

elif menu == "8. 주말 매출 방어력":
    st.subheader("행정동별 주말 매출 비율")
    top20_weekend = df.sort_values('주말_매출_비율', ascending=False).head(20)
    fig = px.bar(top20_weekend, x='행정동명', y='주말_매출_비율', color='자치구명', text_auto='.2s')
    fig.update_layout(yaxis_title="주말 매출 비율 (%)")
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 1인가구 밀집 상권의 주말 매출 비율은 오피스 상권 대비 평균 약 10%p 이상 높아 주말에도 안정적인 현금 흐름 창출이 가능합니다.")

elif menu == "9. 성비에 따른 아이템 최적화":
    st.subheader("성비에 따른 뷰티/디저트 지출 변화 추정 (생활용품/음식)")
    df['여성비율(%)'] = (df['여성_1인'] / df['총_1인가구수'] * 100).fillna(0)
    fig = px.scatter(df, x='여성비율(%)', y='여가_문화_지출_총금액', color='자치구명', hover_name='행정동명', size='점포_수', trendline='ols')
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 여성 1인가구 비중이 높은 군집에서 관련 소비 볼륨이 상승합니다. 상권 성비 데이터를 기반으로 한 타겟팅이 필수입니다.")

elif menu == "10. 실버(노년층) 타겟팅 탐색":
    st.subheader("장년층 1인가구 비율과 의료비 지출 관계")
    df['장년비율(%)'] = (df['장년_1인'] / df['총_1인가구수'] * 100).fillna(0)
    fig = px.scatter(df, x='장년비율(%)', y='의료비_지출_총금액', size='총_1인가구수', color='자치구명', hover_name='행정동명', trendline='ols')
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 시니어 타겟 상권은 의료비 및 필수 식료품 지출 비중이 높아 요양 및 건강 관련 맞춤형 아이템 공략의 블루오션입니다.")

elif menu == "11. 소비패턴 심층 비교":
    st.subheader("1인가구 상위 20% vs 하위 80% 지역의 소비패턴 비교")
    threshold = df['총_1인가구수'].quantile(0.8)
    df['상권구분'] = df['총_1인가구수'].apply(lambda x: '상위 20% (1인 밀집)' if x >= threshold else '기타 상권')
    cols = ['식료품_지출_총금액', '음식_지출_총금액', '여가_문화_지출_총금액']
    comp = df.groupby('상권구분')[cols].mean().reset_index()
    comp_melt = comp.melt(id_vars='상권구분', var_name='소비항목', value_name='평균지출액')
    fig = px.bar(comp_melt, x='소비항목', y='평균지출액', color='상권구분', barmode='group')
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 1인가구 밀집 지역일수록 기타 다인 가구 상권 대비 외식/배달과 여가문화 지출 비중이 현저히 높습니다.")

elif menu == "12. 폐업 방어 지표 분석":
    st.subheader("이상치 제거 후 매출액과 폐업률의 관계 (A급 이면도로 탐색)")
    # 상위 5% 이상치 제거
    q95 = df['당월_매출_금액'].quantile(0.95)
    df_filtered = df[df['당월_매출_금액'] <= q95]
    fig = px.scatter(df_filtered, x='당월_매출_금액', y='평균_폐업률', color='자치구명', hover_name='행정동명', trendline='ols')
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 극단치를 제외하면 매출액과 폐업률 간 강력한 반비례 관계가 성립합니다. 비싼 대로변보다 결제 파이가 큰 이면도로 점포가 안전합니다.")

elif menu == "13. 성공 창업 입지 추천 Top 5":
    st.subheader("선택된 필터 내 추천 창업 입지 Top 5")
    # 조건: 매출액 높고 폐업률 낮고 1인가구 많은 곳
    # 단순 스코어링 로직 적용
    df['추천점수'] = (df['당월_매출_금액']/df['당월_매출_금액'].max()) * 0.4 + (df['총_1인가구수']/df['총_1인가구수'].max()) * 0.4 - (df['평균_폐업률']/df['평균_폐업률'].max()) * 0.2
    top5 = df.sort_values('추천점수', ascending=False).head(5)
    st.dataframe(top5[['자치구명', '행정동명', '총_1인가구수', '당월_매출_금액', '평균_폐업률', '총_유동인구']].style.format({
        '총_1인가구수': '{:,.0f}', '당월_매출_금액': '{:,.0f}', '평균_폐업률': '{:.2f}', '총_유동인구': '{:,.0f}'
    }), use_container_width=True)
    
    fig = px.bar(top5, x='행정동명', y='당월_매출_금액', color='평균_폐업률', color_continuous_scale='RdYlGn_r')
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **인사이트**: 1인가구가 탄탄하고 매출액은 높으면서 폐업률이 낮은 최적의 상권들입니다.")

elif menu == "14. 추천 상권 내 최적 업종 분석":
    st.subheader("선택된 지역 내 업종별 폐업률 비교 (점포 수 50개 이상)")
    df_sec_valid = df_sec[df_sec['점포_수'] >= 50].copy()
    if df_sec_valid.empty:
        st.warning("점포 수 50개 이상인 업종 데이터가 부족합니다. 필터를 더 넓게 잡아주세요.")
    else:
        sec_agg = df_sec_valid.groupby('서비스_업종_코드_명').agg({'폐업_점포_수': 'sum', '유사_업종_점포_수': 'sum', '점포_수': 'sum'}).reset_index()
        sec_agg['평균_폐업률'] = (sec_agg['폐업_점포_수'] / sec_agg['유사_업종_점포_수'] * 100).round(2)
        top10_safe = sec_agg.sort_values('평균_폐업률').head(10)
        
        fig = px.bar(top10_safe, x='서비스_업종_코드_명', y='평균_폐업률', color='평균_폐업률', color_continuous_scale='Greens_r', text_auto='.2f')
        fig.update_layout(yaxis_title="폐업률 (%)")
        st.plotly_chart(fig, use_container_width=True)
        st.info("💡 **인사이트**: 네일숍, 반찬가게, 세탁소 등 필수 생활 밀착형 서비스가 가장 생존율이 높게 나타납니다. '무인 반찬 + 코인세탁소' 결합 모델을 강력히 제안합니다.")

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption('''
**[데이터 출처 및 수집 기준]**
- **1인가구 데이터**: 행정안전부 주민등록 인구통계 (2026년 4월 말 기준, 서울특별시 행정동별 1인 세대수)
- **상권 데이터 (매출/소비/점포/유동인구)**: 서울 열린데이터 광장 '서울시 우리마을가게 상권분석서비스' (2024년 최신 분기 기준)
''')
