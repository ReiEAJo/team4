"""
이 모듈은 관악구 1인가구 소비패턴 데이터를 바탕으로
정적 웹 브라우저 환경에서 볼 수 있는 단일 HTML 대시보드 파일을 생성합니다.
Streamlit 서버 없이도 Plotly의 인터랙티브 차트를 HTML 문서에서 확인할 수 있습니다.
"""

import pandas as pd
import plotly.express as px
import os

def create_html_dashboard():
    base_dir = r"c:\Users\Rei EA Jo\Downloads\icb10\one-person PJT"
    file_path = os.path.join(base_dir, "data", "2025.12월_29개 통신정보 (1).xlsx")
    html_out_path = os.path.join(base_dir, "report", "dashboard.html")
    
    # 데이터 로딩 및 전처리 (관악구 필터링)
    df = pd.read_excel(file_path)
    df_gwanak = df[df['자치구'] == '관악구'].copy()
    df_gwanak['성별명'] = df_gwanak['성별'].map({1: '남성', 2: '여성'}).fillna('기타')
    
    cols_to_numeric = [
        '소액결재 사용금액 평균', '배달 서비스 사용일수', '쇼핑 서비스 사용일수',
        '동영상/방송 서비스 사용일수', '게임 서비스 사용일수'
    ]
    
    available_cols = {}
    for c in cols_to_numeric:
        for col in df_gwanak.columns:
            if c.replace(' ', '') in col.replace(' ', ''):
                available_cols[c] = col
                df_gwanak[col] = pd.to_numeric(df_gwanak[col], errors='coerce').fillna(0)
                break

    col_pay = available_cols.get('소액결재 사용금액 평균')
    col_del = available_cols.get('배달 서비스 사용일수')
    col_shop = available_cols.get('쇼핑 서비스 사용일수')
    col_video = available_cols.get('동영상/방송 서비스 사용일수')
    col_game = available_cols.get('게임 서비스 사용일수')

    # 차트 생성 1: 연령대별 소액결제 금액 (Plotly)
    html_charts = ""
    
    if col_pay:
        fig_pay_age = px.bar(
            df_gwanak.groupby(['연령대', '성별명'], as_index=False)[col_pay].mean(),
            x='연령대', y=col_pay, color='성별명', barmode='group',
            title="연령대별 소액결제 평균 (성별 비교)",
            labels={col_pay: "소액결제 금액(원)"}
        )
        html_charts += fig_pay_age.to_html(full_html=False, include_plotlyjs='cdn')
        
        dong_pay = df_gwanak.groupby('행정동', as_index=False)[col_pay].mean().sort_values(by=col_pay, ascending=False)
        fig_pay_dong = px.bar(
            dong_pay, x='행정동', y=col_pay,
            title="행정동별 평균 소액결제 금액",
            color=col_pay, color_continuous_scale='Blues'
        )
        html_charts += fig_pay_dong.to_html(full_html=False, include_plotlyjs=False)

    if col_del and col_shop:
        fig_scatter = px.scatter(
            df_gwanak, x=col_shop, y=col_del,
            color='연령대', size=col_pay if col_pay else None, hover_name='행정동',
            title="쇼핑 vs 배달 서비스 이용 분포",
            labels={col_shop: "쇼핑 서비스 일수", col_del: "배달 서비스 일수"}
        )
        html_charts += fig_scatter.to_html(full_html=False, include_plotlyjs=False)

    service_cols = [c for c in [col_del, col_shop, col_video, col_game] if c is not None]
    if service_cols:
        df_melted = df_gwanak.melt(id_vars=['연령대'], value_vars=service_cols, var_name='서비스', value_name='사용일수')
        fig_box = px.box(
            df_melted, x='서비스', y='사용일수', color='서비스',
            title="서비스별 이용 일수 분포"
        )
        html_charts += fig_box.to_html(full_html=False, include_plotlyjs=False)

    # KPI 수치
    avg_pay = df_gwanak[col_pay].mean() if col_pay else 0
    avg_del = df_gwanak[col_del].mean() if col_del else 0
    avg_shop = df_gwanak[col_shop].mean() if col_shop else 0

    # HTML 템플릿 생성
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>관악구 1인가구 소비패턴 대시보드</title>
        <style>
            body {{ font-family: "Malgun Gothic", sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 15px; }}
            .kpi-container {{ display: flex; justify-content: space-around; margin: 30px 0; }}
            .kpi-box {{ background: #ebf5fb; padding: 20px; border-radius: 8px; text-align: center; width: 30%; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .kpi-value {{ font-size: 28px; font-weight: bold; color: #2980b9; margin-top: 10px; }}
            .kpi-title {{ font-size: 16px; color: #7f8c8d; }}
            .chart-wrapper {{ margin-bottom: 40px; border: 1px solid #ecf0f1; border-radius: 5px; padding: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 관악구 1인가구 소비패턴 HTML 대시보드</h1>
            <p style="text-align: center; color: #7f8c8d;">2025년 12월 29개 통신정보 데이터 기반 (Python & Plotly 생성)</p>
            
            <div class="kpi-container">
                <div class="kpi-box">
                    <div class="kpi-title">평균 소액결제 금액</div>
                    <div class="kpi-value">{avg_pay:,.0f} 원</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-title">평균 배달 사용일수</div>
                    <div class="kpi-value">{avg_del:,.1f} 일</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-title">평균 쇼핑 사용일수</div>
                    <div class="kpi-value">{avg_shop:,.1f} 일</div>
                </div>
            </div>

            <div class="charts-container">
                {html_charts}
            </div>
        </div>
    </body>
    </html>
    """

    with open(html_out_path, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print(f"HTML dashboard generated at: {html_out_path}")

if __name__ == "__main__":
    create_html_dashboard()
