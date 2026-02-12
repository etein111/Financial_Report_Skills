#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin 用户初始化脚本

功能：
1. 创建默认 Admin 用户（email: admin@neolyst.com, password: Admin123）
2. 自动配置 JWT 有效期为 24 小时
3. 如果 API 失败，输出手动配置指导

使用方法：
    uv run python scripts/init_admin.py
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# 设置 UTF-8 编码输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from supabase import create_client
except ImportError:
    print("缺少 supabase 依赖，请运行: uv sync")
    sys.exit(1)

# 加载环境变量
load_dotenv()

def init_admin():
    """初始化默认 Admin 用户并配置系统"""

    supabase_url = os.getenv('SUPABASE_URL')
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not service_role_key:
        print("缺少环境变量: SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    print(f"Supabase URL: {supabase_url}")
    print(f"Service Role Key: {service_role_key[:20]}...")

    client = create_client(supabase_url, service_role_key)

    admin_email = "admin@neolyst.com"
    admin_password = "Admin123"

    # 1. 创建 Admin 用户
    print("\n正在创建 Admin 用户...")
    try:
        # 使用 Supabase Auth Admin API
        response = client.auth.admin.create_user({
            'email': admin_email,
            'password': admin_password,
            'email_confirm': True,
            'user_metadata': { 'full_name': 'System Administrator' },
            'app_metadata': { 'role': 'admin', 'provider': 'email' }
        })
        print(f"Admin 用户创建成功: {admin_email}")
        print(f"   密码: {admin_password}")
    except Exception as e:
        error_msg = str(e).lower()
        if "already" in error_msg or "exists" in error_msg or "duplicate" in error_msg:
            print("Admin 用户已存在，跳过创建")
        else:
            print(f"创建 Admin 用户失败: {e}")
            print("\n请在 Supabase Dashboard 中手动创建 Admin 用户:")
            print("  1. 访问: https://supabase.com/dashboard/project/slxeorayantrboopghej/auth/users")
            print(f"  2. 创建用户，邮箱: {admin_email}，密码: {admin_password}")
            print("  3. 在用户详情中设置 app_metadata.role = 'admin'")
            # 不退出，继续执行 JWT 配置

    # 2. 配置 JWT 有效期为 24 小时
    print("\n正在配置 JWT token 有效期...")
    configure_jwt_expiry(supabase_url, service_role_key)

    print("\n初始化完成!")
    print("请在首次登录后修改默认密码")

def configure_jwt_expiry(supabase_url, service_role_key):
    """配置 JWT Token 有效期为 24 小时"""

    # 从 URL 中提取 project_ref
    # URL 格式: https://slxeorayantrboopghej.supabase.co
    project_ref = supabase_url.replace('https://', '').replace('.supabase.co', '')

    management_url = f"https://supabase.com/management/v1/projects/{project_ref}/config/jwt"

    headers = {
        'Authorization': f'Bearer {service_role_key}',
        'Content-Type': 'application/json'
    }

    data = { 'jwt_expiry_limit': 86400 }  # 24 小时 = 86400 秒

    try:
        response = requests.patch(management_url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            print("JWT 有效期已设置为 24 小时 (86400 秒)")
        else:
            print(f"配置 JWT 有效期失败 (状态码: {response.status_code})")
            print("请手动在 Supabase Dashboard 中配置:")
            print("  Settings -> Auth -> JWT Settings -> JWT expiry limit = 86400")
    except Exception as e:
        print(f"配置 JWT 有效期时出错: {e}")
        print("请手动在 Supabase Dashboard 中配置:")
        print("  Settings -> Auth -> JWT Settings -> JWT expiry limit = 86400")

if __name__ == "__main__":
    init_admin()
