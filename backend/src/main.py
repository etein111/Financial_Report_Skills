"""
Neolyst API - FastAPI 主应用入口

投资研究报告管理系统后端服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Neolyst 投资研究报告管理系统 API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# 调试端点 - 测试 RLS
@app.get("/debug/test-rls")
async def test_rls():
    """测试 RLS 是否正确工作"""
    try:
        from .core.supabase import get_supabase
        sb = get_supabase()

        # 获取当前使用的 key 信息
        import base64
        import json

        key_parts = sb.supabase_key.split('.')
        if len(key_parts) >= 2:
            payload = key_parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.b64decode(payload)
            key_info = json.loads(decoded)

        # 尝试插入
        result = sb.table('analyst').insert({
            'full_name': 'Debug RLS Test',
            'email': f'debug_rls_{id(result)}@test.com'
        }).execute()

        return {
            "success": True,
            "key_role": key_info.get('role'),
            "inserted": result.data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Neolyst API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# 调试端点 - 检查配置
@app.get("/debug/config")
async def debug_config():
    """调试端点 - 显示配置信息"""
    return {
        "supabase_url": settings.SUPABASE_URL,
        "service_role_key_preview": settings.SUPABASE_SERVICE_ROLE_KEY[:30] + "...",
        "service_role_key_length": len(settings.SUPABASE_SERVICE_ROLE_KEY),
        "contains_service_role": "service_role" in settings.SUPABASE_SERVICE_ROLE_KEY,
        "debug_mode": settings.DEBUG
    }


# 路由将在后续添加
from .api import auth, users, regions, analyst_info
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(regions.router, prefix="/api/regions", tags=["Regions"])
app.include_router(analyst_info.router, prefix="/api/analyst-info", tags=["Analyst Info"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
