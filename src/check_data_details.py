"""
이 스크립트는 서울시 1인가구 주민등록 데이터, 소비 데이터, 점포 데이터를 로드하여
자치구 코드 매핑 상태와 기준 년분기, 데이터 유효성 등을 분석하고 보고서에 필요한 통계를 검증합니다.
"""

import os
import pandas as pd

def analyze():
    # 경로 설정 (상대경로 준수)
    data_dir = 'one-person PJT/data'
    output_path = 'one-person PJT/report/data_details_summary.txt'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    out = []
    
    # 1. 1인 세대수 데이터 확인
    pop_file = os.path.join(data_dir, '행정안전부_지역별(행정동) 성별 연령별 주민등록 1인세대수_20260430.csv')
    if os.path.exists(pop_file):
        df_pop = pd.read_csv(pop_file, encoding='cp949')
        df_pop_seoul = df_pop[df_pop['시도명'] == '서울특별시'].copy()
        
        # 자치구 코드 추출 (행정기관코드는 10자리이며 앞 5자리가 구 코드)
        df_pop_seoul['자치구_코드'] = df_pop_seoul['행정기관코드'].astype(str).str[:5]
        
        out.append("=== 주민등록 1인세대수 데이터 (서울) ===")
        out.append(f"서울 행정동 수: {len(df_pop_seoul)}")
        
        # 구별 1인세대수 합계
        gu_pop = df_pop_seoul.groupby(['자치구_코드', '시군구명'])['계'].sum().reset_index()
        gu_pop_sorted = gu_pop.sort_values(by='계', ascending=False)
        out.append("구별 1인세대수 상위 5:")
        out.append(gu_pop_sorted.head(5).to_string(index=False))
        out.append("\n구별 1인세대수 하위 5:")
        out.append(gu_pop_sorted.tail(5).to_string(index=False))
        out.append("-" * 50)
    else:
        out.append(f"주민등록 데이터 없음: {pop_file}")
        
    # 2. 소비 데이터 확인
    spend_file = os.path.join(data_dir, '서울시 상권분석서비스(소비-행정동).csv')
    if os.path.exists(spend_file):
        df_spend = pd.read_csv(spend_file, encoding='cp949')
        out.append("\n=== 소비-행정동 데이터 ===")
        out.append(f"전체 행 수: {len(df_spend)}")
        out.append(f"기준_년분기_코드 종류: {df_spend['기준_년분기_코드'].unique().tolist()}")
        
        # 최신 분기 데이터 필터링
        latest_quarter = df_spend['기준_년분기_코드'].max()
        out.append(f"최신 분기: {latest_quarter}")
        df_spend_latest = df_spend[df_spend['기준_년분기_코드'] == latest_quarter].copy()
        df_spend_latest['자치구_코드'] = df_spend_latest['행정동_코드'].astype(str).str[:5]
        
        gu_spend = df_spend_latest.groupby('자치구_코드')['지출_총금액'].sum().reset_index()
        out.append("구별 지출 총금액 상위 5:")
        out.append(gu_spend.sort_values(by='지출_총금액', ascending=False).head(5).to_string(index=False))
        out.append("-" * 50)
    else:
        out.append(f"소비 데이터 없음: {spend_file}")
        
    # 3. 점포 데이터 확인
    store_file = os.path.join(data_dir, '서울시 상권분석서비스(점포-행정동)_2024년.csv')
    if os.path.exists(store_file):
        df_store = pd.read_csv(store_file, encoding='cp949')
        out.append("\n=== 점포-행정동 2024년 데이터 ===")
        out.append(f"전체 행 수: {len(df_store)}")
        out.append(f"기준_년분기_코드 종류: {df_store['기준_년분기_코드'].unique().tolist()}")
        
        latest_store_q = df_store['기준_년분기_코드'].max()
        out.append(f"최신 분기: {latest_store_q}")
        
        # 업종 리스트 확인
        services = df_store['서비스_업종_코드_명'].unique().tolist()
        out.append(f"서비스 업종 수: {len(services)}")
        out.append(f"일부 업종 예시: {services[:10]}")
        out.append("-" * 50)
    else:
        out.append(f"점포 데이터 없음: {store_file}")
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(out))
    print(f"상세 분석 결과가 {output_path} 에 저장되었습니다.")

if __name__ == '__main__':
    analyze()
