import glob
"""
이 모듈은 1인가구가 많은 상권(행정동) Top 10을 대상으로
유동인구를 막대그래프로, 매출액을 꺾은선그래프로 비교하는
이중축(Dual-axis) 시각화 이미지를 생성합니다.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# Set Korean font for Windows
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

data_dir = 'data'
img_dir = 'images'
os.makedirs(img_dir, exist_ok=True)

# 1. Load Population (1인가구)
pop_file = os.path.join(data_dir, '행정안전부_지역별(행정동) 성별 연령별 주민등록 1인세대수_20260430.csv')
pop_df = pd.read_csv(pop_file, encoding='cp949')
pop_df['행정동_코드'] = pop_df['행정기관코드'].astype(str).str[:8]
pop_df.rename(columns={'계': '1인가구_총계', '시군구명': '자치구', '읍면동명': '행정동'}, inplace=True)
pop_df['1인가구_총계'] = pd.to_numeric(pop_df['1인가구_총계'], errors='coerce').fillna(0)

# 2. Load Sales (매출/지출)
sales_files = glob.glob(os.path.join(data_dir, '*추정매출-행정동*.csv'))
sales_df = pd.read_csv(sales_files[0], encoding='cp949')
latest_fq = sales_df['기준_년분기_코드'].max()
sales_latest = sales_df[sales_df['기준_년분기_코드'] == latest_fq]
sales_grouped = sales_latest.groupby('행정동_코드_명')[['당월_매출_금액']].sum().reset_index()
sales_grouped.rename(columns={'행정동_코드_명': '행정동'}, inplace=True)

# 3. Load Foot traffic (유동인구 / 생활인구)
foot_files = glob.glob(os.path.join(data_dir, '*생활인구*.csv'))
foot_df = pd.read_csv(foot_files[0], encoding='cp949')

# Get latest day
latest_day = foot_df['기준일ID'].max()
foot_latest = foot_df[foot_df['기준일ID'] == latest_day]
foot_grouped = foot_latest.groupby('행정동코드')['총생활인구수'].sum().reset_index()
foot_grouped.rename(columns={'총생활인구수': '총_유동인구'}, inplace=True)
foot_grouped['행정동코드'] = foot_grouped['행정동코드'].astype(str)
foot_grouped['총_유동인구'] = pd.to_numeric(foot_grouped['총_유동인구'], errors='coerce').fillna(0)

# Merge
merged = pd.merge(pop_df[['행정동', '행정동_코드', '1인가구_총계']], sales_grouped, left_on='행정동', right_on='행정동', how='inner')
merged = pd.merge(merged, foot_grouped, left_on='행정동_코드', right_on='행정동코드', how='inner')

# Sort by 1인가구 to get top regions
merged = merged.sort_values(by='1인가구_총계', ascending=False)
top10 = merged.head(10)

# 4. Plot Dual Axis (Bar: 유동인구, Line: 당월_매출_금액)
fig, ax1 = plt.subplots(figsize=(12, 6))

ax1.bar(top10['행정동'], top10['총_유동인구'], color='skyblue', label='총 유동인구 (명)')
ax1.set_xlabel('행정동 (1인가구 밀집 Top 10)', fontsize=12)
ax1.set_ylabel('총 유동인구 (명)', color='skyblue', fontsize=12)
ax1.tick_params(axis='y', labelcolor='skyblue')
plt.xticks(rotation=45)

ax2 = ax1.twinx()
ax2.plot(top10['행정동'], top10['당월_매출_금액'], color='salmon', marker='o', linewidth=2, label='당월 매출 금액 (만원)')
ax2.set_ylabel('당월 매출 금액 (만원)', color='salmon', fontsize=12)
ax2.tick_params(axis='y', labelcolor='salmon')

plt.title('1인가구 밀집 Top 10 지역의 유동인구 및 매출액 비교')
fig.tight_layout()

# Save
plt.savefig(os.path.join(img_dir, 'plot4.png'), dpi=300, bbox_inches='tight')
print("Saved plot4.png successfully.")
