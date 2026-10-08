#!/usr/bin/env python3
"""
extract_test_values.py
提取当前测试用例的预期值，用于回归测试对照
"""
import sys
from pathlib import Path
import importlib.util
from docx import Document

def main():
    draft_path = 'inbox/samples/company/0402威胜控股（3393.HK）首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航.docx'
    output_dir = 'skills/report_maker/test_automation/test_env/expected/'
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    doc = Document(draft_path)
    paragraphs = [(i, p.text.strip()) for i, p in enumerate(doc.paragraphs) if p.text.strip()]

    total_paras = len(paragraphs)
    print(f'Total paragraphs: {total_paras}')

    with open(f'{output_dir}/draft_paragraphs.txt', 'w') as f:
        f.write(f'{total_paras}\n')
        for i, text in paragraphs:
            f.write(f'{i}: {text[:80]}\n')

    print('Expected values written to test_env/expected/')

if __name__ == '__main__':
    main()
