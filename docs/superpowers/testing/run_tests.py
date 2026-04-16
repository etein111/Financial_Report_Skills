#!/usr/bin/env python
"""
neolyst_integration_test.py — neolyst 集成功能测试脚本

用法:
    python docs/superpowers/testing/run_tests.py

环境变量:
    NEOLYST_URL      — Supabase URL (默认: http://localhost:8000)
    NEOLYST_ANON_KEY — Supabase anon key
    NEOLYST_EMAIL    — 登录邮箱 (若无 session)
    NEOLYST_PASSWORD — 登录密码 (若无 session)
"""

import sys
import os
from pathlib import Path

# ==================== 路径设置 ====================
# 将项目根目录加入 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 添加 skills 目录以便导入 skills.neolyst.scripts 等
SKILLS_DIR = PROJECT_ROOT / "skills"
sys.path.insert(0, str(SKILLS_DIR))

# 设置环境变量（本地 Supabase）
os.environ.setdefault("NEOLYST_URL", "http://localhost:8000")
os.environ.setdefault(
    "NEOLYST_ANON_KEY",
    "***REMOVED-JWT***"
)

# ==================== 导入 ====================
from report_maker.scripts.neolyst_integration import (
    detect_language_from_title,
    compress_investment_thesis,
    resolve_analysts_from_elements,
    get_contact_person_options,
    resolve_coverage_for_report,
    map_elements_to_draft,
    save_draft,
    validate_draft,
    submit_draft,
)
from report_maker.scripts.workflow import (
    prepare_and_save_draft,
    submit_report_workflow,
    COMPANY_REPORT_TYPES,
    SECTOR_REPORT_TYPES,
)

# ==================== 测试函数 ====================

def test_E1_detect_language():
    """E-1: 语言自动判断"""
    print("\n=== E-1: 语言自动判断 ===")

    lang_zh = detect_language_from_title("首次覆盖：配网投资与AI算力双轮驱动")
    lang_en = detect_language_from_title("Cirrus Aircraft Initiates Coverage")

    print(f"  中文标题判定: {lang_zh} (预期: zh)")
    print(f"  英文标题判定: {lang_en} (预期: en)")

    assert lang_zh == "zh", f"Expected zh, got {lang_zh}"
    assert lang_en == "en", f"Expected en, got {lang_en}"
    print("  ✅ E-1 测试通过")


def test_E2_compress_investment_thesis():
    """E-2: 投资要点压缩"""
    print("\n=== E-2: 投资要点压缩 ===")

    long_abstract = "这是很长的摘要内容。" * 50  # 超过 150 字
    compressed = compress_investment_thesis(long_abstract)

    print(f"  原文长度: {len(long_abstract)}")
    print(f"  压缩后长度: {len(compressed)} (预期: <=150)")
    print(f"  压缩后内容: {compressed[:50]}...")

    assert len(compressed) <= 150, f"Expected <=150, got {len(compressed)}"
    print("  ✅ E-2 测试通过")


def test_E3_map_elements_to_draft():
    """E-3: 字段映射"""
    print("\n=== E-3: 字段映射 ===")

    elements = {
        "title": "Cirrus Aircraft Initiates Coverage",
        "ticker": "2507.HK",
        "rating": "Buy",
        "target_price": "15.0",
        "a1": "zhangsan@example.com",
        "a2": "lisi@example.com",
        "abstract": "This is a test abstract.",
    }

    analysts = [
        {"analyst_email": "zhangsan@example.com", "author_order": 1, "analyst_id": "xxx"},
        {"analyst_email": "lisi@example.com", "author_order": 2, "analyst_id": "yyy"},
    ]

    draft = map_elements_to_draft(
        elements=elements,
        report_type="company",
        report_file="/path/to/report.docx",
        pdf_file="/path/to/report.pdf",
        contact_person="zhangsan@example.com",
        analysts=analysts,
        coverage_id="c1111111-1111-1111-1111-111111111111",
    )

    print(f"  title: {draft['title']}")
    print(f"  report_language: {draft['report_language']} (预期: en)")
    print(f"  coverage_id: {draft['coverage_id']}")
    print(f"  ticker: {draft['ticker']}")
    print(f"  rating: {draft['rating']}")

    assert draft["report_language"] == "en"
    assert draft["coverage_id"] == "c1111111-1111-1111-1111-111111111111"
    assert draft["ticker"] == "2507.HK"
    assert draft["rating"] == "Buy"
    print("  ✅ E-3 测试通过")


def test_report_type_constants():
    """验证报告类型常量"""
    print("\n=== 报告类型常量 ===")

    print(f"  COMPANY_REPORT_TYPES: {COMPANY_REPORT_TYPES}")
    print(f"  SECTOR_REPORT_TYPES: {SECTOR_REPORT_TYPES}")

    assert "company" in COMPANY_REPORT_TYPES
    assert "macro" in SECTOR_REPORT_TYPES
    print("  ✅ 报告类型常量测试通过")


def test_get_contact_person_options():
    """测试 contact_person 选项提取"""
    print("\n=== contact_person 选项 ===")

    analysts = [
        {"analyst_email": "zhangsan@example.com", "author_order": 1},
        {"analyst_email": "lisi@example.com", "author_order": 2},
    ]

    options = get_contact_person_options(analysts)
    print(f"  options: {options}")

    assert options == ["zhangsan@example.com", "lisi@example.com"]
    print("  ✅ contact_person 选项测试通过")


def test_supabase_connection():
    """测试 Supabase 连接（需要认证）"""
    print("\n=== Supabase 连接测试 ===")

    try:
        from skills.neolyst.scripts.connection import get_client

        email = os.environ.get("NEOLYST_EMAIL")
        password = os.environ.get("NEOLYST_PASSWORD")

        if email and password:
            client = get_client(email=email, password=password)
        else:
            # 尝试使用 session
            client = get_client()

        print(f"  ✅ Supabase 连接成功: {client}")
    except ValueError as e:
        print(f"  ⚠️ Supabase 认证失败: {e}")
        print("     跳过需要 Supabase 连接的测试")
        return False

    return True


def test_template_publishing_requires_supabase():
    """Group A: 模板发布与复用（需要 Supabase）"""
    print("\n=== Group A: 模板发布与复用 ===")
    print("  ⚠️ 需要 Supabase 连接和有效凭据")
    print("  请确保已执行:")
    print("    - supabase db reset")
    print("    - 上传模板文件到 Storage")
    print("  跳过自动测试")


def test_full_workflow_requires_supabase():
    """Group F: 完整工作流（需要 Supabase）"""
    print("\n=== Group F: 完整工作流 ===")
    print("  ⚠️ 需要 Supabase 连接和有效凭据")
    print("  跳过自动测试")


# ==================== 主函数 ====================

def main():
    print("=" * 60)
    print("neolyst 集成功能测试")
    print("=" * 60)
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"Python: {sys.version}")

    # 本地函数测试（不需要 Supabase）
    try:
        test_E1_detect_language()
        test_E2_compress_investment_thesis()
        test_E3_map_elements_to_draft()
        test_report_type_constants()
        test_get_contact_person_options()
    except AssertionError as e:
        print(f"  ❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Supabase 相关测试
    print("\n" + "=" * 60)
    print("Supabase 相关测试")
    print("=" * 60)

    if test_supabase_connection():
        # 如果 Supabase 连接成功，可以运行更多测试
        print("\n  ✅ Supabase 连接成功，可以运行完整测试")
    else:
        test_template_publishing_requires_supabase()
        test_full_workflow_requires_supabase()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n注意: 部分测试需要 Supabase 连接和有效凭据")
    print("设置环境变量:")
    print("  export NEOLYST_EMAIL=your@email.com")
    print("  export NEOLYST_PASSWORD=your_password")
    print("  export NEOLYST_URL=http://localhost:8000  # 可选")
    print("  export NEOLYST_ANON_KEY=your_anon_key    # 可选")

    return 0


if __name__ == "__main__":
    sys.exit(main())
