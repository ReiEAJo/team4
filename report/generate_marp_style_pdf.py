"""
이 모듈은 Marp 마크다운 형식의 슬라이드 문서를 파이썬 환경에서 HTML로 변환한 뒤,
Playwright를 이용해 PDF 파일로 렌더링하는 역할을 합니다.
주요 기능:
- Marp 프론트매터 및 슬라이드 구분자(`---`) 파싱
- Marp Uncover 테마와 유사한 슬라이드 전용 CSS 주입
- Playwright를 통한 A4 가로(Landscape) 슬라이드 PDF 변환
"""
import os
import markdown
import re
from playwright.sync_api import sync_playwright
from pathlib import Path

def create_marp_style_pdf():
    # 1. Read the Marp Markdown
    current_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(current_dir, 'presentation.md')
    pdf_path = os.path.join(current_dir, 'presentation_marp_style.pdf')
    html_path = os.path.join(current_dir, 'temp_marp.html')
    
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 2. Extract slides separated by '---'
    # Remove frontmatter
    content = re.sub(r'^---.*?---\n', '', content, flags=re.DOTALL)
    
    raw_slides = content.split('\n---\n')
    
    # 3. Generate HTML per slide
    html_slides = ""
    for slide in raw_slides:
        if not slide.strip():
            continue
            
        # Extract class directives like <!-- _class: lead -->
        classes = ["slide"]
        class_match = re.search(r'<!--\s*_class:\s*(.*?)\s*-->', slide)
        if class_match:
            classes.extend(class_match.group(1).split())
            slide = slide.replace(class_match.group(0), '')
            
        # Convert MD to HTML
        slide_html = markdown.markdown(slide, extensions=['tables'])
        
        # Build section
        class_str = " ".join(classes)
        html_slides += f'<section class="{class_str}"><div class="content">{slide_html}</div></section>'

    # 4. Wrap with Marp-like CSS
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
            
            html, body {{
                margin: 0;
                padding: 0;
                background-color: #333;
                font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
            }}
            
            section.slide {{
                width: 1280px;
                height: 720px;
                background-color: #ffffff;
                color: #2d3436;
                position: relative;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: flex-start;
                padding: 60px 80px;
                box-sizing: border-box;
                page-break-after: always;
                margin: 0 auto;
                overflow: hidden;
            }}
            
            .content {{
                width: 100%;
                font-size: 26px;
                line-height: 1.6;
            }}
            
            h1 {{
                color: #1E2761;
                font-size: 52px;
                font-weight: 900;
                border-bottom: 4px solid #F96167;
                padding-bottom: 10px;
                margin-top: 0;
                margin-bottom: 30px;
            }}
            
            h2 {{
                color: #1E2761;
                font-size: 38px;
                margin-bottom: 20px;
            }}
            
            h3 {{
                color: #F96167;
                font-size: 28px;
            }}
            
            /* Lead Slide */
            section.lead {{
                background-color: #1E2761;
                color: #ffffff;
                align-items: center;
                text-align: center;
            }}
            section.lead h1 {{
                color: #ffffff;
                border-bottom: 6px solid #F9E795;
                border-bottom-width: 5px;
            }}
            section.lead h2, section.lead h3, section.lead p {{
                color: #F9E795;
            }}
            
            /* Divider Slide */
            section.divider {{
                background-color: #2c3e50;
                color: #ffffff;
                align-items: center;
                text-align: center;
            }}
            section.divider h2 {{
                color: #ffffff;
                font-size: 60px;
                border-bottom: 3px solid #F96167;
                padding-bottom: 20px;
                display: inline-block;
            }}
            
            ul, ol {{
                margin-left: 20px;
            }}
            li {{
                margin-bottom: 12px;
            }}
            strong {{
                color: #e74c3c;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th {{
                background-color: #1E2761;
                color: #ffffff;
                padding: 15px;
                font-size: 24px;
            }}
            td {{
                padding: 15px;
                border: 1px solid #ddd;
                text-align: center;
                font-size: 22px;
            }}
            
            blockquote {{
                border-left: 8px solid #F9E795;
                background: #f0f4f8;
                padding: 20px 30px;
                margin: 30px 0;
                border-radius: 8px;
                color: #2c3e50;
                font-weight: 700;
            }}
            
            img {{
                max-width: 90%;
                height: auto;
                max-height: 400px;
                display: block;
                margin: 30px auto;
                border-radius: 8px;
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        {html_slides}
    </body>
    </html>
    """
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
        
    print(f"HTML saved to {html_path}")
    print("Generating PDF using Playwright...")

    file_uri = Path(html_path).as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(file_uri)
        # Wait for fonts and images
        page.wait_for_timeout(3000)
        # Print to landscape PDF matching 16:9 1280x720 (Approx 13.3 x 7.5 inches)
        page.pdf(path=pdf_path, width="13.33in", height="7.5in", print_background=True, margin={'top':'0', 'bottom':'0', 'left':'0', 'right':'0'})
        browser.close()
        
    print(f"PDF successfully generated at {pdf_path}")

if __name__ == "__main__":
    create_marp_style_pdf()
