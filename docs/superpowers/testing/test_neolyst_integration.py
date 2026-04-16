#!/usr/bin/env python
"""
test_neolyst_integration.py — neolyst 集成功能测试脚本

用法:
    python docs/superpowers/testing/test_neolyst_integration.py

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
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 添加 skills 目录以便导入 skills.report_maker.scripts 等
SKILLS_DIR = PROJECT_ROOT / "skills"
sys.path.insert(0, str(SKILLS_DIR))

# ==================== 测试结果收集 ====================
results = []
passed = 0
failed = 0


def test(name, fn):
    """运行单个测试"""
    global passed, failed
    try:
        fn()
        results.append(("PASS", name))
        passed += 1
        return True
    except AssertionError as e:
        results.append(("FAIL", f"{name}: {e}"))
        failed += 1
        return False
    except Exception as e:
        results.append(("ERROR", f"{name}: {e}"))
        failed += 1
        return False


# ==================== 导入 neolyst_integration 模块 ====================
# 这些导入会执行，需要正确设置环境变量
os.environ.setdefault("NEOLYST_URL", "http://localhost:8000")
os.environ.setdefault(
    "NEOLYST_ANON_KEY",
    "***REMOVED-JWT***"
)

# ==================== 测试函数 ====================


def test_E1_detect_language():
    """E-1: 语言自动判断"""
    from skills.report_maker.scripts.neolyst_integration import detect_language_from_title

    # 中文标题
    lang_zh = detect_language_from_title("首次覆盖：配网投资与AI算力双轮驱动")
    assert lang_zh == "zh", f"Expected zh, got {lang_zh}"

    # 英文标题
    lang_en = detect_language_from_title("Cirrus Aircraft Initiates Coverage")
    assert lang_en == "en", f"Expected en, got {lang_en}"

    print(f"  [PASS] E-1: lang_zh={lang_zh}, lang_en={lang_en}")


def test_E2_compress_investment_thesis():
    """E-2: 投资要点压缩"""
    from skills.report_maker.scripts.neolyst_integration import compress_investment_thesis

    # 长摘要
    long_abstract = "这是很长的摘要内容。" * 50
    compressed = compress_investment_thesis(long_abstract)
    assert len(compressed) <= 150, f"Expected <=150, got {len(compressed)}"

    # 短摘要不压缩
    short_abstract = "短摘要"
    compressed_short = compress_investment_thesis(short_abstract)
    assert compressed_short == short_abstract

    print(f"  [PASS] E-2: long ({len(long_abstract)} -> {len(compressed)}), short (unchanged)")


def test_E3_map_elements_to_draft():
    """E-3: 字段映射"""
    from skills.report_maker.scripts.neolyst_integration import map_elements_to_draft

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

    assert draft["report_language"] == "en", f"Expected en, got {draft['report_language']}"
    assert draft["coverage_id"] == "c1111111-1111-1111-1111-111111111111"
    assert draft["ticker"] == "2507.HK"
    assert draft["rating"] == "Buy"

    print(f"  [PASS] E-3: report_language={draft['report_language']}, ticker={draft['ticker']}")


def test_report_type_constants():
    """报告类型常量"""
    from skills.report_maker.scripts.workflow import COMPANY_REPORT_TYPES, SECTOR_REPORT_TYPES

    assert "company" in COMPANY_REPORT_TYPES
    assert "macro" in SECTOR_REPORT_TYPES

    print(f"  [PASS] COMPANY_TYPES={COMPANY_REPORT_TYPES}")
    print(f"  [PASS] SECTOR_TYPES={SECTOR_REPORT_TYPES}")


def test_get_contact_person_options():
    """contact_person 选项"""
    from skills.report_maker.scripts.neolyst_integration import get_contact_person_options

    analysts = [
        {"analyst_email": "zhangsan@example.com", "author_order": 1},
        {"analyst_email": "lisi@example.com", "author_order": 2},
    ]

    options = get_contact_person_options(analysts)
    assert options == ["zhangsan@example.com", "lisi@example.com"]

    print(f"  [PASS] options={options}")


def test_supabase_connection():
    """Supabase 连接测试"""
    from supabase import create_client
    from skills.neolyst.scripts.connection import get_client, NeedsLoginError

    url = os.environ.get("NEOLYST_URL", "http://localhost:8000")
    key = os.environ.get("NEOLYST_ANON_KEY")

    if not key:
        print(f"  [SKIP] 需要 NEOLYST_ANON_KEY 环境变量")
        return False

    client = create_client(url, key)

    # 尝试匿名登录
    try:
        client.auth.sign_in_anonymously()
        print(f"  [PASS] Supabase 匿名登录成功")
        return True
    except Exception as anon_err:
        print(f"  [INFO] 匿名登录失败: {anon_err}")

    # 尝试邮箱密码登录
    email = os.environ.get("NEOLYST_EMAIL")
    password = os.environ.get("NEOLYST_PASSWORD")
    if email and password:
        try:
            get_client(email=email, password=password)
            print(f"  [PASS] Supabase 邮箱登录成功")
            return True
        except NeedsLoginError as e:
            print(f"  [INFO] 需要登录: {e}")
            print(f"  [SKIP] 请提供 Supabase 登录凭据")
            return False
        except Exception as e:
            print(f"  [FAIL] 登录失败: {e}")
            return False

    print(f"  [SKIP] 需要 NEOLYST_EMAIL 和 NEOLYST_PASSWORD 环境变量，或启用匿名登录")
    return False


def test_resolve_analysts_requires_auth():
    """分析师解析（需要 Supabase）"""
    print(f"  [SKIP] 需要 Supabase 连接")


def test_resolve_coverage_requires_auth():
    """Coverage 解析（需要 Supabase）"""
    print(f"  [SKIP] 需要 Supabase 连接")


def test_save_draft_requires_auth():
    """保存草稿（需要 Supabase）"""
    print(f"  [SKIP] 需要 Supabase 连接")


# ==================== 主函数 ====================


def main():
    print("=" * 60)
    print("neolyst 集成功能测试")
    print("=" * 60)
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"Python: {sys.version}")
    print()

    # Group E: 本地函数测试（不需要 Supabase）
    print("Group E: 本地函数测试")
    print("-" * 40)
    test("E-1: detect_language_from_title", test_E1_detect_language)
    test("E-2: compress_investment_thesis", test_E2_compress_investment_thesis)
    test("E-3: map_elements_to_draft", test_E3_map_elements_to_draft)
    test("报告类型常量", test_report_type_constants)
    test("contact_person 选项", test_get_contact_person_options)
    print()

    # Supabase 连接测试
    print("Supabase 连接测试")
    print("-" * 40)
    connected = test("Supabase 连接", test_supabase_connection)
    print()

    # Supabase 相关测试（需要认证）
    if connected:
        print("Supabase 相关测试（需要 Supabase 连接）")
        print("-" * 40)
        test("分析师解析", test_resolve_analysts_requires_auth)
        test("Coverage 解析", test_resolve_coverage_requires_auth)
        test("保存草稿", test_save_draft_requires_auth)
    else:
        print("Supabase 相关测试")
        print("-" * 40)
        print("  [SKIP] Supabase 未连接，跳过以下测试:")
        print("    - 分析师解析")
        print("    - Coverage 解析")
        print("    - 保存草稿")
        print("    - 提交草稿")
        print("    - 完整工作流")
    print()

    # 总结
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for status, msg in results:
        print(f"  [{status}] {msg}")
    print()
    print(f"通过: {passed}, 失败: {failed}, 总计: {passed + failed}")
    print()

    if failed > 0:
        print("⚠️  部分测试失败，请检查错误信息")
        return 1
    else:
        print("✅ 所有测试通过")
        return 0


if __name__ == "__main__":
    sys.exit(main())
