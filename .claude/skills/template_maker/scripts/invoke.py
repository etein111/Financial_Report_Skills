#!/usr/bin/env python3
"""Template Maker 调用入口。

这个脚本提供了对话式创建模板的接口，供 Claude 使用。

用法示例：
    python invoke.py --name "西锐飞机首次覆盖" \\
                     --word "samples/西锐飞机首次覆盖报告.docx" \\
                     --elements "samples/西锐飞机 elements.yaml"

对话式用法：
    python invoke.py
    # 按提示输入信息
"""

import sys
import argparse
from pathlib import Path

# 添加项目路径以导入模块
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

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
    return create_template(name, word_path, elements_path)


def create_template(name: str, word_path: Path, elements_path: Path | None = None) -> int:
    """执行模板创建。

    Args:
        name: 模板名称
        word_path: Word 样本路径
        elements_path: elements.yaml 路径（可选）

    Returns:
        0 成功，1 失败
    """
    print(f"\n📝 正在创建模板: {name}")
    print("-" * 60)

    # 初始化
    maker = TemplateMaker(project_root)

    # 创建模板
    result = maker.create_template(
        name=name,
        word_path=word_path,
        elements_path=elements_path
    )

    # 输出结果
    if result["status"] == "success":
        print(f"✅ 模板创建成功！")
        print(f"   位置: {result['template_dir']}")
        print(f"   字段数: {result['fields_count']}")
        return 0
    else:
        print(f"❌ 创建失败: {result.get('message', '未知错误')}")
        return 1


def main():
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="Template Maker - 创建分析师报告模板",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 对话式模式
  python invoke.py

  # 命令行模式
  python invoke.py --name "西锐飞机首次覆盖" \\
                   --word "samples/西锐飞机首次覆盖报告.docx" \\
                   --elements "samples/西锐飞机 elements.yaml"

  # 自动检测 elements.yaml
  python invoke.py --name "西锐飞机首次覆盖" \\
                   --word "samples/西锐飞机首次覆盖报告.docx"
        """
    )

    parser.add_argument(
        "--name",
        help="模板名称"
    )
    parser.add_argument(
        "--word",
        type=Path,
        help="Word 样本文件路径"
    )
    parser.add_argument(
        "--elements",
        type=Path,
        help="elements.yaml 文件路径（可选，默认自动检测）"
    )

    args = parser.parse_args()

    # 判断模式
    if args.name and args.word:
        # 命令行模式
        return create_template(args.name, args.word, args.elements)
    else:
        # 对话式模式
        return interactive_mode()


if __name__ == "__main__":
    sys.exit(main())
