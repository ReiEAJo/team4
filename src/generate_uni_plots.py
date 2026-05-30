"""
이 모듈은 단변량 분석(1인가구_총계, 지출_총금액, 당월_매출_금액, 총_유동인구, 폐업_률)에 대해
자치구별(좌측) 및 행정동별(우측) 비교 막대그래프를 생성합니다.
"""
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import matplotlib.font_manager as fm

# 한글 폰트 설정
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

data_dir = 'data'
images_dir = 'images'
os.makedirs(images_dir, exist_ok=True)

# 1. 데이터 로드
# 인구
pop_file = glob.glob(os.path.join(data_dir, '*주민등록 1인세대수*.csv'))[0]
pop_df = pd.read_csv(pop_file, encoding='cp949')
pop_df['행정동_코드'] = pop_df['행정기관코드'].astype(str).str[:8]
pop_df.rename(columns={'계': '1인가구_총계', '시군구명': '자치구', '읍면동명': '행정동'}, inplace=True)
pop_df['1인가구_총계'] = pd.to_numeric(pop_df['1인가구_총계'], errors='coerce').fillna(0)

# 매출액 (당월_매출_금액)
sales_files = glob.glob(os.path.join(data_dir, '*추정매출-행정동*.csv'))
sales_df = pd.read_csv(sales_files[0], encoding='cp949')
latest_fq = sales_df['기준_년분기_코드'].max()
sales_latest = sales_df[sales_df['기준_년분기_코드'] == latest_fq]
sales_grouped = sales_latest.groupby('행정동_코드_명')[['당월_매출_금액']].sum().reset_index()
sales_grouped.rename(columns={'행정동_코드_명': '행정동'}, inplace=True)

# 지출액 (지출_총금액) - if using 소비-행정동.csv
spend_file = glob.glob(os.path.join(data_dir, '서울시 상권분석서비스(소비-행정동).csv'))
spend_df = pd.read_csv(spend_file[0], encoding='cp949')
latest_fq_spend = spend_df['기준_년분기_코드'].max()
spend_latest = spend_df[spend_df['기준_년분기_코드'] == latest_fq_spend]
spend_grouped = spend_latest.groupby('행정동_코드_명')['지출_총금액'].sum().reset_index()
spend_grouped.rename(columns={'행정동_코드_명': '행정동'}, inplace=True)

# 폐업률
close_file = glob.glob(os.path.join(data_dir, '*점포-행정동*.csv'))[0]
close_df = pd.read_csv(close_file, encoding='cp949')
latest_fq_close = close_df['기준_년분기_코드'].max()
close_latest = close_df[close_df['기준_년분기_코드'] == latest_fq_close]
close_grouped = close_latest.groupby('행정동_코드_명')[['폐업_점포_수', '유사_업종_점포_수']].sum().reset_index()
close_grouped['폐업_률'] = (close_grouped['폐업_점포_수'] / close_grouped['유사_업종_점포_수']) * 100
close_grouped['폐업_률'] = close_grouped['폐업_률'].fillna(0)
close_grouped.rename(columns={'행정동_코드_명': '행정동'}, inplace=True)

# 유동인구
foot_files = glob.glob(os.path.join(data_dir, '*생활인구*.csv'))[0]
foot_df = pd.read_csv(foot_files, encoding='cp949')
latest_day = foot_df['기준일ID'].max()
foot_latest = foot_df[foot_df['기준일ID'] == latest_day]
foot_grouped = foot_latest.groupby('행정동코드')['총생활인구수'].sum().reset_index()
foot_grouped.rename(columns={'총생활인구수': '총_유동인구'}, inplace=True)
foot_grouped['행정동코드'] = foot_grouped['행정동코드'].astype(str)

# Merge
merged = pop_df[['자치구', '행정동', '행정동_코드', '1인가구_총계']].copy()
merged = pd.merge(merged, sales_grouped, on='행정동', how='left')
merged = pd.merge(merged, spend_grouped, on='행정동', how='left')
merged = pd.merge(merged, close_grouped[['행정동', '폐업_률']], on='행정동', how='left')
merged = pd.merge(merged, foot_grouped, left_on='행정동_코드', right_on='행정동코드', how='left')
merged = merged.fillna(0)

def plot_dual_bar(df, col_name, title, filename, is_rate=False):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    unique_gu = sorted([str(x) for x in df['자치구'].dropna().unique() if x != 0 and str(x) != '0'])
    import matplotlib.cm as cm
    import numpy as np
    cmap = cm.get_cmap('tab20')
    color_map = {gu: cmap(i / len(unique_gu)) for i, gu in enumerate(unique_gu)}
    
    # Left: 자치구별 (Top 10)
    if is_rate:
        gu_data = df.groupby('자치구')[col_name].mean().reset_index()
    else:
        gu_data = df.groupby('자치구')[col_name].sum().reset_index()
        
    gu_data = gu_data.sort_values(col_name, ascending=False).head(10)
    colors_left = [color_map[gu] for gu in gu_data['자치구']]
    axes[0].bar(gu_data['자치구'], gu_data[col_name], color=colors_left)
    axes[0].set_title(f'자치구별 {title} Top 10', fontsize=14)
    axes[0].set_xticklabels(gu_data['자치구'], rotation=45)
    
    # Right: 행정동별 (Top 10)
    dong_data = df.sort_values(col_name, ascending=False).head(10)
    colors_right = [color_map[gu] for gu in dong_data['자치구']]
    axes[1].bar(dong_data['행정동'], dong_data[col_name], color=colors_right)
    axes[1].set_title(f'행정동별 {title} Top 10', fontsize=14)
    axes[1].set_xticklabels(dong_data['행정동'], rotation=45)
    
    # Add legend to Right chart (showing which color belongs to which Gu)
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=color_map[gu], label=gu) for gu in dong_data['자치구'].unique()]
    axes[1].legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.25, 1.0))
    
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, filename))
    plt.close()

# Generate plots
plot_dual_bar(merged, '1인가구_총계', '1인가구 분포', 'plot_uni1.png', is_rate=False)
plot_dual_bar(merged, '지출_총금액', '지출 총금액(만원)', 'plot_uni2.png', is_rate=False)
plot_dual_bar(merged, '당월_매출_금액', '당월 매출 금액(만원)', 'plot_uni3.png', is_rate=False)
plot_dual_bar(merged, '총_유동인구', '총 유동인구(명)', 'plot_uni4.png', is_rate=False)
plot_dual_bar(merged, '폐업_률', '평균 폐업률(%)', 'plot_uni5.png', is_rate=True)

print("Univariate plots successfully generated.")
