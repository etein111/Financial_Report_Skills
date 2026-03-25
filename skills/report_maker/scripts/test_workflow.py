#!/usr/bin/env python3
"""测试脚本：验证完整的报告生成流程。"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from common import (
    load_yaml, save_yaml,
    get_template_name,
    create_report_dir,
    normalize_report_name,
    ensure_all_fields,
    validate_elements_against_schema,
    FILE_DRAFT, FILE_ELEMENTS, FILE_ABSTRACT, FILE_BODY,
    FILE_OUTPUT_DOCX, FILE_OUTPUT_PDF
)
from splitter import read_document_structure, get_split_instructions
from renderer import validate_template

def test_workflow():
    """测试完整工作流程。"""
    
    print("=" * 60)
    print("报告生成流程测试")
    print("=" * 60)
    
    # 1. 读取样本 elements
    print("\n1. 读取样本 elements.yaml")
    elements_path = "samples/西锐飞机首次覆盖报告（中文）提交版 elements.yaml"
    elements = load_yaml(elements_path)
    print(f"   读取到 {len(elements)} 个字段")
    print(f"   示例字段: ticker={elements.get('ticker')}, company={elements.get('company')}")
    
    # 2. 读取 schema
    print("\n2. 读取 schema.yaml")
    schema_path = "templates/company/schema.yaml"
    schema = load_yaml(schema_path)
    print(f"   读取到 {len(schema)} 个字段定义")
    
    # 3. 验证 elements 与 schema 一致性
    print("\n3. 验证 elements 与 schema 一致性")
    errors = validate_elements_against_schema(elements, schema)
    if errors:
        print(f"   ❌ 发现 {len(errors)} 个错误:")
        for error in errors:
            print(f"      - {error}")
    else:
        print("   ✅ 验证通过")
    
    # 4. 确保所有字段存在
    print("\n4. 确保所有字段存在")
    elements = ensure_all_fields(elements, schema)
    print(f"   补全后共 {len(elements)} 个字段")
    
    # 5. 读取草稿文档结构
    print("\n5. 读取草稿文档结构")
    draft_path = "samples/西锐飞机首次覆盖报告（中文）提交版.docx"
    doc_structure = read_document_structure(draft_path)
    if "error" in doc_structure:
        print(f"   ❌ {doc_structure['error']}")
    else:
        print(f"   ✅ 文档包含:")
        print(f"      - {doc_structure['paragraphs']} 个段落")
        print(f"      - {doc_structure['tables']} 个表格")
        print(f"      - {doc_structure['sections']} 个节")
    
    # 6. 获取拆分指令
    print("\n6. 生成拆分指令")
    instructions = get_split_instructions(schema)
    print(f"   指令:\n{instructions}")
    
    # 7. 创建报告目录
    print("\n7. 创建报告目录")
    report_dir = create_report_dir("test_report")
    print(f"   ✅ 目录创建成功: {report_dir}")
    
    # 8. 保存 elements.yaml
    print("\n8. 保存 elements.yaml")
    elements_path = report_dir / FILE_ELEMENTS
    save_yaml(elements_path, elements)
    print(f"   ✅ 保存成功: {elements_path}")
    
    # 9. 验证模板
    print("\n9. 验证模板")
    template_path = "templates/company/template.docx"
    template_info = validate_template(template_path)
    if template_info["valid"]:
        print(f"   ✅ 模板有效")
        print(f"      - {template_info['paragraphs']} 个段落")
        print(f"      - {template_info['tables']} 个表格")
    else:
        print(f"   ❌ 模板无效: {template_info.get('error')}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_workflow()
