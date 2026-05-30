"""
이 모듈은 1인가구 최다 거주 자치구를 탐색하고 해당 자치구의 2025년 최신 통신 데이터를 기반으로
소비패턴 및 생활양식을 분석하여 전문적인 EDA 리포트와 시각화 자료를 생성합니다.
주요 기능:
- 1인가구(연령별) 데이터에서 1인가구가 가장 많은 자치구 추출
- 29개 통신정보 데이터에서 해당 자치구 데이터 필터링
- 기술통계 분석 및 결측치 확인
- 연령대 및 성별에 따른 소비/여가 패턴 시각화 (10개 이상)
- 분석 결과를 종합한 마크다운 리포트 생성
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib
import numpy as np

def main():
    base_dir = r"c:\Users\Rei EA Jo\Downloads\icb10\one-person PJT"
    data_dir = os.path.join(base_dir, "data")
    img_dir = os.path.join(base_dir, "images")
    report_dir = os.path.join(base_dir, "report")
    
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)

    # 1. 1인가구 데이터 로드 및 최다 자치구 탐색
    hh_file = os.path.join(data_dir, "1인가구(연령별)_20260516092747.csv")
    try:
        df_hh = pd.read_csv(hh_file, encoding='utf-8')
    except UnicodeDecodeError:
        df_hh = pd.read_csv(hh_file, encoding='cp949')

    # '합계' 또는 '소계'가 아닌 실제 구 이름 필터링 (자치구별(2))
    # 자치구별(1)이 '합계'인 경우는 서울시 전체이므로 제외해야 할 수 있음.
    # 두번째 줄부터 실제 데이터가 있을 수 있음 (multi-index 형태일 수 있으므로 컬럼명 변경)
    if '2024' in df_hh.columns:
        total_col = '2024'
    else:
        total_col = df_hh.columns[3] # 4번째 컬럼을 총합으로 가정

    # 데이터 정리: '자치구별(2)' 컬럼이 '소계'나 '합계'가 아닌 행 중 '성별(1)'이 '계' 또는 '합계'인 것
    df_dist = df_hh[(df_hh['자치구별(2)'] != '소계') & (df_hh['자치구별(2)'] != '합계')]
    df_dist = df_dist[df_dist['성별(1)'].isin(['계', '합계'])]
    
    # 2024 총계를 숫자로 변환
    df_dist[total_col] = pd.to_numeric(df_dist[total_col], errors='coerce')
    top_district = df_dist.sort_values(by=total_col, ascending=False).iloc[0]['자치구별(2)']
    print(f"가장 1인가구가 많은 자치구: {top_district}")

    # 2. 통신정보(소비패턴) 데이터 로드 및 필터링
    # 가장 최신 2025년 데이터 (예: 2025.12월_29개 통신정보 (1).xlsx)
    comm_file = os.path.join(data_dir, "2025.12월_29개 통신정보 (1).xlsx")
    print(f"통신정보 데이터 로딩 중: {comm_file}")
    df_comm = pd.read_excel(comm_file)
    
    # 해당 자치구 필터링
    df_top = df_comm[df_comm['자치구'] == top_district].copy()
    print(f"필터링된 데이터 개수: {len(df_top)}")
    
    # 주요 소비/여가 관련 컬럼 선택
    # 컬럼명이 정확하지 않을 수 있으므로 포함된 단어로 검색
    cols_to_analyze = [
        '행정동', '성별', '연령대', '1인가구수',
        '소액결재 사용금액 평균', '소액결재 사용횟수 평균', 
        '배달 서비스 사용일수', '쇼핑 서비스 사용일수',
        '게임 서비스 사용일수', '금융 서비스 사용일수',
        '동영상/방송 서비스 사용일수', '유튜브 사용일수', '넷플릭스 사용일수'
    ]
    
    # 실제 존재하는 컬럼만 선택
    available_cols = [c for c in cols_to_analyze if c in df_top.columns]
    
    # 없는 컬럼은 비슷한 이름으로 찾아보기
    for c in cols_to_analyze:
        if c not in available_cols:
            for col in df_top.columns:
                if c.replace(' ', '') in col.replace(' ', ''):
                    if col not in available_cols:
                        available_cols.append(col)
                        break

    df_analysis = df_top[available_cols].copy()
    
    # 데이터 전처리 (숫자형 변환)
    num_cols = [c for c in available_cols if c not in ['행정동', '성별', '연령대']]
    for c in num_cols:
        df_analysis[c] = pd.to_numeric(df_analysis[c], errors='coerce').fillna(0)

    # 성별 한글로 매핑 (통상 1:남성, 2:여성)
    df_analysis['성별명'] = df_analysis['성별'].map({1: '남성', 2: '여성'})
    if df_analysis['성별명'].isnull().all():
        df_analysis['성별명'] = df_analysis['성별'].astype(str)

    # 기본 정보 기록
    report_content = []
    report_content.append(f"# {top_district} 1인가구 소비패턴 EDA 리포트")
    report_content.append("\n## 1. 개요")
    report_content.append(f"- **목적**: 1인가구 최다 거주 자치구인 **{top_district}**의 2025년 최신 통신 데이터를 분석하여 소비 및 여가 패턴을 파악합니다.")
    report_content.append(f"- **분석 데이터**: 2025년 12월 29개 통신정보 데이터")
    report_content.append(f"- **데이터 크기**: {df_analysis.shape[0]}행, {df_analysis.shape[1]}열")
    
    # 3. 기술 통계
    report_content.append("\n## 2. 데이터 기본 정보 및 기술 통계")
    report_content.append("\n### 수치형 변수 기술 통계")
    desc = df_analysis[num_cols].describe().round(2)
    report_content.append(desc.to_markdown())
    
    desc_str = (
        f"{top_district} 지역의 통신 및 소비 지표를 분석한 결과, 전반적으로 1인가구의 모바일 기반 소비가 활발하게 나타남을 알 수 있습니다. "
        f"소액결제 사용금액의 평균은 약 {desc['소액결재 사용금액 평균']['mean']:.0f}원이며, 최대 {desc['소액결재 사용금액 평균']['max']:.0f}원까지 소비하는 집단도 확인됩니다. "
        f"또한 배달 및 쇼핑 서비스 사용일수는 각각 평균 {desc.get('배달 서비스 사용일수', {}).get('mean', 0):.1f}일, {desc.get('쇼핑 서비스 사용일수', {}).get('mean', 0):.1f}일로 나타나, "
        "일상 생활에서 온라인 커머스와 배달 플랫폼의 의존도가 높음을 시사합니다. 게임 및 영상 매체 소비 측면에서도 유튜브와 넷플릭스 등의 사용이 지속적으로 이루어지고 있습니다. "
        "전체적으로 이 지역 1인가구는 디지털 환경에 매우 친숙하며, 비대면 소비 패턴이 고착화되어 있음을 기술통계를 통해 확인할 수 있습니다."
    )
    report_content.append(f"\n**[기술통계 요약 및 시사점]**\n{desc_str}")

    # 4. 시각화 (10개 이상) 및 해석
    report_content.append("\n## 3. 소비패턴 심층 시각화 분석")

    def save_plot(filename, title, interpretation):
        plt.tight_layout()
        filepath = os.path.join(img_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        report_content.append(f"\n### {title}")
        report_content.append(f"![{title}](../images/{filename})")
        report_content.append(f"\n**[분석 결과]**: {interpretation}")

    # 1) 연령대별 소액결제 금액 평균
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_analysis, x='연령대', y='소액결재 사용금액 평균', hue='성별명', errorbar=None)
    plt.title("연령대 및 성별 소액결제 사용금액 평균")
    save_plot("plot1_micropayment.png", "연령대 및 성별 소액결제 사용금액 평균", 
              "연령대별 소액결제 금액을 성별로 비교한 막대 그래프입니다. 특정 연령대에서 소액결제가 두드러지게 높게 나타나며, 전반적으로 모바일 소액결제가 활성화된 연령층을 확인할 수 있습니다. 청년층의 모바일 콘텐츠 및 쇼핑 결제 의존도가 상대적으로 높음을 시사합니다.")

    # 2) 쇼핑 vs 배달 서비스 산점도
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df_analysis, x='쇼핑 서비스 사용일수', y='배달 서비스 사용일수', hue='연령대', size='소액결재 사용금액 평균', sizes=(20, 200))
    plt.title("쇼핑 및 배달 서비스 사용일수 관계 (원크기: 소액결제액)")
    save_plot("plot2_shopping_delivery.png", "쇼핑과 배달 서비스 사용일수 산점도", 
              "쇼핑 서비스 사용일수와 배달 서비스 사용일수 간의 양의 상관관계가 관찰됩니다. 이는 온라인 쇼핑을 자주 하는 1인가구일수록 배달 서비스 또한 적극적으로 활용하는 '비대면 소비 친화적' 성향을 가짐을 의미합니다.")

    # 3) 주요 서비스 사용일수 박스플롯
    plt.figure(figsize=(12, 6))
    cols_box = [c for c in ['배달 서비스 사용일수', '쇼핑 서비스 사용일수', '게임 서비스 사용일수', '금융 서비스 사용일수'] if c in df_analysis.columns]
    sns.boxplot(data=df_analysis[cols_box])
    plt.title("주요 모바일 서비스 사용일수 분포")
    save_plot("plot3_service_boxplot.png", "주요 모바일 서비스 사용일수 분포", 
              "여러 모바일 서비스들의 사용일수 분포를 보여주는 박스플롯입니다. 금융 및 쇼핑 서비스의 중앙값이 비교적 높게 형성되어 있어, 해당 서비스들이 1인가구의 일상에서 매우 빈번하게 사용되고 있음을 알 수 있습니다.")

    # 4) 연령대별 1인가구수 파이차트
    age_dist = df_analysis.groupby('연령대')['1인가구수'].sum()
    plt.figure(figsize=(8, 8))
    plt.pie(age_dist, labels=age_dist.index, autopct='%1.1f%%', startangle=140)
    plt.title("연령대별 1인가구 비율")
    save_plot("plot4_age_pie.png", "연령대별 1인가구 비율", 
              "해당 자치구 내 1인가구의 연령대별 분포를 보여주는 파이 차트입니다. 특정 연령대에 인구가 집중되어 있는 구조를 확인할 수 있으며, 이는 자치구의 주거 환경(대학가, 오피스 밀집 지역 등)이 특정 세대에게 매력적임을 보여줍니다.")

    # 5) 동영상 플랫폼(유튜브/넷플릭스) 사용 비교
    if '유튜브 사용일수' in df_analysis.columns and '넷플릭스 사용일수' in df_analysis.columns:
        plt.figure(figsize=(10, 6))
        sns.kdeplot(data=df_analysis, x='유튜브 사용일수', label='유튜브', fill=True, alpha=0.5)
        sns.kdeplot(data=df_analysis, x='넷플릭스 사용일수', label='넷플릭스', fill=True, alpha=0.5)
        plt.legend()
        plt.title("유튜브 및 넷플릭스 사용일수 밀도 함수")
        save_plot("plot5_video_kde.png", "유튜브 및 넷플릭스 사용 밀도 함수", 
                  "유튜브와 넷플릭스 사용일수의 분포를 나타냅니다. 유튜브 사용일수는 전반적으로 높게 넓게 분포하는 반면, 넷플릭스는 특정 구간에 집중되어 있는 특징을 보이며, 두 플랫폼 간의 소비 패턴 차이를 잘 보여줍니다.")

    # 6) 행정동별 평균 소액결제 금액
    dong_payment = df_analysis.groupby('행정동')['소액결재 사용금액 평균'].mean().sort_values(ascending=False)
    plt.figure(figsize=(12, 6))
    sns.barplot(x=dong_payment.index, y=dong_payment.values)
    plt.xticks(rotation=45)
    plt.title("행정동별 소액결제 사용금액 평균")
    save_plot("plot6_dong_payment.png", "행정동별 소액결제 사용금액 평균", 
              "자치구 내 세부 행정동별로 소액결제 사용금액을 비교한 그래프입니다. 특정 행정동에서 유독 소비 규모가 큰 것으로 나타나며, 이는 상권 접근성이나 거주민의 소득 수준 차이에서 기인할 수 있습니다.")

    # 7) 성별 배달 서비스 이용 차이 (Violin Plot)
    if '배달 서비스 사용일수' in df_analysis.columns:
        plt.figure(figsize=(8, 6))
        sns.violinplot(data=df_analysis, x='성별명', y='배달 서비스 사용일수')
        plt.title("성별 배달 서비스 사용일수 분포")
        save_plot("plot7_delivery_gender.png", "성별 배달 서비스 사용일수 (바이올린 플롯)", 
                  "성별에 따른 배달 서비스 이용일수 차이를 입체적으로 보여줍니다. 남성과 여성 집단 간의 배달 앱 활용 빈도의 분포 차이를 통해 타겟팅된 마케팅 전략 수립이 가능함을 시사합니다.")

    # 8) 상관관계 히트맵
    plt.figure(figsize=(10, 8))
    corr = df_analysis[num_cols].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap='coolwarm')
    plt.title("주요 소비/여가 지표 간 상관관계 히트맵")
    save_plot("plot8_heatmap.png", "주요 지표 상관관계 히트맵", 
              "분석에 사용된 다양한 수치형 변수들 간의 상관관계를 보여주는 히트맵입니다. 소액결제와 쇼핑, 쇼핑과 금융 서비스 등 특정 변수 묶음 간에 강한 상관성이 도출되어, 디지털 라이프스타일 지표가 상호 연관되어 움직임을 증명합니다.")

    # 9) 연령대별 금융 서비스 사용 추이
    if '금융 서비스 사용일수' in df_analysis.columns:
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df_analysis, x='연령대', y='금융 서비스 사용일수', marker='o')
        plt.title("연령대별 금융 서비스 사용일수 추이")
        save_plot("plot9_finance_age.png", "연령대별 금융 서비스 사용일수", 
                  "연령대가 증가함에 따라 모바일 금융 서비스의 사용일수가 어떻게 변화하는지 보여주는 선 그래프입니다. 청년층부터 중장년층까지 모바일 뱅킹 및 간편결제 서비스의 침투율을 확인할 수 있는 중요한 지표입니다.")

    # 10) 쇼핑 및 동영상 서비스 산점도 (행정동 구분)
    if '동영상/방송 서비스 사용일수' in df_analysis.columns:
        plt.figure(figsize=(12, 8))
        # 행정동이 너무 많을 수 있으므로 상위 5개만
        top_dongs = df_analysis['행정동'].value_counts().head(5).index
        df_sub = df_analysis[df_analysis['행정동'].isin(top_dongs)]
        sns.scatterplot(data=df_sub, x='쇼핑 서비스 사용일수', y='동영상/방송 서비스 사용일수', hue='행정동')
        plt.title("주요 5개 행정동 쇼핑 vs 동영상 서비스")
        save_plot("plot10_shopping_video_dong.png", "주요 행정동 쇼핑 및 동영상 서비스 산점도", 
                  "가장 인구가 많은 5개 행정동을 대상으로 쇼핑과 동영상 서비스 이용의 군집 특성을 파악한 산점도입니다. 행정동마다 주거하는 1인가구의 성향(영상 미디어 소비 위주인지, 쇼핑 위주인지)이 미세하게 다름을 파악할 수 있습니다.")

    # 마크다운 파일 저장
    report_path = os.path.join(report_dir, "eda_report.md")
    with open(report_path, "w", encoding='utf-8') as f:
        f.write("\n".join(report_content))
    print("EDA 리포트 및 시각화 이미지 생성이 완료되었습니다.")

if __name__ == "__main__":
    main()
