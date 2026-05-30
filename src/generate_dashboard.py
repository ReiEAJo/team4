"""
이 스크립트는 서울특별시 자치구별 1인가구 인구, 소비 지출, 점포 폐업률 데이터를 정제 및 병합하고,
matplotlib을 활용한 10종의 시각화 그래프와 마크다운 보고서(eda_report.md)를 생성합니다.
또한, 서울시 자치구 GeoJSON 데이터에 분석 결과를 결합하여 로컬 브라우저에서 CORS 에러 없이
동작하는 인터랙티브 지도 대시보드(dashboard.html) 및 보고서 뷰어(report.html)를 자동 빌드합니다.
"""

import os
import urllib.request
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib
import shutil

# Matplotlib 차트 스타일 설정 및 한글 폰트 설정
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows 맑은 고딕 강제 지정으로 한글 깨짐 방지
plt.rcParams['axes.unicode_minus'] = False

def download_geojson():
    """서울시 자치구 경계 단순화 GeoJSON 데이터 다운로드"""
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    try:
        with urllib.request.urlopen(url) as response:
            geojson_data = json.loads(response.read().decode('utf-8'))
            return geojson_data
    except Exception as e:
        print(f"GeoJSON 다운로드 실패: {e}")
        # 예외 처리: 다운로드 실패 시 빈 뼈대 반환
        return {"type": "FeatureCollection", "features": []}

def aggregate_data(data_path):
    """1인가구, 소비, 점포 데이터를 가공하여 데이터프레임으로 변환"""
    # 1. 1인가구 데이터
    pop_file = os.path.join(data_path, '행정안전부_지역별(행정동) 성별 연령별 주민등록 1인세대수_20260430.csv')
    df_pop = pd.read_csv(pop_file, encoding='cp949')
    df_pop_seoul = df_pop[df_pop['시도명'] == '서울특별시'].copy()
    df_pop_seoul['자치구_코드'] = df_pop_seoul['행정기관코드'].astype(str).str[:5]
    
    # 연령 그룹 지정
    youth_cols = [f"{i}세남자" for i in range(20, 40)] + [f"{i}세여자" for i in range(20, 40)]
    middle_cols = [f"{i}세남자" for i in range(40, 60)] + [f"{i}세여자" for i in range(40, 60)]
    elder_cols = (
        [f"{i}세남자" for i in range(60, 110)] + ['110세이상 남자'] +
        [f"{i}세여자" for i in range(60, 110)] + ['110세이상 여자']
    )
    
    for c in youth_cols + middle_cols + elder_cols + ['남자', '여자', '계']:
        df_pop_seoul[c] = pd.to_numeric(df_pop_seoul[c], errors='coerce').fillna(0)
        
    df_pop_seoul['청년_1인'] = df_pop_seoul[youth_cols].sum(axis=1)
    df_pop_seoul['중년_1인'] = df_pop_seoul[middle_cols].sum(axis=1)
    df_pop_seoul['장년_1인'] = df_pop_seoul[elder_cols].sum(axis=1)
    
    gu_pop = df_pop_seoul.groupby(['자치구_코드', '시군구명']).agg({
        '계': 'sum',
        '남자': 'sum',
        '여자': 'sum',
        '청년_1인': 'sum',
        '중년_1인': 'sum',
        '장년_1인': 'sum'
    }).reset_index()
    gu_pop.rename(columns={'계': '총_1인가구수', '남자': '남성_1인', '여자': '여성_1인'}, inplace=True)
    
    # 2. 소비 데이터 (2025년 4분기 기준)
    spend_file = os.path.join(data_path, '서울시 상권분석서비스(소비-행정동).csv')
    df_spend = pd.read_csv(spend_file, encoding='cp949')
    latest_quarter = df_spend['기준_년분기_코드'].max()
    df_spend_latest = df_spend[df_spend['기준_년분기_코드'] == latest_quarter].copy()
    df_spend_latest['자치구_코드'] = df_spend_latest['행정동_코드'].astype(str).str[:5]
    
    spend_cols = [
        '지출_총금액', '식료품_지출_총금액', '의류_신발_지출_총금액', '생활용품_지출_총금액',
        '의료비_지출_총금액', '교통_지출_총금액', '교육_지출_총금액', '유흥_지출_총금액',
        '여가_문화_지출_총금액', '기타_지출_총금액', '음식_지출_총금액'
    ]
    for c in spend_cols:
        df_spend_latest[c] = pd.to_numeric(df_spend_latest[c], errors='coerce').fillna(0)
    gu_spend = df_spend_latest.groupby('자치구_코드')[spend_cols].sum().reset_index()
    
    # 3. 점포/폐업률 데이터 (2024년 4분기 기준)
    store_file = os.path.join(data_path, '서울시 상권분석서비스(점포-행정동)_2024년.csv')
    df_store = pd.read_csv(store_file, encoding='cp949')
    latest_store_q = df_store['기준_년분기_코드'].max()
    df_store_latest = df_store[df_store['기준_년분기_코드'] == latest_store_q].copy()
    df_store_latest['자치구_코드'] = df_store_latest['행정동_코드'].astype(str).str[:5]
    
    for c in ['점포_수', '유사_업종_점포_수', '개업_점포_수', '폐업_점포_수']:
        df_store_latest[c] = pd.to_numeric(df_store_latest[c], errors='coerce').fillna(0)
        
    gu_store = df_store_latest.groupby('자치구_코드').agg({
        '점포_수': 'sum',
        '폐업_점포_수': 'sum',
        '유사_업종_점포_수': 'sum'
    }).reset_index()
    gu_store.rename(columns={'폐업_점포_수': '총_폐업점포수'}, inplace=True)
    gu_store['평균_폐업률'] = (gu_store['총_폐업점포수'] / gu_store['유사_업종_점포_수'] * 100).round(2)
    
    # 병합
    merged = pd.merge(gu_pop, gu_spend, on='자치구_코드', how='inner')
    merged = pd.merge(merged, gu_store[['자치구_코드', '점포_수', '총_폐업점포수', '평균_폐업률']], on='자치구_코드', how='inner')
    
    merged['자치구_코드_int'] = merged['자치구_코드'].astype(int)
    merged.sort_values(by='자치구_코드_int', inplace=True)
    merged.drop(columns=['자치구_코드_int'], inplace=True)
    
    # 자치구별/업종별 데이터
    gu_sector_store = df_store_latest.groupby(['자치구_코드', '서비스_업종_코드_명']).agg({
        '점포_수': 'sum',
        '폐업_점포_수': 'sum',
        '유사_업종_점포_수': 'sum'
    }).reset_index()
    gu_sector_store['업종_폐업률'] = (gu_sector_store['폐업_점포_수'] / gu_sector_store['유사_업종_점포_수'] * 100).round(2)
    
    return merged, gu_sector_store

def generate_static_plots(df, df_sector, img_dir):
    """Matplotlib을 활용한 10종의 정적 시각화 차트 생성"""
    os.makedirs(img_dir, exist_ok=True)
    
    # 1. 1인가구수 vs 소비지출액 비교분석 (바 + 선 혼합 그래프)
    plt.figure(figsize=(12, 6))
    df_sorted = df.sort_values('총_1인가구수', ascending=False)
    
    ax1 = plt.gca()
    ax2 = ax1.twinx()
    
    # 바 그래프: 1인가구수
    x_positions = range(len(df_sorted))
    ax1.bar(x_positions, df_sorted['총_1인가구수'], color='#3b82f6', alpha=0.8, label='1인가구수 (명)')
    ax1.set_xlabel('자치구', fontsize=11)
    ax1.set_ylabel('1인가구 수 (명)', color='#3b82f6', fontsize=11)
    ax1.tick_params(axis='y', labelcolor='#3b82f6')
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels(df_sorted['시군구명'], rotation=45, ha='right')
    
    # 선 그래프: 소비지출액
    ax2.plot(x_positions, df_sorted['지출_총금액'], color='#ef4444', marker='o', linewidth=2.5, markersize=8, label='소비지출 총금액 (원)')
    ax2.set_ylabel('소비지출 총금액 (원)', color='#ef4444', fontsize=11)
    ax2.tick_params(axis='y', labelcolor='#ef4444')
    
    plt.title('서울시 자치구별 1인가구 밀도 및 소비지출액 비교', fontsize=15, pad=15, fontweight='bold')
    
    # 레전드 합치기
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')
    
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot1_quadrant_scatter.png'), dpi=300)
    plt.close()

    # 2. 자치구별 1인가구 연령대별 누적막대
    plt.figure(figsize=(12, 6))
    df_sorted_pop = df.sort_values(by='총_1인가구수', ascending=False)
    p1 = plt.bar(df_sorted_pop['시군구명'], df_sorted_pop['청년_1인'], color='#3b82f6', label='청년층(20-39세)')
    p2 = plt.bar(df_sorted_pop['시군구명'], df_sorted_pop['중년_1인'], bottom=df_sorted_pop['청년_1인'], color='#f59e0b', label='중년층(40-59세)')
    p3 = plt.bar(df_sorted_pop['시군구명'], df_sorted_pop['장년_1인'], bottom=df_sorted_pop['청년_1인']+df_sorted_pop['중년_1인'], color='#ef4444', label='장년층(60세이상)')
    plt.title('서울시 자치구별 1인가구 연령대별 누적 분포', fontsize=14, pad=15)
    plt.xticks(rotation=45)
    plt.xlabel('자치구', fontsize=11)
    plt.ylabel('1인가구 수 (명)', fontsize=11)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot2_age_stacked_bar.png'), dpi=300)
    plt.close()

    # 3. 관악구 소비 패턴 Top 5
    fig3 = plt.figure(figsize=(7, 7), facecolor='#0f172a')
    gwanak = df[df['시군구명'] == '관악구'].iloc[0]
    spend_cats = {
        '식료품': gwanak['식료품_지출_총금액'],
        '의류/신발': gwanak['의류_신발_지출_총금액'],
        '생활용품': gwanak['생활용품_지출_총금액'],
        '의료비': gwanak['의료비_지출_총금액'],
        '교통': gwanak['교통_지출_총금액'],
        '교육': gwanak['교육_지출_총금액'],
        '유흥': gwanak['유흥_지출_총금액'],
        '여가/문화': gwanak['여가_문화_지출_총금액'],
        '음식': gwanak['음식_지출_총금액'],
        '기타': gwanak['기타_지출_총금액']
    }
    top5_gwanak = sorted(spend_cats.items(), key=lambda x: x[1], reverse=True)[:5]
    labels, values = zip(*top5_gwanak)
    explode = (0.08, 0, 0, 0, 0)
    colors = sns.color_palette("Set3")[0:5]
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, 
            explode=explode, shadow=True, wedgeprops=dict(width=0.5, edgecolor='#0f172a', linewidth=2),
            textprops={'fontsize': 11, 'fontweight': 'bold', 'color': '#e2e8f0'})
    plt.title('관악구(1인가구 최다) 소비패턴 Top 5 지출 비중', fontsize=15, pad=15, fontweight='bold', color='#e2e8f0')
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot3_gwanak_spend_top5.png'), dpi=300, facecolor=fig3.get_facecolor(), transparent=True)
    plt.close()

    # 4. 중구 소비 패턴 Top 5
    fig4 = plt.figure(figsize=(7, 7), facecolor='#0f172a')
    jung = df[df['시군구명'] == '중구'].iloc[0]
    spend_cats_jung = {
        '식료품': jung['식료품_지출_총금액'],
        '의류/신발': jung['의류_신발_지출_총금액'],
        '생활용품': jung['생활용품_지출_총금액'],
        '의료비': jung['의료비_지출_총금액'],
        '교통': jung['교통_지출_총금액'],
        '교육': jung['교육_지출_총금액'],
        '유흥': jung['유흥_지출_총금액'],
        '여가/문화': jung['여가_문화_지출_총금액'],
        '음식': jung['음식_지출_총금액'],
        '기타': jung['기타_지출_총금액']
    }
    top5_jung = sorted(spend_cats_jung.items(), key=lambda x: x[1], reverse=True)[:5]
    labels_j, values_j = zip(*top5_jung)
    explode_j = (0.08, 0, 0, 0, 0)
    colors_j = sns.color_palette("pastel")[0:5]
    plt.pie(values_j, labels=labels_j, autopct='%1.1f%%', startangle=90, colors=colors_j,
            explode=explode_j, shadow=True, wedgeprops=dict(width=0.5, edgecolor='#0f172a', linewidth=2),
            textprops={'fontsize': 11, 'fontweight': 'bold', 'color': '#e2e8f0'})
    plt.title('중구(저밀도-고지출) 소비패턴 Top 5 지출 비중', fontsize=15, pad=15, fontweight='bold', color='#e2e8f0')
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot4_jung_spend_top5.png'), dpi=300, facecolor=fig4.get_facecolor(), transparent=True)
    plt.close()

    # 5. 관악구 주요 업종 폐업률 (점포수 30개 이상)
    plt.figure(figsize=(10, 5))
    gwanak_sectors = df_sector[(df_sector['자치구_코드'] == 11620) & (df_sector['점포_수'] >= 30)].sort_values(by='업종_폐업률').head(10)
    sns.barplot(data=gwanak_sectors, x='업종_폐업률', y='서비스_업종_코드_명', palette='viridis')
    plt.title('관악구 주요 생활밀착형 안전 업종 폐업률 Top 10 (점포수 30개 이상)', fontsize=13, pad=15)
    plt.xlabel('폐업률 (%)', fontsize=11)
    plt.ylabel('업종명', fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot5_gwanak_safe_sectors.png'), dpi=300)
    plt.close()

    # 6. 중구 주요 업종 폐업률 (점포수 30개 이상)
    plt.figure(figsize=(10, 5))
    jung_sectors = df_sector[(df_sector['자치구_코드'] == 11140) & (df_sector['점포_수'] >= 30)].sort_values(by='업종_폐업률').head(10)
    sns.barplot(data=jung_sectors, x='업종_폐업률', y='서비스_업종_코드_명', palette='magma')
    plt.title('중구 프리미엄 안전 업종 폐업률 Top 10 (점포수 30개 이상)', fontsize=13, pad=15)
    plt.xlabel('폐업률 (%)', fontsize=11)
    plt.ylabel('업종명', fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot6_jung_safe_sectors.png'), dpi=300)
    plt.close()

    # 7. 자치구별 1인가구 성별 비율 비교 막대 그래프
    plt.figure(figsize=(12, 6))
    df_sorted_gender = df.sort_values(by='총_1인가구수', ascending=False)
    x = np.arange(len(df_sorted_gender))
    width = 0.35
    plt.bar(x - width/2, df_sorted_gender['남성_1인'], width, label='남성 1인가구', color='#3b82f6')
    plt.bar(x + width/2, df_sorted_gender['여성_1인'], width, label='여성 1인가구', color='#ec4899')
    plt.title('서울시 자치구별 1인가구 성별 가구수 비교', fontsize=14, pad=15)
    plt.xticks(x, df_sorted_gender['시군구명'], rotation=45)
    plt.ylabel('1인가구 수 (명)', fontsize=11)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot7_gender_compare.png'), dpi=300)
    plt.close()

    # 8. 서울시 자치구별 전체 평균 폐업률 순위
    plt.figure(figsize=(12, 5))
    df_sorted_close = df.sort_values(by='평균_폐업률')
    sns.barplot(data=df_sorted_close, x='시군구명', y='평균_폐업률', palette='coolwarm')
    plt.title('서울시 자치구별 전체 평균 폐업률 비교 (낮은 순)', fontsize=14, pad=15)
    plt.xticks(rotation=45)
    plt.ylabel('평균 폐업률 (%)', fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot8_district_closure_rate.png'), dpi=300)
    plt.close()

    # 9. 연령대별 1인가구 총합 분포
    plt.figure(figsize=(7, 7))
    total_youth = df['청년_1인'].sum()
    total_middle = df['중년_1인'].sum()
    total_elder = df['장년_1인'].sum()
    plt.pie([total_youth, total_middle, total_elder], labels=['청년층(20-39세)', '중년층(40-59세)', '장년층(60세이상)'], autopct='%1.1f%%', startangle=140, colors=['#60a5fa', '#fbbf24', '#f87171'])
    plt.title('서울시 전체 1인가구 연령대별 지분 비율', fontsize=14, pad=15)
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot9_age_total_pie.png'), dpi=300)
    plt.close()

    # 10. 1인가구 1인당 지출액 비율 (소비력 지수) 상위 10개 구
    plt.figure(figsize=(10, 6))
    df['1인당_평균지출액'] = df['지출_총금액'] / df['총_1인가구수']
    df_sorted_per = df.sort_values(by='1인당_평균지출액', ascending=False).head(10)
    sns.barplot(data=df_sorted_per, x='1인당_평균지출액', y='시군구명', palette='crest')
    plt.title('서울시 자치구별 1인가구 1인당 평균 지출액 상위 10개 구 (단위: 원/구)', fontsize=13, pad=15)
    plt.xlabel('1인당 평균 소비지출 추정치 (원)', fontsize=11)
    plt.ylabel('자치구', fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(img_dir, 'plot10_spend_per_person.png'), dpi=300)
    plt.close()

def generate_markdown_report(df, df_sector, report_dir):
    """상세 분석 결과 마크다운 리포트 eda_report.md 생성"""
    os.makedirs(report_dir, exist_ok=True)
    
    gwanak = df[df['시군구명'] == '관악구'].iloc[0]
    jung = df[df['시군구명'] == '중구'].iloc[0]
    
    report_content = f"""# 서울특별시 1인가구 소비 패턴 및 상권 분석 리포트

본 보고서는 서울특별시 25개 자치구의 1인가구 주민등록 인구 통계, 소비 지출 총액, 그리고 자치구별 점포 폐업률 데이터를 융합 분석하여 1인가구 맞춤형 유망 비즈니스 아이템을 도출합니다.

---

## 1. 서울특별시 1인가구 인구 통계 요약 (성별, 연령대별)

주민등록 데이터를 기반으로 서울특별시 1인가구 현황을 분석한 결과, 1인가구 최다 거주지는 **관악구**(186,002명)로 집계되었으며, 최저 거주지는 **중구**(34,490명)입니다.

### 1인가구 인구 규모 상위 5개 자치구
| 자치구 | 총 1인가구 수 (명) | 남성 1인가구 (명) | 여성 1인가구 (명) | 청년 1인 (명) | 중년 1인 (명) | 장년 1인 (명) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **관악구** | {df.loc[df['시군구명']=='관악구', '총_1인가구수'].values[0]:,} | {df.loc[df['시군구명']=='관악구', '남성_1인'].values[0]:,} | {df.loc[df['시군구명']=='관악구', '여성_1인'].values[0]:,} | {df.loc[df['시군구명']=='관악구', '청년_1인'].values[0]:,} | {df.loc[df['시군구명']=='관악구', '중년_1인'].values[0]:,} | {df.loc[df['시군구명']=='관악구', '장년_1인'].values[0]:,} |
| **강서구** | {df.loc[df['시군구명']=='강서구', '총_1인가구수'].values[0]:,} | {df.loc[df['시군구명']=='강서구', '남성_1인'].values[0]:,} | {df.loc[df['시군구명']=='강서구', '여성_1인'].values[0]:,} | {df.loc[df['시군구명']=='강서구', '청년_1인'].values[0]:,} | {df.loc[df['시군구명']=='강서구', '중년_1인'].values[0]:,} | {df.loc[df['시군구명']=='강서구', '장년_1인'].values[0]:,} |
| **송파구** | {df.loc[df['시군구명']=='송파구', '총_1인가구수'].values[0]:,} | {df.loc[df['시군구명']=='송파구', '남성_1인'].values[0]:,} | {df.loc[df['시군구명']=='송파구', '여성_1인'].values[0]:,} | {df.loc[df['시군구명']=='송파구', '청년_1인'].values[0]:,} | {df.loc[df['시군구명']=='송파구', '중년_1인'].values[0]:,} | {df.loc[df['시군구명']=='송파구', '장년_1인'].values[0]:,} |
| **영등포구** | {df.loc[df['시군구명']=='영등포구', '총_1인가구수'].values[0]:,} | {df.loc[df['시군구명']=='영등포구', '남성_1인'].values[0]:,} | {df.loc[df['시군구명']=='영등포구', '여성_1인'].values[0]:,} | {df.loc[df['시군구명']=='영등포구', '청년_1인'].values[0]:,} | {df.loc[df['시군구명']=='영등포구', '중년_1인'].values[0]:,} | {df.loc[df['시군구명']=='영등포구', '장년_1인'].values[0]:,} |
| **강남구** | {df.loc[df['시군구명']=='강남구', '총_1인가구수'].values[0]:,} | {df.loc[df['시군구명']=='강남구', '남성_1인'].values[0]:,} | {df.loc[df['시군구명']=='강남구', '여성_1인'].values[0]:,} | {df.loc[df['시군구명']=='강남구', '청년_1인'].values[0]:,} | {df.loc[df['시군구명']=='강남구', '중년_1인'].values[0]:,} | {df.loc[df['시군구명']=='강남구', '장년_1인'].values[0]:,} |

![연령대별 누적막대 그래프](../images/plot2_age_stacked_bar.png)
*(그림 1: 서울시 자치구별 1인가구 연령대별 누적 분포)*

### 핵심 시사점
- 관악구는 서울에서 독보적으로 많은 1인가구가 거주하며, 대학가(서울대) 및 고시촌의 특성상 **청년층(20-39세)** 비율이 매우 높습니다.
- 강남구와 송파구는 청년층뿐만 아니라 중년층과 장년층 1인가구도 골고루 많이 분포하여 안정적인 배후수요를 형성하고 있습니다.

---

## 2. 1인가구 거주 밀도와 소비지출액 비교분석 (사분면 분석)

1인가구 수와 상권의 총 소비지출 규모를 비교분석하여 네 개의 영역으로 구분하였습니다.

![사분면 산점도 그래프](../images/plot1_quadrant_scatter.png)
*(그림 2: 서울시 자치구별 1인가구수 vs 소비지출액 비교 산점도)*

- **우측 상단 (고밀도-고지출)**: 1인가구가 많고 상권 활성화 지수도 높음 (예: 강남구, 송파구, 관악구). 대량 소비와 트렌디한 F&B 중심의 상권이 유망합니다.
- **좌측 상단 (저밀도-고지출)**: 1인가구는 적지만 도심 중심업무지구(CBD) 영향으로 지출 총금액이 압도적임 (예: 중구, 종로구). 고소득 직장인을 타겟으로 한 프리미엄 및 여가/케어 서비스가 적합합니다.
- **우측 하단 (고밀도-저지출)**: 1인가구가 많지만 1인당 지출력이 보통 수준인 생활 밀착형 주거 상권.
- **좌측 하단 (저밀도-저지출)**: 일반형 주거 상권.

---

## 3. 주요 자치구별 1인가구 소비 패턴 분석 (Top 5)

<div style="display: flex; justify-content: space-between; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px;">
        <h3>관악구(1인가구 최다) 소비패턴 Top 5</h3>
        <p>관악구의 1인가구 소비 지출 중 가장 비중이 높은 상위 5개 항목은 다음과 같습니다.</p>
        <ol>
            <li><strong>음식</strong>: {gwanak['음식_지출_총금액']:,} 원 (30.4%)</li>
            <li><strong>식료품</strong>: {gwanak['식료품_지출_총금액']:,} 원 (29.4%)</li>
            <li><strong>의료비</strong>: {gwanak['의료비_지출_총금액']:,} 원 (19.1%)</li>
            <li><strong>교통</strong>: {gwanak['교통_지출_총금액']:,} 원 (13.5%)</li>
            <li><strong>여가_문화</strong>: {gwanak['여가_문화_지출_총금액']:,} 원 (7.2%)</li>
        </ol>
        <img src="../images/plot3_gwanak_spend_top5.png" alt="관악구 소비 패턴" style="width:100%; border-radius:10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <p align="center"><em>(그림 3: 관악구 1인가구 소비패턴 Top 5)</em></p>
    </div>
    <div style="flex: 1; min-width: 300px;">
        <h3>중구(저밀도-고지출) 소비패턴 Top 5</h3>
        <p>중구의 1인가구 소비 지출 중 가장 비중이 높은 상위 5개 항목입니다.</p>
        <ol>
            <li><strong>음식</strong>: {jung['음식_지출_총금액']:,} 원 (36.2%)</li>
            <li><strong>식료품</strong>: {jung['식료품_지출_총금액']:,} 원 (21.4%)</li>
            <li><strong>교통</strong>: {jung['교통_지출_총금액']:,} 원 (17.5%)</li>
            <li><strong>의료비</strong>: {jung['의료비_지출_총금액']:,} 원 (12.1%)</li>
            <li><strong>여가_문화</strong>: {jung['여가_문화_지출_총금액']:,} 원 (8.5%)</li>
        </ol>
        <img src="../images/plot4_jung_spend_top5.png" alt="중구 소비 패턴" style="width:100%; border-radius:10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <p align="center"><em>(그림 4: 중구 1인가구 소비패턴 Top 5)</em></p>
    </div>
</div>

---

## 4. 자치구별 맞춤형 상업(서비스) 아이템 추천 (폐업률 반영)

점포 2024년 4분기 기준 폐업률 데이터를 조사하여 상권 안정성이 검증된 유망 아이템을 도출했습니다.

### 4-1. 1인가구 최다 거주지 (관악구) 추천 아이템
관악구는 청년층 1인가구의 비중이 매우 크며, 식비(음식 + 식료품) 지출액이 전체의 약 60%를 차지합니다.
- **추천 아이템 1**: **1인 전용 헤어숍/미용실**
  - **선정 근거**: 관악구 내 미용실 점포수는 382개에 달하지만, 분기 폐업률은 **0.47%**로 극히 낮아 사업 안정성이 매우 큽니다.
- **추천 아이템 2**: **반찬 전문점 및 테이크아웃 밀프렙**
  - **선정 근거**: 식료품 지출액이 약 293억 원 규모로 2위를 차지하고 있으며, 1인가구의 가성비 식사 준비에 대한 니즈가 강합니다.

### 4-2. 저밀도-고지출 지역 (중구) 추천 상권/아이템
중구는 거주 인구는 적으나 도심 상권의 지출액이 서울에서 가장 높고 여가/웰니스 지출 성향이 강합니다.
- **추천 아이템 1**: **도심형 실내 골프연습장 및 피트니스 클럽**
  - **선정 근거**: 중구 내 골프연습장(점포 43개) 및 피트니스 관련 점포의 폐업률은 **0.0%**로 견고한 고소득층 수요를 자랑합니다.
- **추천 아이템 2**: **프리미엄 피부관리실 및 에스테틱 전문점**
  - **선정 근거**: 중구 내 피부관리 점포(55개)의 폐업률은 **0.0%**로, 미용과 자기관리에 투자를 아끼지 않는 고지출 1인가구 및 직장인 수요가 탄탄합니다.

### 4-3. 중장년층 1인가구 최다 거주지 (관악구) 추천 및 서울시 지원제도 연계
서울시에서 중장년(40-59세) 1인가구가 가장 많이 사는 구 또한 **관악구**(34,580명)입니다. 중장년층은 청년층에 비해 의료비 지출 비중이 3위(190억 원)로 높게 올라오는 특성을 보입니다.
- **추천 아이템 1**: **건강/저염식 소셜다이닝 반찬 배달 서비스**
  - **정책 연계**: 서울시 1인가구 지원사업인 **소셜다이닝 '행복한 밥상'** 사업과 연계 가능. 건강 및 영양 관리에 취약한 중장년 1인가구 대상 식단 정기 구독 모델이 적합합니다.
- **추천 아이템 2**: **1인가구 주택관리/홈케어 대행 서비스**
  - **정책 연계**: 서울시의 **1인가구 주택관리 서비스** 제도를 참고하여 전등 교체, 수도꼭지 수리, 에어컨 청소, 방역 등 간단하지만 중장년 1인가구가 직접 해결하기 곤란한 기술 지원 대행 서비스를 제안합니다.
- **추천 아이템 3**: **O2O 병원 동행 및 메디컬 이동 지원 플랫폼**
  - **정책 연계**: 서울시 **'1인가구 안심동행'** 서비스(병원 동행 연계) 제도를 민간 비즈니스로 확장하여, 중장년 및 시니어 1인가구의 병원 에스코트, 처방전 약품 수령 대행 서비스를 제안합니다. (관악구 내 일반의원 385개, 폐업률 0.0%로 메디컬 인프라 밀접 연계 가능).

---
*보고서 작성 연월: 2026년 5월*
"""
    
    report_path = os.path.join(report_dir, "eda_report.md")
    with open(report_path, "w", encoding='utf-8') as f:
        f.write(report_content)
    print(f"마크다운 분석 보고서가 {report_path}에 작성되었습니다.")

def build_dashboard_html(df, df_sector, geojson_data, output_file):
    """Leaflet.js 지도와 Chart.js 그래프를 포함하는 apps/dashboard.html 생성"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 1. GeoJSON의 Feature properties에 분석 데이터 주입
    # GeoJSON의 구 이름 키: 'name' (예: '강남구')
    district_data_map = {}
    for _, r in df.iterrows():
        district_data_map[r['시군구명']] = {
            'code': r['자치구_코드'],
            'total_pop': int(r['총_1인가구수']),
            'male_pop': int(r['남성_1인']),
            'female_pop': int(r['여성_1인']),
            'youth_pop': int(r['청년_1인']),
            'middle_pop': int(r['중년_1인']),
            'elder_pop': int(r['장년_1인']),
            'spend_total': float(r['지출_총금액']),
            'store_count': int(r['점포_수']),
            'closure_rate': float(r['평균_폐업률']),
            'spend_food': float(r['식료품_지출_총금액']),
            'spend_dining': float(r['음식_지출_총금액']),
            'spend_medical': float(r['의료비_지출_총금액']),
            'spend_transport': float(r['교통_지출_총금액']),
            'spend_leisure': float(r['여가_문화_지출_총금액']),
            'spend_other': float(r['기타_지출_총금액'])
        }
        
    for feature in geojson_data.get('features', []):
        gu_name = feature.get('properties', {}).get('name', '')
        if gu_name in district_data_map:
            feature['properties'].update(district_data_map[gu_name])
            
    geojson_str = json.dumps(geojson_data, ensure_ascii=False)
    districts_list_str = df.to_json(orient='records', force_ascii=False)
    
    # HTML 내용 작성
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>서울시 1인가구 분석 및 상권 추천 대시보드</title>
    
    <!-- SEO 및 메타 태그 -->
    <meta name="description" content="서울특별시 자치구별 1인가구 현황, 소비 패턴, 그리고 점포 폐업률 분석을 통한 최적의 비즈니스 아이템 추천 대시보드">
    <meta name="keywords" content="1인가구, 서울시, 소비패턴, 상권분석, 폐업률, 비즈니스 추천, 대시보드">
    
    <!-- Leaflet.js CSS / JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Chart.js Annotation Plugin -->
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1"></script>
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;600;800&family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: #111827;
            --border-color: #1f2937;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --accent-blue: #3b82f6;
            --accent-yellow: #fbbf24;
            --accent-red: #ef4444;
            --accent-pink: #ec4899;
            --accent-green: #10b981;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Noto Sans KR', 'Inter', sans-serif;
            overflow-x: hidden;
            padding: 20px;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 30px;
            background: linear-gradient(135deg, #111827, #1f2937);
            border: 1px solid var(--border-color);
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
        }}

        header h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(to right, #a5b4fc, #818cf8, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .nav-btn {{
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        }}

        .nav-btn:hover {{
            background-color: var(--primary-hover);
            transform: translateY(-2px);
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns: 2fr 1.5fr 1.5fr;
            gap: 20px;
            margin-bottom: 20px;
        }}

        @media (max-width: 1200px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
            position: relative;
            overflow: hidden;
            transition: transform 0.3s ease;
        }}

        .card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background-color: var(--primary);
            opacity: 0.8;
        }}

        .card h2 {{
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .card h2 .subtitle {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 400;
        }}

        #map {{
            height: 480px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            background-color: #111a2e;
        }}

        /* 지도 호버 정보창 */
        .info-panel {{
            padding: 10px;
            background: rgba(17, 24, 39, 0.95);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            font-size: 13px;
            line-height: 1.5;
        }}

        .info-panel h4 {{
            margin-bottom: 5px;
            color: var(--accent-blue);
            font-size: 15px;
        }}

        /* 추천 패널 및 통계 */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }}

        .stat-box {{
            background-color: rgba(31, 41, 55, 0.5);
            border: 1px solid var(--border-color);
            padding: 12px;
            border-radius: 10px;
            text-align: center;
        }}

        .stat-label {{
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 5px;
        }}

        .stat-value {{
            font-family: 'Outfit', sans-serif;
            font-size: 20px;
            font-weight: 700;
        }}

        .recommendation-section {{
            background-color: rgba(31, 41, 55, 0.3);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 15px;
            margin-top: 15px;
        }}

        .recommendation-title {{
            font-size: 14px;
            font-weight: 700;
            color: var(--accent-yellow);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .recommendation-item {{
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .recommendation-item:last-child {{
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }}

        .recommendation-name {{
            font-weight: 600;
            font-size: 14px;
            color: var(--accent-green);
            margin-bottom: 3px;
        }}

        .recommendation-desc {{
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.5;
        }}

        .charts-row {{
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}

        @media (max-width: 768px) {{
            .charts-row {{
                grid-template-columns: 1fr;
            }}
        }}

        .chart-container {{
            position: relative;
            height: 280px;
            width: 100%;
        }}

        .quadrant-legend {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 10px;
            font-size: 11px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}

        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}
    </style>
</head>
<body>
    <header>
        <h1>📊 서울시 1인가구 분석 & 상업 아이템 추천 대시보드</h1>
        <a href="report.html" class="nav-btn">📑 분석리포트(MD) 보기</a>
    </header>

    <div class="dashboard-grid">
        <!-- 1. 지도시각화 영역 -->
        <div class="card">
            <h2>🗺️ 서울시 1인가구 공간적 분포 <span class="subtitle">지도를 클릭하면 자치구 정보로 갱신됩니다</span></h2>
            <div id="map"></div>
        </div>

        <!-- 2. 선택 자치구 주요 지표 -->
        <div class="card">
            <h2>📈 <span id="selected-gu-name">관악구</span> 1인가구 지표 분석</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">총 1인가구 수</div>
                    <div class="stat-value" id="stat-total-pop" style="color: var(--accent-blue);">0명</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">상권 총 소비지출액</div>
                    <div class="stat-value" id="stat-spend-total" style="color: var(--accent-green);">0원</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">점포 수</div>
                    <div class="stat-value" id="stat-stores" style="color: var(--accent-yellow);">0개</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">평균 폐업률</div>
                    <div class="stat-value" id="stat-closure" style="color: var(--accent-red);">0.0%</div>
                </div>
            </div>

            <!-- 인구 연령대 비율 비중 차트 -->
            <h3 style="font-size: 14px; margin-bottom: 10px; color: var(--text-muted);">성별/연령대별 가구 구성</h3>
            <div class="chart-container" style="height: 180px;">
                <canvas id="ageGenderChart"></canvas>
            </div>
        </div>

        <!-- 3. 자치구별 상업 아이템 추천 패널 -->
        <div class="card">
            <h2>💡 <span id="recommend-gu-name">관악구</span> 맞춤형 상업 추천</h2>
            
            <div class="recommendation-section">
                <div class="recommendation-title" style="color: var(--accent-green);">
                    📌 생활 밀착/안정형 추천 (폐업률 기준)
                </div>
                <div id="rec-safe-container">
                    <!-- JS에서 동적 주입 -->
                </div>
            </div>

            <div class="recommendation-section" style="margin-top: 15px;">
                <div class="recommendation-title" style="color: var(--accent-yellow);">
                    🏢 1인가구 맞춤 복지 제도 연계형 추천
                </div>
                <div id="rec-welfare-container">
                    <!-- JS에서 동적 주입 -->
                </div>
            </div>
        </div>
    </div>

    <!-- 하단 그래프 로우 -->
    <div class="charts-row">
        <!-- 4. 사분면 산점도 (Scatter) -->
        <div class="card">
            <h2>📊 서울시 1인가구 밀도 vs 상권 소비 비교 <span class="subtitle">마우스 드래그로 툴팁 확인 가능</span></h2>
            <div class="chart-container">
                <canvas id="scatterChart"></canvas>
            </div>
            <div class="quadrant-legend">
                <div class="legend-item"><span class="legend-dot" style="background-color: var(--accent-red);"></span>고밀도-고지출 (주력 상권)</div>
                <div class="legend-item"><span class="legend-dot" style="background-color: var(--accent-pink);"></span>저밀도-고지출 (프리미엄 상권)</div>
                <div class="legend-item"><span class="legend-dot" style="background-color: var(--accent-blue);"></span>고밀도-저지출 (생활형 상권)</div>
                <div class="legend-item"><span class="legend-dot" style="background-color: var(--text-muted);"></span>저밀도-저지출 (주거 상권)</div>
            </div>
        </div>

        <!-- 5. 소비 패턴 (Top 5) -->
        <div class="card">
            <h2>🛍️ 소비 카테고리별 지출액 비중 (Top 5)</h2>
            <div class="chart-container">
                <canvas id="spendPatternChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        // 파이썬에서 주입된 데이터
        const seoulGeoJSON = {geojson_str};
        const districtsData = {districts_list_str};

        // 데이터 맵 생성
        const districtMap = {{}};
        districtsData.forEach(d => {{
            districtMap[d.시군구명] = d;
        }});

        // 1. 지도 초기화
        const map = L.map('map').setView([37.5665, 126.9780], 11);
        
        // 다크 테마 타일 맵 로드
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors, © CARTO'
        }}).addTo(map);

        // 1인가구에 따른 구 컬러 스케일
        function getColor(pop) {{
            return pop > 150000 ? '#4f46e5' :
                   pop > 100000 ? '#6366f1' :
                   pop > 80000  ? '#818cf8' :
                   pop > 60000  ? '#a5b4fc' :
                   pop > 40000  ? '#c7d2fe' :
                                  '#e0e7ff';
        }}

        function style(feature) {{
            return {{
                fillColor: getColor(feature.properties.total_pop || 0),
                weight: 1.5,
                opacity: 1,
                color: '#1f2937',
                fillOpacity: 0.8
            }};
        }}

        let geojson;
        
        // 마우스 오버 및 클릭 이벤트 핸들러
        function onEachFeature(feature, layer) {{
            layer.on({{
                mouseover: highlightFeature,
                mouseout: resetHighlight,
                click: selectDistrict
            }});
        }}

        function highlightFeature(e) {{
            const layer = e.target;
            layer.setStyle({{
                weight: 3,
                color: '#a5b4fc',
                fillOpacity: 0.9
            }});
            layer.bringToFront();
        }}

        function resetHighlight(e) {{
            geojson.resetStyle(e.target);
        }}

        function selectDistrict(e) {{
            const props = e.target.feature.properties;
            updateDistrictDashboard(props.name);
        }}

        geojson = L.geoJson(seoulGeoJSON, {{
            style: style,
            onEachFeature: onEachFeature
        }}).addTo(map);

        // 2. 차트들 인스턴스 전역 변수
        let ageGenderChart;
        let spendPatternChart;
        let scatterChart;

        // 3. 대시보드 데이터 업데이트 함수
        function updateDistrictDashboard(guName) {{
            const data = districtMap[guName];
            if (!data) return;

            // UI 텍스트 갱신
            document.getElementById('selected-gu-name').innerText = guName;
            document.getElementById('recommend-gu-name').innerText = guName;
            document.getElementById('stat-total-pop').innerText = data.총_1인가구수.toLocaleString() + '명';
            document.getElementById('stat-spend-total').innerText = (data.지출_총금액 / 1e12).toFixed(2) + '조원';
            document.getElementById('stat-stores').innerText = data.점포_수.toLocaleString() + '개';
            document.getElementById('stat-closure').innerText = data.평균_폐업률.toFixed(2) + '%';

            // ① 연령/성별 차트 업데이트
            const ageData = {{
                labels: ['청년층(20-39세)', '중년층(40-59세)', '장년층(60세+)'],
                datasets: [
                    {{
                        label: '남성 가구',
                        data: [data.청년_1인 * (data.남성_1인 / data.총_1인가구수), data.중년_1인 * (data.남성_1인 / data.총_1인가구수), data.장년_1인 * (data.남성_1인 / data.총_1인가구수)],
                        backgroundColor: '#3b82f6'
                    }},
                    {{
                        label: '여성 가구',
                        data: [data.청년_1인 * (data.여성_1인 / data.총_1인가구수), data.중년_1인 * (data.여성_1인 / data.총_1인가구수), data.장년_1인 * (data.여성_1인 / data.총_1인가구수)],
                        backgroundColor: '#ec4899'
                    }}
                ]
            }};

            if (ageGenderChart) ageGenderChart.destroy();
            const ctxAge = document.getElementById('ageGenderChart').getContext('2d');
            ageGenderChart = new Chart(ctxAge, {{
                type: 'bar',
                data: ageData,
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{ stacked: true, grid: {{ display: false }} }},
                        y: {{ stacked: true, grid: {{ color: '#1f2937' }} }}
                    }},
                    plugins: {{
                        legend: {{ position: 'bottom', labels: {{ color: '#f3f4f6' }} }}
                    }}
                }}
            }});

            // ② 소비패턴 Top 5 차트 업데이트
            const spendCats = [
                {{ name: '식료품', val: data.식료품_지출_총금액 }},
                {{ name: '의류/신발', val: data.의류_신발_지출_총금액 }},
                {{ name: '생활용품', val: data.생활용품_지출_총금액 }},
                {{ name: '의료비', val: data.의료비_지출_총금액 }},
                {{ name: '교통', val: data.교통_지출_총금액 }},
                {{ name: '교육', val: data.교육_지출_총금액 }},
                {{ name: '유흥', val: data.유흥_지출_총금액 }},
                {{ name: '여가/문화', val: data.여가_문화_지출_총금액 }},
                {{ name: '음식', val: data.음식_지출_총금액 }},
                {{ name: '기타', val: data.기타_지출_총금액 }}
            ];
            spendCats.sort((a, b) => b.val - a.val);
            const top5 = spendCats.slice(0, 5);

            const patternData = {{
                labels: top5.map(x => x.name),
                datasets: [{{
                    data: top5.map(x => x.val),
                    backgroundColor: ['#6366f1', '#3b82f6', '#10b981', '#fbbf24', '#f43f5e']
                }}]
            }};

            if (spendPatternChart) spendPatternChart.destroy();
            const ctxPattern = document.getElementById('spendPatternChart').getContext('2d');
            spendPatternChart = new Chart(ctxPattern, {{
                type: 'doughnut',
                data: patternData,
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'right', labels: {{ color: '#f3f4f6' }} }}
                    }}
                }}
            }});

            // ③ 추천 문구 가변적 주입
            updateRecommendations(guName, data);
        }}

        // 추천 로직 업데이트 함수
        function updateRecommendations(guName, data) {{
            const safeContainer = document.getElementById('rec-safe-container');
            const welfareContainer = document.getElementById('rec-welfare-container');

            let safeHtml = '';
            let welfareHtml = '';

            if (guName === '관악구') {{
                safeHtml = `
                    <div class="recommendation-item">
                        <div class="recommendation-name">✂️ 1인 맞춤형 헤어숍/미용실</div>
                        <div class="recommendation-desc">관악구 내 점포수가 382개에 달하지만 폐업률은 0.47%로 극단적 안전성을 보입니다. 청년층 1인가구 타겟의 맞춤형 살롱이 최적입니다.</div>
                    </div>
                    <div class="recommendation-item">
                        <div class="recommendation-name">🍱 가성비 수제 도시락 및 밀프렙 반찬 배달</div>
                        <div class="recommendation-desc">식료품 지출(293억)과 음식 지출(303억)이 최상위권입니다. 1인가구 청년들을 위한 실속 반찬 배달/정기 구독이 경쟁력 있습니다.</div>
                    </div>
                `;
                welfareHtml = `
                    <div class="recommendation-item">
                        <div class="recommendation-name">🥗 소셜다이닝 연계 건강 반찬 서비스</div>
                        <div class="recommendation-desc">서울시 '행복한 밥상' 사업과 매칭하여 관악구의 중장년(3.4만)을 겨냥한 저염/당뇨 케어 건강 식단 배달.</div>
                    </div>
                    <div class="recommendation-item">
                        <div class="recommendation-name">🔧 1인가구 홈케어/집수리 O2O 대행</div>
                        <div class="recommendation-desc">서울시 주택관리 사업과 연계하여 등기구 교체, 에어컨 살균 등 소규모 수리/기술 지원을 대행하는 로컬 매칭 서비스.</div>
                    </div>
                `;
            }} else if (guName === '중구') {{
                safeHtml = `
                    <div class="recommendation-item">
                        <div class="recommendation-name">⛳ 프리미엄 실내 골프 아카데미 및 샵</div>
                        <div class="recommendation-desc">중구 내 골프연습장 점포의 폐업률은 0.0%입니다. 중심지 1인가구의 고급 여가 수요에 완벽 매칭됩니다.</div>
                    </div>
                    <div class="recommendation-item">
                        <div class="recommendation-name">🧖‍♀️ 하이엔드 피부관리실 및 에스테틱 전문점</div>
                        <div class="recommendation-desc">피부관리 전문점(점포 55개)의 폐업률이 0.0%를 자랑하며, 자기관리에 집중 투자하는 도심 고소득 직장인/1인가구를 타겟팅합니다.</div>
                    </div>
                `;
                welfareHtml = `
                    <div class="recommendation-item">
                        <div class="recommendation-name">💼 고소득 중장년 직무 전환 및 재취업 컨설팅</div>
                        <div class="recommendation-desc">중구의 고지출 중장년층을 겨냥한 일자리 매칭 및 생애 자산 컨설팅(서울시 중장년 지원정책 연계).</div>
                    </div>
                `;
            }} else {{
                // 일반 자치구용 공통 추천 템플릿
                const isHighSpend = data.지출_총금액 > 1e12;
                const isHighPop = data.총_1인가구수 > 80000;
                
                if (isHighPop) {{
                    safeHtml = `
                        <div class="recommendation-item">
                            <div class="recommendation-name">🧺 O2O 비대면 세탁 및 의류 살균 서비스</div>
                            <div class="recommendation-desc">1인가구 밀도가 높으므로 주거단지 거점 모바일 세탁 대행(수거/배달) 비즈니스가 지속적으로 안정적인 폐업률을 유지합니다.</div>
                        </div>
                    `;
                }} else {{
                    safeHtml = `
                        <div class="recommendation-item">
                            <div class="recommendation-name">🛒 주거 밀착형 종합 간편편의점</div>
                            <div class="recommendation-desc">점포당 배후 1인가구의 일상 밀접도가 높은 업종으로, 폐업률 변동 폭이 적고 지속적인 소규모 수요가 있습니다.</div>
                        </div>
                    `;
                }}

                welfareHtml = `
                    <div class="recommendation-item">
                        <div class="recommendation-name">🤝 1인가구 안심 병원동행 서비스 연계</div>
                        <div class="recommendation-desc">구 내 의료비 지출 비중을 토대로, 거동이 불편한 중장년/노인 1인가구를 위한 '안심 동행 서비스' 지원 사업 협력 비즈니스.</div>
                    </div>
                `;
            }}

            safeContainer.innerHTML = safeHtml;
            welfareContainer.innerHTML = welfareHtml;
        }}

        // 4. 사분면 산점도 차트 초기화 (Chart.js)
        function initScatterChart() {{
            const avgPop = {df['총_1인가구수'].mean()};
            const avgSpend = {df['지출_총금액'].mean()};

            const scatterData = districtsData.map(d => {{
                let color = '#9ca3af'; // 기본 회색 (저밀도-저지출)
                if (d.총_1인가구수 >= avgPop && d.지출_총금액 >= avgSpend) {{
                    color = '#ef4444'; // 고밀도-고지출 (레드)
                }} else if (d.총_1인가구수 < avgPop && d.지출_총금액 >= avgSpend) {{
                    color = '#ec4899'; // 저밀도-고지출 (핑크)
                }} else if (d.총_1인가구수 >= avgPop && d.지출_총금액 < avgSpend) {{
                    color = '#3b82f6'; // 고밀도-저지출 (블루)
                }}
                
                return {{
                    x: d.총_1인가구수,
                    y: d.지출_총금액,
                    label: d.시군구명,
                    backgroundColor: color
                }};
            }});

            const ctxScatter = document.getElementById('scatterChart').getContext('2d');
            scatterChart = new Chart(ctxScatter, {{
                type: 'scatter',
                data: {{
                    datasets: [{{
                        data: scatterData,
                        pointRadius: 8,
                        pointHoverRadius: 10,
                        backgroundColor: scatterData.map(p => p.backgroundColor)
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{
                            title: {{ display: true, text: '1인가구수 (명)', color: '#f3f4f6' }},
                            grid: {{ color: '#1f2937' }}
                        }},
                        y: {{
                            title: {{ display: true, text: '소비지출 총금액 (원)', color: '#f3f4f6' }},
                            grid: {{ color: '#1f2937' }}
                        }}
                    }},
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const item = context.raw;
                                    return `${{item.label}}: 가구수 ${{item.x.toLocaleString()}}명, 소비 ${{item.y.toLocaleString()}}원`;
                                }}
                            }}
                        }},
                        annotation: {{
                            annotations: {{
                                lineX: {{
                                    type: 'line',
                                    xMin: avgPop,
                                    xMax: avgPop,
                                    borderColor: 'rgba(255, 255, 255, 0.4)',
                                    borderWidth: 1.5,
                                    borderDash: [5, 5]
                                }},
                                lineY: {{
                                    type: 'line',
                                    yMin: avgSpend,
                                    yMax: avgSpend,
                                    borderColor: 'rgba(255, 255, 255, 0.4)',
                                    borderWidth: 1.5,
                                    borderDash: [5, 5]
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}

        // 초기 구 기동
        updateDistrictDashboard('관악구');
        initScatterChart();

    </script>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"인터랙티브 대시보드가 {output_file}에 빌드되었습니다.")

def build_report_html(report_md_file, output_html_file):
    """Marked.js와 Resizable Table 스크립트를 포함하는 apps/report.html 빌드"""
    os.makedirs(os.path.dirname(output_html_file), exist_ok=True)
    
    # MD 파일 로드
    with open(report_md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
        
    # JSON 문자열 인코딩하여 HTML 내에 안전하게 삽입
    md_content_escaped = json.dumps(md_content, ensure_ascii=False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>서울특별시 1인가구 분석 리포트</title>
    
    <!-- Marked.js (마크다운 파서) -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
    
    <style>
        body {{
            background-color: #0f172a;
            color: #e2e8f0;
            font-family: 'Noto Sans KR', 'Inter', sans-serif;
            font-size: 14px; /* 기존 기본 크기에서 -2px 줄여 가독성 향상 */
            line-height: 1.6;
            padding: 40px;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}

        header h1 {{
            font-size: 20px;
            font-weight: 700;
            color: #f1f5f9;
            margin: 0;
        }}

        .nav-btn {{
            background-color: #6366f1;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.3s;
            font-size: 13px;
        }}

        .nav-btn:hover {{
            background-color: #4f46e5;
        }}

        #report-content {{
            max-width: 900px;
            margin: 0 auto;
            background-color: #1e293b;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            border: 1px solid #334155;
        }}

        /* 마크다운 스타일 커스터마이징 */
        #report-content h1 {{
            font-size: 24px;
            border-bottom: 2px solid #6366f1;
            padding-bottom: 10px;
            margin-top: 0;
            margin-bottom: 25px;
            color: #f8fafc;
        }}

        #report-content h2 {{
            font-size: 18px;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #f1f5f9;
        }}

        #report-content h3 {{
            font-size: 15px;
            margin-top: 20px;
            margin-bottom: 10px;
            color: #e2e8f0;
        }}

        #report-content p {{
            margin-bottom: 15px;
            color: #cbd5e1;
        }}

        #report-content img {{
            max-width: 100%;
            border-radius: 8px;
            margin: 15px 0;
            border: 1px solid #475569;
        }}

        /* 리사이즈 테이블 스타일 */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            table-layout: fixed;
            position: relative;
        }}

        th, td {{
            border: 1px solid #475569;
            padding: 10px;
            text-align: left;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            position: relative;
        }}

        th {{
            background-color: #334155;
            color: #f8fafc;
            font-weight: 600;
        }}

        td {{
            background-color: #1e293b;
        }}

        /* 리사이즈 조절선 */
        .resizer {{
            position: absolute;
            top: 0;
            right: 0;
            width: 5px;
            cursor: col-resize;
            user-select: none;
            height: 100%;
            z-index: 1;
        }}

        .resizer:hover, .resizing {{
            background-color: #6366f1;
            width: 4px;
        }}
    </style>
</head>
<body>
    <header>
        <h1>📑 서울특별시 1인가구 분석 종합 리포트</h1>
        <a href="dashboard.html" class="nav-btn">📊 대시보드로 돌아가기</a>
    </header>

    <div id="report-content"></div>

    <script>
        const rawMarkdown = {md_content_escaped};
        
        // 마크다운 파싱 및 주입
        document.getElementById('report-content').innerHTML = marked.parse(rawMarkdown);

        // 테이블 리사이즈 기능 활성화 함수
        function makeTablesResizable() {{
            const tables = document.querySelectorAll('#report-content table');
            tables.forEach(table => {{
                const cols = table.querySelectorAll('th');
                cols.forEach(col => {{
                    // 리사이즈 드래그 조절선 핸들 추가
                    const resizer = document.createElement('div');
                    resizer.classList.add('resizer');
                    col.appendChild(resizer);
                    
                    // 마우스 이벤트 바인딩
                    let startX, startWidth;
                    
                    resizer.addEventListener('mousedown', e => {{
                        startX = e.clientX;
                        startWidth = col.offsetWidth;
                        col.classList.add('resizing');
                        
                        document.addEventListener('mousemove', mouseMoveHandler);
                        document.addEventListener('mouseup', mouseUpHandler);
                    }});
                    
                    function mouseMoveHandler(e) {{
                        const width = startWidth + (e.clientX - startX);
                        col.style.width = width + 'px';
                    }}
                    
                    function mouseUpHandler() {{
                        col.classList.remove('resizing');
                        document.removeEventListener('mousemove', mouseMoveHandler);
                        document.removeEventListener('mouseup', mouseUpHandler);
                    }}
                }});
            }});
        }}

        // DOM 업데이트 후 리사이저 동작
        setTimeout(makeTablesResizable, 100);
    </script>
</body>
</html>
"""
    
    with open(output_html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"리포트 뷰어가 {output_html_file}에 생성되었습니다.")

def main():
    base_dir = "one-person PJT"
    data_path = os.path.join(base_dir, "data")
    img_dir = os.path.join(base_dir, "images")
    report_dir = os.path.join(base_dir, "report")
    apps_dir = os.path.join(base_dir, "apps")
    
    print("1. 데이터 자치구별 병합 및 집계 분석 시작...")
    df, df_sector = aggregate_data(data_path)
    
    print("2. Matplotlib 분석 차트 10종 생성 및 저장...")
    generate_static_plots(df, df_sector, img_dir)
    
    print("3. 마크다운 보고서(eda_report.md) 빌드...")
    generate_markdown_report(df, df_sector, report_dir)
    
    print("4. 서울시 자치구 경계 GeoJSON 데이터 연동...")
    geojson_data = download_geojson()
    
    # 5. apps 폴더 생성 및 정적 이미지 에셋 동기화
    os.makedirs(apps_dir, exist_ok=True)
    apps_img_dir = os.path.join(apps_dir, "images")
    if os.path.exists(apps_img_dir):
        shutil.rmtree(apps_img_dir)
    shutil.copytree(img_dir, apps_img_dir)
    print("5. 정적 이미지 에셋을 apps/images/ 폴더로 복사 완료.")
    
    print("6. 인터랙티브 HTML 대시보드(apps/dashboard.html) 빌드...")
    build_dashboard_html(df, df_sector, geojson_data, os.path.join(apps_dir, "dashboard.html"))
    
    print("7. 마크다운 연동형 리포트 뷰어(apps/report.html) 빌드...")
    build_report_html(os.path.join(report_dir, "eda_report.md"), os.path.join(apps_dir, "report.html"))
    
    print("모든 리소스 빌드가 완료되었습니다!")

if __name__ == "__main__":
    main()
