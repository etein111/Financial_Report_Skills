"""
Neolyst FastAPI 应用主入口
"""
from fastapi import FastAPI

app = FastAPI(
    title="Neolyst API",
    description="投资研究报告管理系统后端 API",
    version="0.1.0",
)


@app.get("/")
async def root():
    """健康检查端点"""
    return {
        "status": "ok",
        "message": "Neolyst API is running",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """详细健康检查"""
    return {
        "status": "healthy",
        "service": "neolyst-backend"
    }
