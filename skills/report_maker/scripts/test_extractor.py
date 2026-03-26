"""test_extractor.py - 测试自动化提取功能。

验证新的嵌套表格提取功能是否正常工作。
"""

import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.report_maker.scripts import extractor, common


def test_auto_extraction():
    """测试自动化提取功能。"""
    print("=" * 60)
    print("测试自动化提取功能")
    print("=" * 60)

    # 加载 schema
    schema_path = PROJECT_ROOT / "templates" / "company" / "schema.yaml"
    schema = common.load_yaml(schema_path)

    print(f"\n✅ 加载 schema: {len(schema)} 个字段")

    # 草稿文件路径
    draft_path = PROJECT_ROOT / "samples" / "西锐飞机首次覆盖报告（中文）提交版.docx"

    if not draft_path.exists():
        print(f"\n❌ 草稿文件不存在: {draft_path}")
        return

    print(f"✅ 草稿文件: {draft_path.name}")

    # 执行提取
    print(f"\n🔍 开始提取...")
    elements = extractor.extract_elements(
        str(draft_path),
        schema,
        use_auto_extraction=True
    )

    # 显示结果
    print(f"\n📊 提取结果:")
    print("-" * 60)

    # 使用格式化函数
    table = extractor.format_elements_for_confirmation(elements)
    print(table)

    # 统计提取情况
    extracted_count = sum(1 for k, v in elements.items() if v and k not in ['abstract', 'body'])
    total_count = sum(1 for k in elements.keys() if k not in ['abstract', 'body'])

    print(f"\n📈 提取统计: {extracted_count}/{total_count} 个字段")

    # 保存结果
    print(f"\n💾 保存结果到测试目录...")
    test_dir = PROJECT_ROOT / "reports" / "test_extraction"
    test_dir.mkdir(parents=True, exist_ok=True)

    elements_path = test_dir / "elements.yaml"
    common.save_yaml(elements_path, elements)
    print(f"✅ 已保存到: {elements_path}")


if __name__ == "__main__":
    test_auto_extraction()
