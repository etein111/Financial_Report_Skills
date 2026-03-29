#!/usr/bin/env python3
"""template_maker 脚本入口点

支持命令行调用，自动化模式下的批量模板创建。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 添加 scripts 目录到 path
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from schema import generate_schema, save_schema
from template import (
    load_document, save_document,
    replace_field_value_in_doc,
    replace_abstract_in_doc,
    replace_body_in_doc,
    replace_analyst_fields_in_doc
)
from document import find_abstract_by_elements, find_body_range_by_sections
from router import load_router, update_mapping, save_router
import yaml


DEFAULT_ABSTRACT_SCOPE = "首页右侧"
DEFAULT_BODY_SCOPE = "从首页之后到报告结尾"


def create_template(
    name: str,
    word_path: str,
    elements_path: str,
    abstract_scope: str = DEFAULT_ABSTRACT_SCOPE,
    body_scope: str | None = DEFAULT_BODY_SCOPE,
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

    # 先处理分析师字段（特殊处理：组合格式 + 空位置占位符）
    doc = replace_analyst_fields_in_doc(doc, elements)
    print("分析师字段: 已处理")

    # 替换普通字段值为占位符（跳过分析师字段）
    analyst_fields = {f'a{i}_{f}' for i in range(1, 9) for f in ['cn', 'en', 'sfc', 'email']}
    for field_name, field_value in elements.items():
        if field_value and field_name not in analyst_fields:
            doc = replace_field_value_in_doc(doc, field_name, str(field_value))

    # 替换摘要区域为 {{ abstract }} 占位符
    abstract_location = find_abstract_by_elements(str(word_path), elements)
    if abstract_location.get("found"):
        doc = replace_abstract_in_doc(
            doc,
            table=abstract_location["table"],
            row=abstract_location["row"],
            col_start=abstract_location["col_start"],
            col_end=abstract_location["col_end"]
        )
        print(f"摘要位置: {abstract_location['context']}")
    else:
        print(f"警告: 未能自动定位摘要位置 - {abstract_location.get('reason', '未知原因')}")

    # 替换正文区域为 {{ body }} 占位符（如果有正文）
    if body_scope:
        body_location = find_body_range_by_sections(str(word_path))
        if body_location.get("found"):
            doc = replace_body_in_doc(
                doc,
                start_paragraph=body_location["start_paragraph"],
                end_paragraph=body_location["end_paragraph"]
            )
            print(f"正文位置: {body_location['context']}")
        else:
            print(f"警告: 未能自动定位正文位置 - {body_location.get('reason', '未知原因')}")

    # 保存模板
    template_docx_path = template_dir / "template.docx"
    save_document(doc, str(template_docx_path))

    # 5. 更新 router.yaml
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
