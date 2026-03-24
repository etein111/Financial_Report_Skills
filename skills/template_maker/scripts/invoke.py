#\!/usr/bin/env python3
"""Template Maker 调用入口。

这个脚本提供了对话式创建模板的接口，供 Claude 使用。

用法示例：
    python invoke.py --name "西锐飞机首次覆盖" \
                     --word "samples/西锐飞机首次覆盖报告.docx" \
                     --elements "samples/西锐飞机 elements.yaml"

对话式用法：
    python invoke.py
    # 按提示输入信息
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径（支持作为脚本直接运行）
scripts_dir = Path(__file__).parent
project_root = scripts_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入 TemplateMaker
from skills.template_maker.scripts.core import TemplateMaker


def interactive_mode():
    """对话式模式。"""
    print("=" * 60)
    print("Template Maker - 创建分析师报告模板")
    print("=" * 60)

    # 1. 模板名称
    name = input("\n请输入模板名称（如：西锐飞机首次覆盖）: ").strip()
    if not name:
        print("❌ 模板名称不能为空")
        return 1

    # 2. Word 文件路径
    word_path_str = input("请输入 Word 样本文件路径: ").strip()
    word_path = Path(word_path_str)
    if not word_path.exists():
        print(f"❌ 文件不存在: {word_path}")
        return 1

    # 3. elements.yaml 路径（可选）
    elements_input = input("请输入 elements.yaml 路径（留空自动检测）: ").strip()
    elements_path = Path(elements_input) if elements_input else None

    if elements_path and not elements_path.exists():
        print(f"❌ 文件不存在: {elements_path}")
        return 1

    # 执行创建
    maker = TemplateMaker(project_root)
    result = maker.create_template(name, word_path, elements_path)

    if result.get("status") == "success":
        print(f"\n✅ 模板创建成功！")
        print(f"   模板目录: {result['template_dir']}")
        print(f"   字段数量: {result['fields_count']}")
        return 0
    else:
        print(f"\n❌ 创建失败: {result.get('message')}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Template Maker - 创建分析师报告模板")
    parser.add_argument("--name", help="模板名称")
    parser.add_argument("--word", help="Word 样本文件路径")
    parser.add_argument("--elements", help="elements.yaml 路径（可选）")

    args = parser.parse_args()

    if args.name and args.word:
        maker = TemplateMaker(project_root)
        word_path = Path(args.word)
        elements_path = Path(args.elements) if args.elements else None
        result = maker.create_template(args.name, word_path, elements_path)

        if result.get("status") == "success":
            print(f"✅ 模板创建成功！")
            print(f"   模板目录: {result['template_dir']}")
            return 0
        else:
            print(f"❌ 创建失败: {result.get('message')}")
            return 1
    else:
        return interactive_mode()


if __name__ == "__main__":
    sys.exit(main())