from markdown_pdf import Section, MarkdownPdf
import os

pdf = MarkdownPdf(toc_level=2)

report_path = "report/eda_report.md"
pdf_path = "report/eda_report.pdf"

# We need to make sure the image paths are resolved correctly relative to the markdown file
with open(report_path, "r", encoding="utf-8") as f:
    text = f.read()

# markdown-pdf might struggle with relative paths from script directory.
# Let's change cwd to the directory where markdown file is, or replace the paths with absolute paths.
import re
abs_img_dir = os.path.abspath("images")
text = re.sub(r"\.\./images", abs_img_dir.replace("\\", "/"), text)

pdf.add_section(Section(text))

# Also need to use a font that supports Korean
# markdown-pdf uses default fonts, it might cause mojibake for Korean if not specified, 
# wait, actually let's just save it and check.
pdf.meta["title"] = "관악구 1인가구 소비패턴 EDA 리포트"
pdf.save(pdf_path)
print(f"PDF saved to {pdf_path}")
