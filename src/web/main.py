#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : main.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: FastAPI Web应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.web.api import auth, monitor, datacenter, system_config
from src.web.core.database import init_db, close_db
from src.utils.log import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("=" * 60)
    logger.info("Homalos Web应用启动")
    logger.info("=" * 60)
    
    # 初始化数据库
    await init_db()
    
    yield
    
    # 关闭时执行
    logger.info("=" * 60)
    logger.info("Homalos Web应用关闭")
    logger.info("=" * 60)
    
    # 关闭数据库连接
    await close_db()


# 创建FastAPI应用
app = FastAPI(
    title="Homalos量化交易系统",
    description="基于Python的期货量化交易系统Web管理平台",
    version="0.0.1",
    lifespan=lifespan
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vue开发服务器
        "http://localhost:5174",  # Vue开发服务器（备用端口）
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")
app.include_router(datacenter.router, prefix="/api")
app.include_router(system_config.router, prefix="/api")


@app.get("/", tags=["根路径"])
async def root():
    """
    API根路径
    """
    return {
        "message": "Welcome to Homalos量化交易系统",
        "version": "0.0.1",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口
    """
    return {
        "status": "healthy",
        "service": "Homalos Web API"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

