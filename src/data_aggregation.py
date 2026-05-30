"""
이 스크립트는 서울특별시 자치구별 1인가구 데이터(성별, 연령대별), 소비 데이터, 
그리고 점포 및 폐업률 데이터를 병합하고 분석하여 비즈니스 추천을 위한 핵심 통계를 산출합니다.
"""

import os
import pandas as pd
import json

def aggregate_data():
    data_dir = 'one-person PJT'
    data_path = os.path.join(data_dir, 'data')
    report_path = os.path.join(data_dir, 'report')
    os.makedirs(report_path, exist_ok=True)
    
    # 1. 1인가구 인구 데이터 가공
    pop_file = os.path.join(data_path, '행정안전부_지역별(행정동) 성별 연령별 주민등록 1인세대수_20260430.csv')
    df_pop = pd.read_csv(pop_file, encoding='cp949')
    
    # 서울특별시 필터링
    df_pop_seoul = df_pop[df_pop['시도명'] == '서울특별시'].copy()
    df_pop_seoul['자치구_코드'] = df_pop_seoul['행정기관코드'].astype(str).str[:5]
    
    # 연령대 컬럼 정의
    # 청년층 (20~39세)
    youth_cols = [f"{i}세남자" for i in range(20, 40)] + [f"{i}세여자" for i in range(20, 40)]
    # 중년층 (40~59세)
    middle_cols = [f"{i}세남자" for i in range(40, 60)] + [f"{i}세여자" for i in range(40, 60)]
    # 장년/노년층 (60세 이상)
    elder_cols = (
        [f"{i}세남자" for i in range(60, 110)] + ['110세이상 남자'] +
        [f"{i}세여자" for i in range(60, 110)] + ['110세이상 여자']
    )
    
    # 숫자로 변환
    for c in youth_cols + middle_cols + elder_cols + ['남자', '여자', '계']:
        df_pop_seoul[c] = pd.to_numeric(df_pop_seoul[c], errors='coerce').fillna(0)
        
    df_pop_seoul['청년_1인'] = df_pop_seoul[youth_cols].sum(axis=1)
    df_pop_seoul['중년_1인'] = df_pop_seoul[middle_cols].sum(axis=1)
    df_pop_seoul['장년_1인'] = df_pop_seoul[elder_cols].sum(axis=1)
    
    # 구별 집계
    gu_pop = df_pop_seoul.groupby(['자치구_코드', '시군구명']).agg({
        '계': 'sum',
        '남자': 'sum',
        '여자': 'sum',
        '청년_1인': 'sum',
        '중년_1인': 'sum',
        '장년_1인': 'sum'
    }).reset_index()
    
    gu_pop.rename(columns={'계': '총_1인가구수', '남자': '남성_1인', '여자': '여성_1인'}, inplace=True)
    
    # 2. 소비 데이터 가공 (2025년 4분기 기준)
    spend_file = os.path.join(data_path, '서울시 상권분석서비스(소비-행정동).csv')
    df_spend = pd.read_csv(spend_file, encoding='cp949')
    
    # 최신 분기 필터링 (20254)
    latest_quarter = df_spend['기준_년분기_코드'].max()
    df_spend_latest = df_spend[df_spend['기준_년분기_코드'] == latest_quarter].copy()
    df_spend_latest['자치구_코드'] = df_spend_latest['행정동_코드'].astype(str).str[:5]
    
    # 지출 항목들
    spend_cols = [
        '지출_총금액', '식료품_지출_총금액', '의류_신발_지출_총금액', '생활용품_지출_총금액',
        '의료비_지출_총금액', '교통_지출_총금액', '교육_지출_총금액', '유흥_지출_총금액',
        '여가_문화_지출_총금액', '기타_지출_총금액', '음식_지출_총금액'
    ]
    for c in spend_cols:
        df_spend_latest[c] = pd.to_numeric(df_spend_latest[c], errors='coerce').fillna(0)
        
    # 구별 소비 집계 (합산)
    gu_spend = df_spend_latest.groupby('자치구_코드')[spend_cols].sum().reset_index()
    
    # 3. 점포 및 폐업률 데이터 가공 (2024년 4분기 기준)
    store_file = os.path.join(data_path, '서울시 상권분석서비스(점포-행정동)_2024년.csv')
    df_store = pd.read_csv(store_file, encoding='cp949')
    
    # 최신 분기 필터링 (20244)
    latest_store_q = df_store['기준_년분기_코드'].max()
    df_store_latest = df_store[df_store['기준_년분기_코드'] == latest_store_q].copy()
    df_store_latest['자치구_코드'] = df_store_latest['행정동_코드'].astype(str).str[:5]
    
    # 숫자 형변환
    for c in ['점포_수', '유사_업종_점포_수', '개업_점포_수', '폐업_점포_수']:
        df_store_latest[c] = pd.to_numeric(df_store_latest[c], errors='coerce').fillna(0)
        
    # 자치구별 전체 점포 수 및 폐업 점포 수 집계하여 구별 평균 폐업률 계산
    gu_store = df_store_latest.groupby('자치구_코드').agg({
        '점포_수': 'sum',
        '폐업_점포_su' if '폐업_점포_su' in df_store_latest.columns else '폐업_점포_수': 'sum',
        '유사_업종_점포_수': 'sum'
    }).reset_index()
    
    # 컬럼명 통일
    p_col = '폐업_점포_수'
    gu_store.rename(columns={p_col: '총_폐업점포수'}, inplace=True)
    gu_store['평균_폐업률'] = (gu_store['총_폐업점포수'] / gu_store['유사_업종_점포_수'] * 100).round(2)
    
    # 자치구별 업종별 폐업률 계산 (추천시 사용)
    # 업종별로 자치구 코드와 묶어서 폐업률 계산
    gu_sector_store = df_store_latest.groupby(['자치구_코드', '서비스_업종_코드_명']).agg({
        '점포_수': 'sum',
        '폐업_점포_수': 'sum',
        '유사_업종_점포_수': 'sum'
    }).reset_index()
    gu_sector_store['업종_폐업률'] = (gu_sector_store['폐업_점포_수'] / gu_sector_store['유사_업종_점포_수'] * 100).round(2)
    
    # 4. 데이터 병합 (주민등록 + 소비 + 점포)
    merged = pd.merge(gu_pop, gu_spend, on='자치구_코드', how='inner')
    merged = pd.merge(merged, gu_store[['자치구_코드', '점포_수', '총_폐업점포수', '평균_폐업률']], on='자치구_코드', how='inner')
    
    # 자치구 코드 정수 변환 및 정렬
    merged['자치구_코드_int'] = merged['자치구_코드'].astype(int)
    merged.sort_values(by='자치구_코드_int', inplace=True)
    merged.drop(columns=['자치구_코드_int'], inplace=True)
    
    # 핵심 인사이트 추출
    # 4-1. 1인가구 최다 거주 자치구
    top_pop_gu = merged.sort_values(by='총_1인가구수', ascending=False).iloc[0]
    top_pop_code = top_pop_gu['자치구_코드']
    top_pop_name = top_pop_gu['시군구명']
    
    # 4-2. 1인가구 거주수는 적지만 소비지출액이 높은 자치구
    # 1인가구수 하위 50% 중 지출_총금액이 가장 높은 자치구 찾기
    median_pop = merged['총_1인가구수'].median()
    low_pop_high_spend = merged[merged['총_1인가구수'] < median_pop].sort_values(by='지출_총금액', ascending=False).iloc[0]
    low_pop_code = low_pop_high_spend['자치구_코드']
    low_pop_name = low_pop_high_spend['시군구명']
    
    # 4-3. 중장년층(40-59세) 1인가구 최다 거주 자치구
    top_middle_gu = merged.sort_values(by='중년_1인', ascending=False).iloc[0]
    top_middle_code = top_middle_gu['자치구_코드']
    top_middle_name = top_middle_gu['시군구명']
    
    # 파일 저장 (JSON)
    result_data = {
        'districts': merged.to_dict(orient='records'),
        'top_pop_district': {
            'code': top_pop_code,
            'name': top_pop_name,
            'pop_count': int(top_pop_gu['총_1인가구수']),
            'spend_total': float(top_pop_gu['지출_총금액'])
        },
        'low_pop_high_spend_district': {
            'code': low_pop_code,
            'name': low_pop_name,
            'pop_count': int(low_pop_high_spend['총_1인가구수']),
            'spend_total': float(low_pop_high_spend['지출_총금액'])
        },
        'top_middle_age_district': {
            'code': top_middle_code,
            'name': top_middle_name,
            'middle_pop_count': int(top_middle_gu['중년_1인']),
            'spend_total': float(top_middle_gu['지출_총금액'])
        }
    }
    
    with open(os.path.join(report_path, 'summary_analysis.json'), 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
        
    # 각 자치구별 업종별 폐업률도 저장
    gu_sector_store.to_json(os.path.join(report_path, 'district_sectors.json'), orient='records', force_ascii=False, indent=4)
    
    # 텍스트로 요약 결과 기록
    summary_text = f"""=== 서울시 1인가구 및 소비 분석 핵심 통계 요약 ===
1. 1인가구 최다 거주 자치구: {top_pop_name} (코드: {top_pop_code}, 1인가구수: {top_pop_gu['총_1인가구수']:,}명, 평균 폐업률: {top_pop_gu['평균_폐업률']}%)
2. 1인가구 저밀도-고지출 자치구: {low_pop_name} (코드: {low_pop_code}, 1인가구수: {low_pop_high_spend['총_1인가구수']:,}명, 지출 총금액: {low_pop_high_spend['지출_총금액']:,}원)
3. 중장년층(40-59세) 1인가구 최다 거주 자치구: {top_middle_name} (코드: {top_middle_code}, 중장년 1인가구수: {top_middle_gu['중년_1인']:,}명, 평균 폐업률: {top_middle_gu['평균_폐업률']}%)

각 구별 성별 비율:
- {top_pop_name}: 남성 {top_pop_gu['남성_1인']:,}명, 여성 {top_pop_gu['여성_1인']:,}명
- {low_pop_name}: 남성 {low_pop_high_spend['남성_1인']:,}명, 여성 {low_pop_high_spend['여성_1인']:,}명
- {top_middle_name}: 남성 {top_middle_gu['남성_1인']:,}명, 여성 {top_middle_gu['여성_1인']:,}명
"""
    with open(os.path.join(report_path, 'summary_analysis_text.txt'), 'w', encoding='utf-8') as f:
        f.write(summary_text)
        
    print("데이터 병합 및 요약 분석이 성공적으로 완료되었습니다!")

if __name__ == '__main__':
    aggregate_data()
