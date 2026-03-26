#!/usr/bin/env python3
"""template_maker 脚本入口点

支持命令行调用，自动化模式下的批量模板创建。
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# 添加 scripts 目录到 path
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from . import common
from .schema import generate_schema, save_schema
from .template import (
    load_document, save_document,
    replace_field_value_in_doc,
    replace_abstract_in_doc,
    replace_body_elements_in_doc,
    replace_appendix_in_doc
)
from .document import (
    find_abstract_by_elements,
    find_body_elements,
    find_appendix_elements,
    find_section_by_title
)
from .router import load_router, update_mapping, save_router
from .validate import validate_template, print_validation_report


def create_template(
    name: str,
    word_path: str,
    elements_path: str,
    abstract_scope: str = None,
    body_scope: Optional[str] = None,
    no_abstract: bool = False,
    output_dir: str = "templates",
    auto_confirm: bool = False
) -> dict:
    """创建模板的主函数。

    Args:
        name: 模板名称
        word_path: Word 样本文件路径
        elements_path: elements.yaml 配置文件路径
        abstract_scope: 摘要位置描述
        body_scope: 正文位置描述（None 表示没有正文）
        no_abstract: 是否禁用摘要（True 表示没有摘要）
        output_dir: 输出目录
        auto_confirm: 跳过确认，直接创建

    Returns:
        {"success": bool, "message": str, "files": list}
    """
    # 使用默认值（注意：body_scope=None 表示没有正文，不要覆盖）
    if abstract_scope is None and not no_abstract:
        abstract_scope = common.DEFAULT_ABSTRACT_SCOPE
    # body_scope 由调用方控制，None 表示没有正文

    word_path = Path(word_path)
    elements_path = Path(elements_path)
    output_dir = Path(output_dir)

    # 验证输入文件
    if not word_path.exists():
        return {"success": False, "message": f"Word 文件不存在: {word_path}"}
    if not elements_path.exists():
        return {"success": False, "message": f"{common.FILE_ELEMENTS} 不存在: {elements_path}"}

    # 加载 elements.yaml
    elements = common.load_yaml(elements_path)

    if not auto_confirm:
        print(f"\n=== 模板创建配置 ===")
        print(f"模板名称: {name}")
        print(f"Word 文件: {word_path}")
        print(f"elements.yaml: {elements_path}")
        print(f"摘要位置: {abstract_scope if not no_abstract else '无'}")
        print(f"正文位置: {body_scope or '无（快讯报告）'}")
        confirm = input("\n确认创建吗？(y/n): ")
        if confirm.lower() != 'y':
            return {"success": False, "message": "用户取消"}

    # 1. 创建输出目录
    template_dir = output_dir / name
    template_dir.mkdir(parents=True, exist_ok=True)

    # 2. 生成 schema.yaml
    if no_abstract:
        abstract_config = {"enabled": False}
    else:
        abstract_config = {"scope": abstract_scope}
    if body_scope:
        body_config = {"scope": body_scope}
    else:
        # 快讯报告，禁用 body
        body_config = {"enabled": False}
    schema = generate_schema(elements, abstract_config, body_config)
    schema_path = template_dir / common.FILE_SCHEMA
    save_schema(schema_path, schema)

    # 3. 生成 meta.yaml
    meta = {
        "name": name,
        "display_name": f"{name} 模板",
        "version": "1.0.0",
        "status": "active",
        "sample_source": str(word_path)
    }
    meta_path = template_dir / common.FILE_META
    common.save_yaml(meta_path, meta)

    # 4. 处理 Word 文档
    doc = load_document(str(word_path))

    # 展平 elements（处理 analysts 等嵌套字段）
    flat_elements = common.flatten_elements(elements)

    # 5. 定位并替换摘要区域（如果启用）
    if not no_abstract:
        abstract_result = find_abstract_by_elements(str(word_path), elements)
        if abstract_result.get('found'):
            doc = replace_abstract_in_doc(
                doc,
                table=abstract_result['table'],
                row=abstract_result['row_start'],
                col_start=abstract_result['col_start'],
                col_end=abstract_result['col_end'],
                row_end=abstract_result.get('row_end')
            )
        else:
            print(f"警告：未能定位摘要位置 - {abstract_result.get('reason', '未知原因')}")

    # 6. 定位所有区域（在替换前获取所有位置信息）
    body_result = None
    appendix_result = None

    if body_scope:
        body_result = find_body_elements(str(word_path))
        if not body_result.get('found'):
            print(f"警告：未能定位正文位置 - {body_result.get('reason', '未知原因')}")
            body_result = None

    if 'appendix' in elements:
        appendix_result = find_appendix_elements(str(word_path))
        if not appendix_result.get('found'):
            print(f"警告：未能定位 APPENDIX 位置 - {appendix_result.get('reason', '未知原因')}")
            appendix_result = None

    # 检查并定位所有 sections.* 子字段的区域（用于文档级别的段落区域）
    # 标题映射：section_name -> (start_titles, end_titles)
    # start_titles 是列表，按优先级尝试匹配
    SECTION_TITLE_MAP = {
        'viewpoint': (['核心观点'], ['投资建议', '风险提示', '风险', 'APPENDIX', '附录']),
        'event': (['事件'], ['点评', '评论', '投资建议', '风险提示', '风险', 'APPENDIX', '附录']),
        'comment': (['点评', '评论'], ['投资建议', '风险提示', '风险', 'APPENDIX', '附录']),
        'advice': (['投资建议'], ['风险提示', '风险', 'APPENDIX', '附录']),
        'risks': (['风险提示', '风险'], ['APPENDIX', '附录']),
    }

    section_results = {}  # 存储找到的 section 区域
    if 'sections' in elements:
        sections_data = elements.get('sections', {})
        for section_name, (start_titles, end_titles) in SECTION_TITLE_MAP.items():
            if section_name in sections_data:
                # 尝试每个可能的 start_title
                for start_title in start_titles:
                    result = find_section_by_title(
                        str(word_path),
                        start_title=start_title,
                        end_titles=end_titles
                    )
                    if result.get('found'):
                        section_results[section_name] = result
                        break
                # 如果没找到，不打印警告，因为可能在表格单元格内

    # 对于没有找到区域的 sections_* 字段，需要使用字段值替换
    # 重新遍历 flat_elements，只替换没有区域的 sections_* 字段和其他字段
    for field_name, field_value in flat_elements.items():
        # 检查是否是 sections_* 字段
        if field_name.startswith('sections_'):
            section_key = field_name.replace('sections_', '')
            # 如果这个 section 已经找到了区域，跳过字段值替换
            if section_key in section_results:
                continue
        doc = replace_field_value_in_doc(doc, field_name, field_value)

    # 7. 从后往前替换区域（避免索引偏移问题）
    # 先替换 APPENDIX（位置更靠后）
    if appendix_result:
        doc = replace_appendix_in_doc(
            doc,
            start_element_idx=appendix_result['start_element_idx'],
            end_element_idx=appendix_result['end_element_idx']
        )

    # 再替换正文（位置更靠前）
    if body_result:
        doc = replace_body_elements_in_doc(
            doc,
            start_element_idx=body_result['start_element_idx'],
            end_element_idx=body_result['end_element_idx']
        )

    # 最后替换所有 sections 区域（从后往前，按照在文档中的位置）
    # 注意：如果 section 区域完全在 body 范围内，跳过替换（已被 body 覆盖）
    # 排序：按 start_element_idx 降序，确保从后往前替换
    from .template import _replace_elements_region

    # 过滤掉被 body 覆盖的 sections
    filtered_sections = {}
    for section_name, result in section_results.items():
        section_start = result['start_element_idx']
        section_end = result['end_element_idx']

        # 检查是否被 body 覆盖
        if body_result:
            body_start = body_result['start_element_idx']
            body_end = body_result['end_element_idx']
            # 如果 section 完全在 body 范围内，跳过
            if section_start >= body_start and section_end <= body_end:
                continue

        filtered_sections[section_name] = result

    sorted_sections = sorted(
        filtered_sections.items(),
        key=lambda x: x[1]['start_element_idx'],
        reverse=True
    )
    for section_name, result in sorted_sections:
        doc = _replace_elements_region(
            doc,
            start_element_idx=result['start_element_idx'],
            end_element_idx=result['end_element_idx'],
            placeholder=common.format_placeholder(f'sections_{section_name}')
        )

    # 8. 保存模板
    template_docx_path = template_dir / common.FILE_TEMPLATE
    save_document(doc, str(template_docx_path))

    # 9. 更新 router.yaml
    router_path = output_dir / common.FILE_ROUTER
    router_data = load_router(router_path)
    router_data = update_mapping(router_data, name, name)
    save_router(router_path, router_data)

    # 10. 验证模板（完整性 + 格式）
    passed, summary, validation_results = validate_template(
        template_path=str(template_docx_path),
        schema_path=str(schema_path),
        sample_path=str(word_path),
        elements_path=str(elements_path)
    )

    # 打印验证报告
    if not auto_confirm:
        print_validation_report(validation_results)

    # 构建返回结果
    result = {
        "success": True,
        "message": f"模板 '{name}' 创建成功",
        "files": [
            str(schema_path),
            str(meta_path),
            str(template_docx_path),
            str(router_path)
        ],
        "validation": {
            "passed": passed,
            "summary": summary,
            "details": {
                name: {
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                }
                for name, r in validation_results.items()
            }
        }
    }

    # 如果验证失败，添加警告
    if not passed:
        result["message"] = f"模板 '{name}' 创建成功，但验证发现问题"
        result["warning"] = summary

    return result


def main() -> int:
    """命令行入口函数。

    Returns:
        退出码（0 表示成功，1 表示失败）
    """
    parser = argparse.ArgumentParser(
        description="创建分析师报告模板",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式创建模板
  python invoke.py --name common --word samples/macro.docx --elements samples/macro_elements.yaml

  # 自动化模式（跳过确认）
  python invoke.py --name company --word samples/company.docx --elements samples/company_elements.yaml --auto-confirm

  # 快讯报告（无正文）
  python invoke.py --name flash --word samples/flash.docx --elements samples/flash_elements.yaml --no-body --auto-confirm
        """
    )

    parser.add_argument("--name", required=True, help="模板名称")
    parser.add_argument("--word", required=True, help="Word 样本文件路径")
    parser.add_argument("--elements", required=True, help=f"{common.FILE_ELEMENTS} 配置文件路径")
    parser.add_argument("--abstract-scope", default=common.DEFAULT_ABSTRACT_SCOPE, help="摘要位置描述")
    parser.add_argument("--body-scope", default=common.DEFAULT_BODY_SCOPE, help="正文位置描述")
    parser.add_argument("--no-body", action="store_true", help="快讯报告，没有正文部分")
    parser.add_argument("--no-abstract", action="store_true", help="没有摘要部分")
    parser.add_argument("--output-dir", default="templates", help="输出目录（默认: templates）")
    parser.add_argument("--auto-confirm", "-y", action="store_true", help="跳过确认，直接创建")

    args = parser.parse_args()

    # 处理 --no-body 参数
    body_scope = None if args.no_body else args.body_scope

    result = create_template(
        name=args.name,
        word_path=args.word,
        elements_path=args.elements,
        abstract_scope=args.abstract_scope,
        body_scope=body_scope,
        no_abstract=args.no_abstract,
        output_dir=args.output_dir,
        auto_confirm=args.auto_confirm
    )

    if result["success"]:
        print(f"\n{result['message']}")
        print("创建的文件:")
        for f in result["files"]:
            print(f"  - {f}")

        # 显示验证结果
        if "validation" in result:
            validation = result["validation"]
            print(f"\n验证结果: {validation['summary']}")
            if not validation["passed"] and "warning" in result:
                print(f"⚠️  警告: {result['warning']}")

        return 0
    else:
        print(f"\n{result['message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
