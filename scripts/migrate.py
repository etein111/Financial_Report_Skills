#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移执行脚本

使用方法：
1. 在 Supabase Dashboard 的 SQL Editor 中手动执行迁移脚本
   （推荐方式：https://supabase.com/dashboard/project/slxeorayantrboopghej/sql/new）

2. 或者使用本脚本自动执行（需要配置环境变量）
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 设置 UTF-8 编码输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from supabase import create_client
except ImportError:
    print("❌ 缺少 supabase 依赖，请运行: uv sync")
    sys.exit(1)

# 加载环境变量
load_dotenv()

def read_migration_file(filename: str) -> str:
    """读取迁移文件内容"""
    migration_path = Path(__file__).parent / "migrations" / filename
    with open(migration_path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    """执行数据库迁移"""
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        print("❌ 缺少环境变量: SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY")
        print("\n💡 推荐做法：在 Supabase Dashboard 的 SQL Editor 中手动执行迁移脚本")
        print("   访问: https://supabase.com/dashboard/project/slxeorayantrboopghej/sql/new")
        print("\n   需要按顺序执行以下文件：")
        print("   1. migrations/000_create_rls_function.sql")
        print("   2. migrations/001_create_region_table.sql")
        print("   3. migrations/002_create_analyst_table.sql")
        return

    print("📋 Neolyst 数据库迁移脚本")
    print("=" * 50)

    # 获取迁移文件列表
    migrations = [
        "000_create_rls_function.sql",
        "001_create_region_table.sql",
        "002_create_analyst_table.sql",
    ]

    print("\n⚠️  注意：Supabase 不支持通过 Python Client 执行 DDL 语句")
    print("\n💡 请在 Supabase Dashboard 的 SQL Editor 中手动执行以下迁移文件：\n")

    for i, migration in enumerate(migrations, 1):
        print(f"   {i}. {migration}")

    print("\n🔗 SQL Editor: https://supabase.com/dashboard/project/slxeorayantrboopghej/sql/new")

if __name__ == "__main__":
    main()
