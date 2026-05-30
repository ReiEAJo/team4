"""
이 임시 모듈은 one-person PJT/data 폴더에 있는 주요 CSV 파일들의
인코딩(cp949 vs utf-8)을 확인하고 컬럼명을 출력하여 분석을 지원합니다.
"""

import os
import pandas as pd

def check_files():
    data_dir = 'one-person PJT/data'
    files = [
        '행정안전부_지역별(행정동) 성별 연령별 주민등록 1인세대수_20260430.csv',
        '서울시 상권분석서비스(소비-행정동).csv',
        '서울시 상권분석서비스(점포-행정동)_2024년.csv'
    ]
    
    out_lines = []
    for f in files:
        path = os.path.join(data_dir, f)
        if not os.path.exists(path):
            out_lines.append(f"파일 없음: {path}\n")
            continue
            
        out_lines.append(f"=== {f} ===")
        # cp949 시도
        try:
            df = pd.read_csv(path, encoding='cp949', nrows=5)
            out_lines.append("Encoding: cp949")
            out_lines.append(f"Columns: {df.columns.tolist()}")
            out_lines.append(df.head(2).to_string())
        except Exception as e1:
            # utf-8 시도
            try:
                df = pd.read_csv(path, encoding='utf-8', nrows=5)
                out_lines.append("Encoding: utf-8")
                out_lines.append(f"Columns: {df.columns.tolist()}")
                out_lines.append(df.head(2).to_string())
            except Exception as e2:
                out_lines.append(f"Error reading with both cp949 and utf-8:\nCP949 Error: {e1}\nUTF-8 Error: {e2}")
        out_lines.append("\n")
        
    os.makedirs('one-person PJT/report', exist_ok=True)
    with open('one-person PJT/report/check_output.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(out_lines))
    print("진단 완료! check_output.txt에 기록되었습니다.")

if __name__ == '__main__':
    check_files()
