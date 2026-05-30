"""
마크다운 문서를 PDF로 변환하는 스크립트입니다.
로컬 이미지 경로 문제로 이미지가 PDF에 표시되지 않는 현상을 방지하기 위해,
이미지 파일을 Base64 문자열로 직접 인코딩하여 HTML 내에 삽입한 후 PDF로 렌더링합니다.
"""

import os
import re
import base64
import markdown
from playwright.sync_api import sync_playwright

def encode_image_to_base64(filepath):
    try:
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        print(f"Error encoding {filepath}: {e}")
        return ""

def convert_md_to_pdf(md_path, pdf_path, img_base_dir):
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # 정규표현식을 사용해 마크다운 이미지 구문을 찾음: ![alt text](../images/filename.png)
    # 이미지 경로를 base64 데이터로 치환
    def replace_image(match):
        alt_text = match.group(1)
        rel_path = match.group(2)
        # ../images/filename.png -> filename.png 추출
        filename = os.path.basename(rel_path)
        img_full_path = os.path.join(img_base_dir, filename)
        
        base64_data = encode_image_to_base64(img_full_path)
        if base64_data:
            # HTML img 태그로 치환하여 직접 삽입
            return f'<img src="{base64_data}" alt="{alt_text}" />'
        return match.group(0) # 실패 시 원본 반환

    md_text_with_base64 = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image, md_text)

    # 마크다운을 HTML로 변환
    html_body = markdown.markdown(md_text_with_base64, extensions=['tables'])

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
                line-height: 1.6;
                color: #333;
                padding: 20px;
                max-width: 800px;
                margin: 0 auto;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
                font-size: 11px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: right;
            }}
            th {{
                background-color: #f2f2f2;
                font-weight: bold;
                text-align: center;
            }}
            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 20px auto;
                border: 1px solid #ddd;
            }}
            h1, h2, h3 {{
                color: #2c3e50;
                page-break-after: avoid;
            }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        
        page.pdf(
            path=pdf_path,
            format="A4",
            margin={"top": "20mm", "right": "15mm", "bottom": "20mm", "left": "15mm"},
            print_background=True
        )
        browser.close()

if __name__ == "__main__":
    base_dir = r"c:\Users\Rei EA Jo\Downloads\icb10\one-person PJT"
    md_file = os.path.join(base_dir, "report", "eda_report.md")
    pdf_file = os.path.join(base_dir, "report", "eda_report.pdf")
    img_dir = os.path.join(base_dir, "images")
    
    convert_md_to_pdf(md_file, pdf_file, img_dir)
    print(f"Base64 encoded PDF successfully created at: {pdf_file}")
