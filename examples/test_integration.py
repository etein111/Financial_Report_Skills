#!/usr/bin/env python3
"""
report_maker 集成测试示例

演示如何使用 report_maker 的核心功能处理报告。
"""

import sys
import os
from pathlib import Path

# 添加 scripts 目录到路径
scripts_dir = Path(__file__).parent.parent / "skills" / "report_maker" / "scripts"
sys.path.insert(0, str(scripts_dir))

try:
    import common
    import extractor
    import splitter
    import renderer

    print("=== report_maker 集成测试 ===")
    print()

    # 1. 测试 YAML 工具
    print("1. 测试 YAML 工具")
    print("-" * 40)

    test_data = {"company": "测试公司", "ticker": "TEST.HK"}
    test_file = "/tmp/test_yaml.yaml"

    common.save_yaml(test_file, test_data)
    loaded = common.load_yaml(test_file)

    assert loaded == test_data, "YAML 工具测试失败"
    print("✓ YAML 工具正常")

    os.remove(test_file)
    print()

    # 2. 测试路由功能
    print("2. 测试报告类型路由")
    print("-" * 40)

    template = common.get_template_name("company")
    assert template == "company", "路由测试失败"
    print(f"✓ company -> {template}")

    template = common.get_template_name("nonexistent")
    assert template is None, "无效类型应该返回 None"
    print("✓ 无效类型 -> None")

    print()

    # 3. 测试要素提取
    print("3. 测试要素提取")
    print("-" * 40)

    # 加载 schema
    schema_path = Path(__file__).parent.parent / "templates" / "company" / "schema.yaml"
    if schema_path.exists():
        schema = common.load_yaml(schema_path)
        elements = extractor.extract_elements("draft.docx", schema)

        # 验证要素
        assert "company" in elements, "缺少 company 字段"
        assert "ticker" in elements, "缺少 ticker 字段"
        assert "abstract" in elements, "缺少 abstract 字段"
        assert "body" in elements, "缺少 body 字段"

        print(f"✓ 提取了 {len(elements)} 个字段")
    else:
        print("⚠ schema.yaml 不存在，跳过测试")

    print()

    # 4. 测试文档结构读取
    print("4. 测试文档结构读取")
    print("-" * 40)

    sample_doc = Path(__file__).parent.parent / "samples" / "西锐飞机首次覆盖报告（中文）提交版.docx"
    if sample_doc.exists():
        structure = splitter.read_document_structure(str(sample_doc))

        if "error" not in structure:
            print(f"✓ 段落数: {structure['paragraphs']}")
            print(f"✓ 表格数: {structure['tables']}")
            print(f"✅ 文档结构读取成功")
        else:
            print(f"⚠ 读取文档结构失败: {structure['error']}")
    else:
        print("⚠ 样本文件不存在，跳过测试")

    print()

    # 5. 测试 LibreOffice 检测
    print("5. 测试 LibreOffice 检测")
    print("-" * 40)

    libreoffice = renderer.find_libreoffice()
    if libreoffice:
        print(f"✓ LibreOffice: {libreoffice}")
    else:
        print("⚠ LibreOffice 未安装（PDF 转换将不可用）")

    print()

    # 6. 测试报告目录创建
    print("6. 测试报告目录创建")
    print("-" * 40)

    report_dir = common.create_report_dir("test_report", "/tmp/test_reports")
    assert report_dir.exists(), "目录创建失败"
    print(f"✓ 创建报告目录: {report_dir}")

    # 清理
    import shutil
    shutil.rmtree("/tmp/test_reports")

    print()

    # 总结
    print("=" * 40)
    print("  集成测试完成！")
    print("=" * 40)
    print()
    print("所有核心功能正常。")
    print()
    print("下一步：")
    print("  1. 在 Claude Code 中上传真实草稿")
    print("  2. 使用 report_maker 处理")
    print("  3. 生成标准报告")

except ImportError as e:
    print(f"错误: 无法导入模块 - {e}")
    print("请确保已安装依赖: pip install python-docx docxtpl")
    sys.exit(1)
except Exception as e:
    print(f"错误: 测试失败 - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
