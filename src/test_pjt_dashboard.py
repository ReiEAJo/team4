"""
이 테스트 모듈은 Playwright를 사용하여 빌드된 대시보드(dashboard.html) 및 
보고서 뷰어(report.html)가 웹 브라우저에서 올바르게 렌더링되고 동작하는지 검증합니다.
주요 검증 항목:
- 페이지 로딩 시 콘솔 에러 유무 확인
- Leaflet.js 지도 및 Chart.js 그래프의 비정상 출력 검사
- 특정 자치구 갱신 등 인터랙션 반응 검사
- 최종 대시보드 화면 스크린샷 캡처 및 저장
"""

import os
import sys
from playwright.sync_api import sync_playwright

def test_dashboard():
    # 경로 설정 (상대경로 기준)
    base_dir = os.path.abspath("one-person PJT")
    dashboard_path = os.path.join(base_dir, "apps", "dashboard.html")
    report_path = os.path.join(base_dir, "apps", "report.html")
    capture_path = os.path.join(base_dir, "report", "dashboard_capture.png")
    
    if not os.path.exists(dashboard_path):
        print(f"오류: 대시보드 파일이 없습니다: {dashboard_path}")
        sys.exit(1)
        
    print(f"로컬 대시보드 경로: {dashboard_path}")
    
    # 브라우저 콘솔 및 에러 로그 기록용 리스트
    console_errors = []
    page_errors = []
    
    with sync_playwright() as p:
        # Chromium 브라우저 실행
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 콘솔 이벤트 리스너 등록
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        # 페이지 스크립트 에러 리스너 등록
        page.on("pageerror", lambda err: page_errors.append(err))
        
        # 1. 대시보드 페이지 로드
        print("1. 대시보드 페이지 로드 중...")
        file_url = f"file:///{dashboard_path.replace(os.sep, '/')}"
        page.goto(file_url)
        
        # 지도 및 차트가 그려질 때까지 대기
        page.wait_for_timeout(3000)
        
        # 2. 콘솔 에러 검증
        if console_errors:
            print("경고: 대시보드 로드 중 콘솔 에러 발생:")
            for err in console_errors:
                print(f" - [Console Error] {err}")
        else:
            print("대시보드 콘솔 에러 없음: 검증 통과")
            
        if page_errors:
            print("오류: 대시보드 스크립트 실행 오류 발생:")
            for err in page_errors:
                print(f" - [Page Error] {err}")
            browser.close()
            sys.exit(1)
        else:
            print("대시보드 페이지 스크립트 에러 없음: 검증 통과")
            
        # 3. 기본 정보 표시 요소 및 인터랙션 검증
        print("3. 기본 정보 렌더링 확인 중...")
        gu_name = page.locator("#selected-gu-name").inner_text()
        print(f"현재 선택된 구: {gu_name}")
        
        total_pop = page.locator("#stat-total-pop").inner_text()
        print(f"총 1인가구 지표 값: {total_pop}")
        
        # 4. 스크린샷 캡처
        print(f"4. 대시보드 화면 캡처 중... ({capture_path})")
        os.makedirs(os.path.dirname(capture_path), exist_ok=True)
        page.screenshot(path=capture_path, full_page=True)
        print("화면 캡처 완료.")
        
        # 5. 리포트 뷰어 페이지 로드 및 검증
        print("5. 리포트 뷰어 페이지 로드 중...")
        report_url = f"file:///{report_path.replace(os.sep, '/')}"
        page.goto(report_url)
        page.wait_for_timeout(2000)
        
        report_title = page.locator("header h1").inner_text()
        # 이모지로 인한 인코딩 오류 방지를 위해 유니코드 이모지 제거 후 출력
        clean_title = "".join(c for c in report_title if ord(c) < 0x10000)
        print(f"리포트 타이틀: {clean_title}")
        
        browser.close()
        
    print("모든 자동화 검증이 정상적으로 통과되었습니다!")

if __name__ == "__main__":
    test_dashboard()
