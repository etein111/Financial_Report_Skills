#!/usr/bin/env python3
"""测试脚本：模拟两阶段报告生成流程。"""

import sys
import shutil
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from common import (
    load_yaml, save_yaml,
    get_template_name,
    create_report_dir,
    normalize_report_name,
    ensure_all_fields,
    FILE_DRAFT, FILE_ELEMENTS, FILE_ABSTRACT, FILE_BODY,
    FILE_OUTPUT_DOCX, FILE_OUTPUT_PDF
)


def stage1_extract_and_confirm():
    """第一阶段：抽取与确认。"""
    
    print("\n" + "="*70)
    print("第一阶段：抽取与确认")
    print("="*70)
    
    # 1. 接收草稿
    print("\n[步骤 1] 接收草稿")
    draft_path = "samples/西锐飞机首次覆盖报告（中文）提交版.docx"
    report_type = "company"  # 人工指定
    print(f"   草稿: {draft_path}")
    print(f"   报告类型: {report_type}")
    
    # 2. 路由到模板
    print("\n[步骤 2] 路由到模板")
    template_name = get_template_name(report_type)
    print(f"   模板: {template_name}")
    
    # 3. 创建报告目录
    print("\n[步骤 3] 创建报告目录")
    report_name = normalize_report_name("西锐飞机首次覆盖报告.docx")
    report_dir = create_report_dir(report_name)
    print(f"   目录: {report_dir}")
    
    # 4. 加载 schema
    print("\n[步骤 4] 加载 schema")
    schema_path = f"templates/{template_name}/schema.yaml"
    schema = load_yaml(schema_path)
    print(f"   Schema 字段数: {len(schema)}")
    
    # 5. LLM 提取要素（模拟）
    print("\n[步骤 5] LLM 提取要素")
    elements_path = f"samples/{Path(draft_path).stem} elements.yaml"
    elements = load_yaml(elements_path)
    print(f"   提取到 {len(elements)} 个字段")
    
    # 展示关键字段
    print("\n   提取结果（关键字段）:")
    key_fields = ['ticker', 'company', 'rating', 'target_price', 'title']
    for field in key_fields:
        if field in elements:
            print(f"      {field}: {elements[field]}")
    
    # 6. 交互式确认（模拟）
    print("\n[步骤 6] 交互式确认")
    print("   ✓ ticker: 2507.HK")
    print("   ✓ company: 西锐飞机")
    print("   ✓ rating: OUTPERFORM")
    print("   ✓ target_price: 86.72")
    print("   ✓ title: 首次覆盖：...")
    print("   (用户确认: 全部正确)")
    
    # 7. 确保所有字段存在
    print("\n[步骤 7] 确保所有字段存在")
    elements = ensure_all_fields(elements, schema)
    print(f"   补全后字段数: {len(elements)}")
    
    # 8. 保存 elements
    print("\n[步骤 8] 保存 elements.yaml")
    elements_file = report_dir / FILE_ELEMENTS
    save_yaml(elements_file, elements)
    print(f"   保存到: {elements_file}")
    
    # 9. 拆分摘要和正文（模拟）
    print("\n[步骤 9] 拆分摘要和正文")
    print("   (由 Claude 在 skill 执行时完成)")
    
    # 10. 复制草稿
    print("\n[步骤 10] 复制草稿")
    draft_dest = report_dir / FILE_DRAFT
    shutil.copy(draft_path, draft_dest)
    print(f"   复制到: {draft_dest}")
    
    print("\n" + "="*70)
    print("第一阶段完成！等待用户确认...")
    print("="*70)
    
    return report_dir, elements, template_name


def stage2_render_and_output(report_dir, elements, template_name):
    """第二阶段：渲染与输出。"""
    
    print("\n" + "="*70)
    print("第二阶段：渲染与输出")
    print("="*70)
    
    # 1. 更新修正后的数据
    print("\n[步骤 1] 更新数据")
    print("   (无修正，直接使用第一阶段的数据)")
    
    # 2. 准备渲染上下文
    print("\n[步骤 2] 准备渲染上下文")
    from renderer import prepare_render_context
    context = prepare_render_context(elements, str(report_dir))
    print(f"   上下文字段数: {len(context)}")
    
    # 3. 渲染模板
    print("\n[步骤 3] 渲染模板")
    template_path = f"templates/{template_name}/template.docx"
    output_path = report_dir / FILE_OUTPUT_DOCX
    
    from renderer import render_template
    success = render_template(
        template_path,
        elements,
        str(report_dir / FILE_ABSTRACT),
        str(report_dir / FILE_BODY),
        str(output_path)
    )
    
    if success:
        print(f"   ✓ 渲染成功: {output_path}")
    else:
        print(f"   ✗ 渲染失败")
        return
    
    # 4. 转换 PDF
    print("\n[步骤 4] 转换 PDF")
    pdf_path = report_dir / FILE_OUTPUT_PDF
    
    from renderer import convert_to_pdf
    pdf_success = convert_to_pdf(str(output_path), str(pdf_path))
    
    if pdf_success:
        print(f"   ✓ PDF 转换成功: {pdf_path}")
    else:
        print(f"   ! PDF 转换跳过（LibreOffice 未安装）")
    
    print("\n" + "="*70)
    print("第二阶段完成！报告生成成功！")
    print("="*70)
    
    # 5. 总结
    print("\n生成的文件:")
    for f in report_dir.iterdir():
        if f.is_file():
            size = f.stat().st_size
            print(f"   - {f.name} ({size} bytes)")


def main():
    """主流程。"""
    print("\n" + "="*70)
    print("报告生成两阶段流程测试")
    print("="*70)
    
    # 第一阶段
    report_dir, elements, template_name = stage1_extract_and_confirm()
    
    # 模拟用户确认
    print("\n[用户] 确认，继续生成")
    
    # 第二阶段
    stage2_render_and_output(report_dir, elements, template_name)
    
    print("\n✓ 测试完成！")


if __name__ == "__main__":
    main()
