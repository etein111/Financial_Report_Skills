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

from schema import generate_schema, save_schema
from template import (
    load_document, save_document,
    replace_field_value_in_doc,
    replace_abstract_in_doc,
    replace_body_in_doc,
    replace_body_elements_in_doc
)
from document import (
    find_abstract_by_elements,
    find_body_range_by_sections,
    find_body_elements
)
from router import load_router, update_mapping, save_router
import yaml


DEFAULT_ABSTRACT_SCOPE = "首页右侧"
DEFAULT_BODY_SCOPE = "从首页之后到报告结尾"


def flatten_elements(elements: Dict[str, Any]) -> Dict[str, str]:
    """展平 elements（处理 analysts 等嵌套字段）。

    Args:
        elements: 原始 elements 字典

    Returns:
        展平后的 field_name -> field_value 映射
    """
    flat = {}
    for name, value in elements.items():
        if name == "analysts" and isinstance(value, list):
            for i, analyst in enumerate(value):
                prefix = f"analyst_{i+1}" if len(value) > 1 else "analyst"
                if isinstance(analyst, dict):
                    for key, val in analyst.items():
                        if val and val != "null":
                            flat[f"{prefix}_{key}"] = str(val)
        elif value is not None and value != "null":
            flat[name] = str(value)
    return flat


def create_template(
    name: str,
    word_path: str,
    elements_path: str,
    abstract_scope: str = DEFAULT_ABSTRACT_SCOPE,
    body_scope: Optional[str] = DEFAULT_BODY_SCOPE,
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
        output_dir: 输出目录
        auto_confirm: 跳过确认，直接创建

    Returns:
        {"success": bool, "message": str, "files": list}
    """
    word_path = Path(word_path)
    elements_path = Path(elements_path)
    output_dir = Path(output_dir)

    # 验证输入文件
    if not word_path.exists():
        return {"success": False, "message": f"Word 文件不存在: {word_path}"}
    if not elements_path.exists():
        return {"success": False, "message": f"elements.yaml 不存在: {elements_path}"}

    # 加载 elements.yaml
    elements = yaml.safe_load(elements_path.read_text())

    if not auto_confirm:
        print(f"\n=== 模板创建配置 ===")
        print(f"模板名称: {name}")
        print(f"Word 文件: {word_path}")
        print(f"elements.yaml: {elements_path}")
        print(f"摘要位置: {abstract_scope}")
        print(f"正文位置: {body_scope or '无（快讯报告）'}")
        confirm = input("\n确认创建吗？(y/n): ")
        if confirm.lower() != 'y':
            return {"success": False, "message": "用户取消"}

    # 1. 创建输出目录
    template_dir = output_dir / name
    template_dir.mkdir(parents=True, exist_ok=True)

    # 2. 生成 schema.yaml
    abstract_config = {"scope": abstract_scope}
    if body_scope:
        body_config = {"scope": body_scope}
    else:
        # 快讯报告，禁用 body
        body_config = {"enabled": False}
    schema = generate_schema(elements, abstract_config, body_config)
    schema_path = template_dir / "schema.yaml"
    save_schema(schema_path, schema)

    # 3. 生成 meta.yaml
    meta = {
        "name": name,
        "display_name": f"{name} 模板",
        "version": "1.0.0",
        "status": "active",
        "sample_source": str(word_path)
    }
    meta_path = template_dir / "meta.yaml"
    meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))

    # 4. 处理 Word 文档
    doc = load_document(str(word_path))

    # 展平 elements（处理 analysts 等嵌套字段）
    flat_elements = flatten_elements(elements)

    # 替换字段值为占位符
    for field_name, field_value in flat_elements.items():
        doc = replace_field_value_in_doc(doc, field_name, field_value)

    # 5. 定位并替换摘要区域
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

    # 6. 定位并替换正文区域（如果有正文）
    # 使用 find_body_elements + replace_body_elements_in_doc
    # 正文包括段落、表格、图表等所有块级元素，附录保留不替换
    if body_scope:
        body_result = find_body_elements(str(word_path))
        if body_result.get('found'):
            doc = replace_body_elements_in_doc(
                doc,
                start_element_idx=body_result['start_element_idx'],
                end_element_idx=body_result['end_element_idx']
            )

    # 保存模板
    template_docx_path = template_dir / "template.docx"
    save_document(doc, str(template_docx_path))

    # 7. 更新 router.yaml
    router_path = output_dir / "router.yaml"
    router_data = load_router(router_path)
    router_data = update_mapping(router_data, name, name)
    save_router(router_path, router_data)

    return {
        "success": True,
        "message": f"模板 '{name}' 创建成功",
        "files": [
            str(schema_path),
            str(meta_path),
            str(template_docx_path),
            str(router_path)
        ]
    }


def main():
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
    parser.add_argument("--elements", required=True, help="elements.yaml 配置文件路径")
    parser.add_argument("--abstract-scope", default=DEFAULT_ABSTRACT_SCOPE, help="摘要位置描述")
    parser.add_argument("--body-scope", default=DEFAULT_BODY_SCOPE, help="正文位置描述")
    parser.add_argument("--no-body", action="store_true", help="快讯报告，没有正文部分")
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
        output_dir=args.output_dir,
        auto_confirm=args.auto_confirm
    )

    if result["success"]:
        print(f"\n{result['message']}")
        print("创建的文件:")
        for f in result["files"]:
            print(f"  - {f}")
        return 0
    else:
        print(f"\n{result['message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
