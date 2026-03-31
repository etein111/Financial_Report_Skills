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
from document import find_abstract_by_elements, find_body_range_by_sections, find_appendix_by_markers, find_first_appendix_position
from router import load_router, update_mapping, save_router, get_all_router_mappings
import yaml


DEFAULT_APPENDIX_SCOPE = "正文之后，报告末尾"


def validate_template_placeholders(doc, elements: dict, abstract_scope: str, body_scope: str) -> dict:
    """验证模板中的占位符是否完整提取。

    检查所有 elements.yaml 中定义的字段以及 abstract、body 是否都正确提取为占位符。

    Args:
        doc: Document 对象
        elements: elements.yaml 内容
        abstract_scope: 摘要位置描述
        body_scope: 正文位置描述

    Returns:
        {
            "valid": bool,
            "found_placeholders": list[str],  # 找到的占位符
            "missing_placeholders": list[str],  # 缺失的占位符
            "warnings": list[str]  # 警告信息
        }
    """
    import re

    # 收集模板中所有的占位符
    found_placeholders = set()

    # 从段落中提取占位符
    for para in doc.paragraphs:
        text = para.text
        matches = re.findall(r'\{\{\s*(\w+)\s*\}\}', text)
        found_placeholders.update(matches)

    # 从表格中提取占位符
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    text = para.text
                    matches = re.findall(r'\{\{\s*(\w+)\s*\}\}', text)
                    found_placeholders.update(matches)

    # 期望的占位符列表
    expected_placeholders = []

    # 1. 添加 elements.yaml 中的所有字段（除分析师和结构化字段外）
    analyst_fields = {f'a{i}_{f}' for i in range(1, 9) for f in ['cn', 'en', 'sfc', 'email']}
    skip_fields = {'sections', 'analysts'}

    for field_name, field_value in elements.items():
        if not field_value or field_name in analyst_fields or field_name in skip_fields:
            continue
        if isinstance(field_value, dict) or isinstance(field_value, list):
            continue
        expected_placeholders.append(field_name)

    # 2. 如果有 abstract_scope，添加 abstract 占位符
    if abstract_scope:
        expected_placeholders.append('abstract')

    # 3. 如果有 body_scope，添加 body 占位符
    if body_scope:
        expected_placeholders.append('body')

    # 4. 添加分析师占位符（即使为空也需要占位符）
    for i in range(1, 9):
        expected_placeholders.extend([f'a{i}_cn', f'a{i}_en', f'a{i}_sfc', f'a{i}_email'])

    # 检查缺失的占位符
    missing_placeholders = []
    for placeholder in expected_placeholders:
        if placeholder not in found_placeholders:
            missing_placeholders.append(placeholder)

    # 生成警告信息
    warnings = []
    if missing_placeholders:
        warnings.append(f"缺失占位符: {', '.join(missing_placeholders)}")

    return {
        "valid": len(missing_placeholders) == 0,
        "found_placeholders": sorted(found_placeholders),
        "missing_placeholders": sorted(missing_placeholders),
        "warnings": warnings
    }

# 模板类型到扫描目录的映射
TEMPLATE_SCAN_DIRS = {
    'company': 'samples',
    'sector': 'samples',
    'flash': 'samples/flash',  # 通用 flash
    'company_flash': 'samples/flash',
    'sector_flash': 'samples/flash',
    'macro': 'samples/macro',
    'strategy': 'samples/macro',
    'quantitative': 'samples/macro',
    'bond': 'samples/macro',
    'common': 'samples/macro',
}


def scan_docx_files_by_template(base_dir: Path, template_type: str) -> list[tuple[int, Path]]:
    """根据模板类型扫描对应目录下的 .docx 文件。

    Args:
        base_dir: 基础目录（通常是项目根目录）
        template_type: 模板类型（如 'flash', 'company', 'macro'）

    Returns:
        [(编号, 文件路径), ...] 列表
    """
    # 确保 base_dir 是 Path 对象
    base_dir = Path(base_dir)
    scan_dir_name = TEMPLATE_SCAN_DIRS.get(template_type.lower(), 'samples')
    scan_dir = base_dir / scan_dir_name

    if not scan_dir.exists():
        scan_dir = base_dir / 'samples'  # 回退到 samples 目录

    docx_files = []
    # 只扫描指定目录，不递归
    for path in scan_dir.glob("*.docx"):
        # 排除临时文件、以 ~ 开头的文件
        if path.name.startswith("~"):
            continue
        docx_files.append(path)

    # 按路径排序
    docx_files.sort()
    return list(enumerate(docx_files, start=1))


def find_elements_yaml(word_path: Path) -> Path | None:
    """查找与 Word 文件配对的 elements.yaml。

    在同目录下查找：
    1. {文件名} elements.yaml
    2. {文件名}_elements.yaml
    3. elements.yaml

    Args:
        word_path: Word 文件路径

    Returns:
        找到的 elements.yaml 路径，未找到返回 None
    """
    word_path = Path(word_path)
    word_dir = word_path.parent
    word_name = word_path.stem

    candidates = [
        word_dir / f"{word_name} elements.yaml",
        word_dir / f"{word_name}_elements.yaml",
        word_dir / "elements.yaml",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def prompt_select_docx(base_dir: Path, template_type: str = None) -> Path | None:
    """让用户从扫描到的 docx 文件中选择。

    根据模板类型自动扫描对应目录。

    Args:
        base_dir: 基础目录
        template_type: 模板类型（如 'flash', 'company', 'macro'）

    Returns:
        选择的文件路径，None 表示放弃
    """
    print("\n" + "=" * 60)
    print("【扫描样本文档】")
    print("=" * 60)

    if template_type:
        print(f"\n正在扫描 {template_type} 类型对应的目录...")
        docx_files = scan_docx_files_by_template(base_dir, template_type)
    else:
        # 如果没有指定模板类型，扫描 samples 目录
        scan_dir = base_dir / "samples"
        if not scan_dir.exists():
            scan_dir = base_dir
        docx_files = []
        for path in scan_dir.rglob("*.docx"):
            if path.name.startswith("~"):
                continue
            docx_files.append(path)
        docx_files.sort()
        docx_files = list(enumerate(docx_files, start=1))

    if not docx_files:
        print("\n未找到任何 .docx 文件")
        return None

    print(f"\n找到 {len(docx_files)} 个 Word 文档：")
    for idx, path in docx_files:
        print(f"  {idx}. {path}")

    print("\n请选择要使用的样本文档（输入编号，或 q 退出）:")

    while True:
        user_input = input("\n您的选择: ").strip().lower()
        if user_input == 'q':
            return None
        try:
            choice = int(user_input)
            if 1 <= choice <= len(docx_files):
                selected_path = docx_files[choice - 1][1]
                print(f"\n→ 已选择: {selected_path}")
                return selected_path
            else:
                print(f"请输入 1-{len(docx_files)} 之间的数字")
        except ValueError:
            print("请输入数字编号")


def _auto_detect_locations(word_path: Path, elements: dict) -> dict:
    """自动检测文档中的摘要、正文、附录位置。

    Args:
        word_path: Word 文件路径
        elements: elements.yaml 内容

    Returns:
        检测结果字典
    """
    result = {
        "abstract": None,
        "body": None,
        "appendix": None,
        "first_appendix": None  # 第一个 APPENDIX 标题位置（用于确定正文结束位置）
    }

    # 检测摘要位置
    abstract_location = find_abstract_by_elements(str(word_path), elements)
    if abstract_location.get("found"):
        result["abstract"] = {
            "location": abstract_location
        }

    # 检测正文位置
    body_location = find_body_range_by_sections(str(word_path))
    if body_location.get("found"):
        result["body"] = {
            "location": body_location
        }

    # 检测第一个 APPENDIX 标题位置（用于确定正文结束位置）
    first_appendix = find_first_appendix_position(str(word_path))
    if first_appendix.get("found"):
        result["first_appendix"] = first_appendix

    # 检测法律附录位置
    appendix_location = find_appendix_by_markers(str(word_path))
    if appendix_location.get("found"):
        result["appendix"] = {
            "location": appendix_location
        }

    return result


def _confirm_abstract_location(detected: dict) -> str | None:
    """交互确认摘要位置。

    Args:
        detected: 自动检测结果

    Returns:
        摘要位置描述，None 表示没有摘要
    """
    print("\n" + "=" * 60)
    print("【步骤 1/3】确认摘要位置")
    print("=" * 60)

    # 询问是否有摘要
    print("\n这份报告是否有摘要部分？")
    print("  - 公司报告通常有摘要（首页投资亮点）")
    print("  - 快讯报告可能没有摘要")

    while True:
        user_input = input("\n是否有摘要？(y/n，直接回车表示有): ").strip().lower()
        if user_input == 'n':
            print("→ 将跳过摘要部分")
            return None
        elif user_input in ['', 'y']:
            break
        print("请输入 y 或 n")

    if detected and detected.get("found"):
        detected_scope = detected.get('scope') or detected.get('context', '未知')
        print(f"\n检测到的摘要位置：")
        print(f"  位置：{detected_scope}")
        if detected.get("preview"):
            print(f"  预览：{detected['preview'][:80]}...")

        print("\n请确认摘要位置是否正确？")
        print("  - 直接回车：使用检测到的位置")
        print("  - 输入描述：手动指定位置（如：首页右侧、第二页表格中）")

        user_input = input("\n您的选择: ").strip()
        if user_input:
            return user_input
        return detected_scope
    else:
        print(f"\n⚠️ 自动检测摘要位置失败：{detected.get('reason', '未知原因')}")
        print("请手动指定摘要位置：")
        print("  示例：首页右侧、第二页表格中、首页左侧表格")

        user_input = input("\n请输入摘要位置: ").strip()
        if not user_input:
            print("→ 无法确定摘要位置，将跳过摘要")
            return None
        return user_input


def _confirm_body_location(detected: dict) -> str | None:
    """交互确认正文位置。

    Args:
        detected: 自动检测结果

    Returns:
        正文位置描述，None 表示没有正文
    """
    print("\n" + "=" * 60)
    print("【步骤 2/3】确认正文位置")
    print("=" * 60)

    print("\n这份报告是否有正文部分？")
    print("  - 快讯报告（flash）通常没有正文")
    print("  - 公司报告、行业报告通常有正文")

    while True:
        user_input = input("\n是否有正文？(y/n，直接回车表示有): ").strip().lower()
        if user_input == 'n':
            print("→ 将跳过正文部分（快讯报告模式）")
            return None
        elif user_input in ['', 'y']:
            break
        print("请输入 y 或 n")

    if detected and detected.get("found"):
        detected_scope = detected.get('scope') or detected.get('context', '未知')
        print(f"\n检测到的正文位置：")
        print(f"  位置：{detected_scope}")

        print("\n请确认正文位置是否正确？")
        print("  - 直接回车：使用检测到的位置")
        print("  - 输入描述：手动指定位置（如：从第二页开始、从目录之后开始）")

        user_input = input("\n您的选择: ").strip()
        if user_input:
            return user_input
        return detected_scope
    else:
        reason = detected.get('reason', '未知原因') if detected else '未知原因'
        print(f"\n⚠️ 自动检测正文位置失败：{reason}")
        print("请手动指定正文位置：")
        print("  示例：从第二页开始、从目录之后开始、从第一章开始")

        user_input = input("\n请输入正文位置: ").strip()
        if not user_input:
            print("→ 无法确定正文位置，将跳过正文")
            return None
        return user_input


def _get_appendix_location(detected: dict) -> str:
    """获取法律披露附录位置（法律附录是必有的，直接返回检测结果或默认值）。

    Args:
        detected: 自动检测结果

    Returns:
        附录位置描述
    """
    if detected and detected.get("found"):
        location = detected.get('location', {})
        return location.get('context', DEFAULT_APPENDIX_SCOPE)
    else:
        # 法律附录一定有，使用默认位置
        return DEFAULT_APPENDIX_SCOPE


def _confirm_report_type_mapping(name: str, router_path: Path, auto_confirm: bool) -> str | None:
    """交互确认报告类型映射。

    Args:
        name: 模板名称
        router_path: router.yaml 文件路径
        auto_confirm: 是否自动确认

    Returns:
        要映射的报告类型，None 表示不添加到 router
    """
    print("\n" + "=" * 60)
    print("【步骤 4/4】配置报告类型映射")
    print("=" * 60)

    # 显示现有映射
    router_data = load_router(router_path)
    existing_mappings = get_all_router_mappings(router_data)

    if existing_mappings:
        print("\n现有映射：")
        for rt, tmpl in existing_mappings.items():
            print(f"  {rt} → {tmpl}")
    else:
        print("\n当前没有映射配置")

    print(f"\n此模板 '{name}' 将用于哪种报告类型？")
    print("  - 输入报告类型名称（如：company、sector、macro）")
    print("  - 直接回车：使用模板名称作为报告类型")
    print("  - 输入 'n' 或 'no'：不添加到路由")

    if auto_confirm:
        # 自动化模式：使用模板名称作为报告类型
        print(f"\n[自动化模式] 使用 '{name}' 作为报告类型")
        return name

    while True:
        user_input = input("\n报告类型: ").strip().lower()

        if user_input in ['n', 'no', '']:
            return name  # 默认使用模板名称
        elif user_input:
            return user_input

        print("请输入报告类型名称")


def create_template(
    name: str,
    word_path: str,
    elements_path: str,
    abstract_scope: str | None = None,
    body_scope: str | None = None,
    appendix_scope: str | None = None,
    output_dir: str = "templates",
    auto_confirm: bool = False
) -> dict:
    """创建模板的主函数。

    Args:
        name: 模板名称
        word_path: Word 样本文件路径
        elements_path: elements.yaml 配置文件路径
        abstract_scope: 摘要位置描述（None 表示交互询问）
        body_scope: 正文位置描述（None 表示交互询问，"" 表示没有正文）
        appendix_scope: 法律披露附录位置描述（None 表示交互询问，"" 表示没有附录）
        output_dir: 输出目录
        auto_confirm: 跳过确认，直接使用默认值

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

    print(f"\n{'=' * 60}")
    print("模板创建向导")
    print(f"{'=' * 60}")
    print(f"模板名称: {name}")
    print(f"Word 文件: {word_path}")
    print(f"elements.yaml: {elements_path}")

    # 自动检测位置
    print("\n正在自动检测文档结构...")
    detected_locations = _auto_detect_locations(word_path, elements)

    # 交互确认位置
    if auto_confirm:
        # 自动化模式：如果命令行指定了值就使用，否则必须询问
        if abstract_scope is None:
            abstract_scope = _confirm_abstract_location(detected_locations.get("abstract"))
        if body_scope is None:
            body_scope = _confirm_body_location(detected_locations.get("body"))
        if appendix_scope is None:
            appendix_scope = _get_appendix_location(detected_locations.get("appendix"))
        print("\n[自动化模式] 位置配置完成")
    else:
        # 交互模式：逐个确认
        abstract_scope = _confirm_abstract_location(detected_locations.get("abstract"))
        body_scope = _confirm_body_location(detected_locations.get("body"))
        appendix_scope = _get_appendix_location(detected_locations.get("appendix"))

    # 准备 router.yaml 路径（用于显示现有映射）
    router_path = output_dir / "router.yaml"

    # 报告类型映射确认
    report_type = _confirm_report_type_mapping(name, router_path, auto_confirm)

    # 显示最终配置
    print("\n" + "=" * 60)
    print("【最终配置确认】")
    print("=" * 60)
    print(f"模板名称: {name}")
    print(f"报告类型映射: {report_type} → {name}")
    print(f"摘要位置: {abstract_scope}")
    print(f"正文位置: {body_scope or '无（快讯报告）'}")
    print(f"法律披露附录: {appendix_scope}（保留原样）")

    if not auto_confirm:
        confirm = input("\n确认创建模板？(y/n): ").strip()
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
    if appendix_scope:
        appendix_config = {"scope": appendix_scope}
    else:
        # 没有法律披露附录
        appendix_config = {"enabled": False}
    schema = generate_schema(elements, abstract_config, body_config, appendix_config)
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

    # 替换普通字段值为占位符（跳过分析师字段和结构化字段）
    analyst_fields = {f'a{i}_{f}' for i in range(1, 9) for f in ['cn', 'en', 'sfc', 'email']}
    # 只跳过结构化字段（字典类型），保留 summary 等文本字段
    skip_fields = {'sections', 'analysts'}
    replaced_fields = []

    for field_name, field_value in elements.items():
        if not field_value or field_name in analyst_fields or field_name in skip_fields:
            continue

        # 如果是字典类型（如 sections），跳过
        if isinstance(field_value, dict):
            continue

        # 如果是列表类型，跳过
        if isinstance(field_value, list):
            continue

        field_str = str(field_value)
        # 尝试替换
        doc = replace_field_value_in_doc(doc, field_name, field_str)
        replaced_fields.append(field_name)

    if replaced_fields:
        print(f"字段替换: {', '.join(replaced_fields)}")

    # 替换摘要区域为 {{ abstract }} 占位符
    # 使用之前检测的位置信息，而不是重新检测
    abstract_detected = detected_locations.get("abstract")
    abstract_location = abstract_detected.get("location") if abstract_detected else None

    if abstract_scope and abstract_location and abstract_location.get("found"):
        doc = replace_abstract_in_doc(
            doc,
            table=abstract_location["table"],
            row=abstract_location["row"],
            col_start=abstract_location["col_start"],
            col_end=abstract_location["col_end"]
        )
        print(f"摘要位置: {abstract_location['context']}")
    elif abstract_scope:
        # 用户确认有摘要，但自动检测失败，尝试重新检测
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
            print(f"警告: 用户确认有摘要，但未能自动定位摘要位置 - {abstract_location.get('reason', '未知原因')}")
            print("提示: 摘要区域需要手动调整模板")
    else:
        print("摘要: 用户确认无摘要，跳过")

    # 替换正文区域为 {{ body }} 占位符（如果有正文）
    if body_scope:
        # 使用之前检测的位置信息
        body_detected = detected_locations.get("body")
        body_location = body_detected.get("location") if body_detected else None

        if not body_location or not body_location.get("found"):
            # 尝试重新检测
            body_location = find_body_range_by_sections(str(word_path))

        if body_location and body_location.get("found"):
            start_para = body_location["start_paragraph"]
            end_para = body_location["end_paragraph"]

            # 使用第一个 APPENDIX 标题位置来确定正文结束位置
            # 这样可以保留所有 APPENDIX 内容（包括 "APPENDIX 1 Summary" 和法律附录）
            first_appendix = detected_locations.get("first_appendix")
            if first_appendix and first_appendix.get("found"):
                appendix_start = first_appendix.get("start_paragraph")
                if appendix_start and appendix_start < end_para:
                    end_para = appendix_start
                    print(f"正文结束位置调整为第一个 APPENDIX 起始位置: 段落 {appendix_start}")
                    print(f"  APPENDIX 标题: {first_appendix.get('text', '')[:50]}")

            doc = replace_body_in_doc(
                doc,
                start_paragraph=start_para,
                end_paragraph=end_para
            )
            print(f"正文位置: 段落 {start_para} 到 {end_para}")
        else:
            reason = body_location.get('reason', '未知原因') if body_location else '未知原因'
            print(f"警告: 未能自动定位正文位置 - {reason}")
    else:
        print("正文: 用户确认无正文（快讯报告模式），跳过")

    # ========== 验证占位符 ==========
    print("\n正在验证模板占位符...")
    validation = validate_template_placeholders(doc, elements, abstract_scope, body_scope)

    if validation["found_placeholders"]:
        print(f"已提取占位符: {', '.join(validation['found_placeholders'])}")

    if validation["missing_placeholders"]:
        print(f"\n⚠️ 警告: 以下占位符未能提取:")
        for placeholder in validation["missing_placeholders"]:
            print(f"  - {{{{ {placeholder} }}}}")
        print("\n这些字段可能需要手动调整模板")

    if validation["valid"]:
        print("✓ 占位符验证通过")
    else:
        print("⚠️ 占位符验证未完全通过，请检查模板")
    # ========== 验证完成 ==========

    # 保存模板
    template_docx_path = template_dir / "template.docx"
    save_document(doc, str(template_docx_path))

    # 5. 更新 router.yaml（使用用户确认的报告类型映射）
    router_path = output_dir / "router.yaml"
    router_data = load_router(router_path)
    router_data = update_mapping(router_data, report_type, name)
    save_router(router_path, router_data)
    print(f"\n路由配置已更新: {report_type} → {name}")

    return {
        "success": True,
        "message": f"模板 '{name}' 创建成功",
        "validation": validation,
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

  # 快讯报告（无正文，无附录）
  python invoke.py --name flash --word samples/flash.docx --elements samples/flash_elements.yaml --no-body --no-appendix --auto-confirm
        """
    )

    parser.add_argument("--name", required=True, help="模板名称")
    parser.add_argument("--word", required=True, help="Word 样本文件路径")
    parser.add_argument("--elements", required=True, help="elements.yaml 配置文件路径")
    parser.add_argument("--abstract-scope", default=None, help="摘要位置描述（默认: 询问用户）")
    parser.add_argument("--body-scope", default=None, help="正文位置描述（默认: 询问用户）")
    parser.add_argument("--no-body", action="store_true", help="快讯报告，没有正文部分")
    parser.add_argument("--appendix-scope", default=DEFAULT_APPENDIX_SCOPE, help="法律披露附录位置描述")
    parser.add_argument("--no-appendix", action="store_true", help="没有法律披露附录")
    parser.add_argument("--output-dir", default="templates", help="输出目录（默认: templates）")
    parser.add_argument("--auto-confirm", "-y", action="store_true", help="跳过确认，直接创建")

    args = parser.parse_args()

    # 处理 --no-body 和 --no-appendix 参数
    body_scope = None if args.no_body else args.body_scope
    appendix_scope = None if args.no_appendix else args.appendix_scope

    result = create_template(
        name=args.name,
        word_path=args.word,
        elements_path=args.elements,
        abstract_scope=args.abstract_scope,
        body_scope=body_scope,
        appendix_scope=appendix_scope,
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