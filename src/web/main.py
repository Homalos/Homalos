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

from src.web.api import auth, monitor, datacenter, system_config, trading_account, strategy, alarm
from src.web.core.database import init_db, close_db
from src.web.services.strategy_service import strategy_service
from src.web.services.monitor_service import MonitorService
from src.utils.log import get_logger
from src.utils.get_path import get_path_ins
import asyncio

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
    
    # 初始化告警管理器
    from src.core.alarm_manager import AlarmManager
    from src.core.notifiers import EmailNotifier, WebSocketNotifier
    from src.web.api.alarm import broadcast_alarm
    
    try:
        loop = asyncio.get_running_loop()
        db_path = str(get_path_ins.join_path("data", "homalos_web.db"))
        
        # 创建告警管理器
        alarm_mgr = AlarmManager(db_path=db_path, loop=loop)
        await alarm_mgr.startup()
        
        # 注册WebSocket通知器
        ws_notifier = WebSocketNotifier(broadcast_func=broadcast_alarm)
        alarm_mgr.register_notifier(ws_notifier)
        
        # 注册邮件通知器
        async def get_email_config():
            """获取邮件配置的回调函数"""
            from src.web.services.system_config_service import SystemConfigService
            try:
                config = await SystemConfigService.get_email_config()
                return config
            except Exception:
                return {}
        
        email_notifier = EmailNotifier(config_getter=get_email_config)
        alarm_mgr.register_notifier(email_notifier)
        
        # 设置全局告警管理器实例
        alarm.alarm_manager = alarm_mgr
        
        # 关联告警管理器到监控服务
        MonitorService.set_alarm_manager(alarm_mgr)
        
        logger.info("告警管理器初始化成功")
    except Exception as e:
        logger.error(f"告警管理器初始化失败: {e}", exc_info=True)
    
    # 初始化策略管理器
    try:
        loop = asyncio.get_running_loop()
        await strategy_service.initialize_manager(loop)
        
        # 关联告警管理器到策略管理器
        manager = strategy_service.get_manager()
        manager.alarm_manager = alarm_mgr
        
        logger.info("策略管理器初始化成功")
    except Exception as e:
        logger.error(f"策略管理器初始化失败: {e}", exc_info=True)
    
    yield
    
    # 关闭时执行
    logger.info("=" * 60)
    logger.info("Homalos Web应用关闭")
    logger.info("=" * 60)
    
    # 关闭策略管理器
    try:
        await strategy_service.shutdown()
        logger.info("策略管理器已关闭")
    except Exception as e:
        logger.error(f"关闭策略管理器失败: {e}", exc_info=True)
    
    # 关闭告警管理器
    try:
        if alarm.alarm_manager:
            await alarm.alarm_manager.shutdown()
            logger.info("告警管理器已关闭")
    except Exception as e:
        logger.error(f"关闭告警管理器失败: {e}", exc_info=True)
    
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
app.include_router(trading_account.router, prefix="/api")
app.include_router(strategy.router, prefix="/api")
app.include_router(alarm.router, prefix="/api")


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

