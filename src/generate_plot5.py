"""
이 모듈은 핵심 소비 카테고리 비중(plot5) 파이차트를 생성합니다.
테이블 내용(여가_문화 58.55%)과 정확히 일치하도록 시각화합니다.
"""
import matplotlib.pyplot as plt
import os
import matplotlib.font_manager as fm

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 데이터 (테이블 기반)
categories = ['여가/문화', '의료비', '기타', '음식', '식료품', '생활용품', '의류/신발', '교육', '유흥', '교통']
sizes = [58.55, 10.24, 8.88, 8.52, 5.44, 2.23, 2.05, 1.74, 1.39, 0.96]
colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0', '#ffb3e6', '#c4e17f', '#76d7ea', '#ffb3a7', '#d9d9d9']

# 상위 5개와 나머지 '기타'로 묶기
labels = ['여가/문화', '의료비', '기타(원데이터)', '음식', '식료품', '기타(그 외)']
sizes_grouped = [58.55, 10.24, 8.88, 8.52, 5.44, sum(sizes[5:])]
colors_grouped = ['#ff9999', '#66b3ff', '#d9d9d9', '#ffcc99', '#c2c2f0', '#e0e0e0']
explode = (0.05, 0, 0, 0, 0, 0)

fig, ax = plt.subplots(figsize=(10, 8))
wedges, texts, autotexts = ax.pie(sizes_grouped, explode=explode, labels=labels, colors=colors_grouped,
                                  autopct='%1.1f%%', shadow=True, startangle=140,
                                  textprops=dict(color="black", fontsize=12))

plt.setp(autotexts, size=11, weight="bold")
ax.set_title("1인가구 상권 핵심 소비 카테고리 비중", fontsize=16)

os.makedirs('images', exist_ok=True)
plt.savefig('images/plot5.png', dpi=300, bbox_inches='tight')
plt.close()
print("plot5.png generated successfully.")
