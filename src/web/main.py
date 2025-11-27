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

from src.web.api import auth, monitor, system_config, trading_account, strategy, alarm, trading_system, trading_core, account, admin_auth, brokerage, users, strategy_db, strategy_position, websocket_position
from src.web.core.database import init_db, close_db
from src.web.services.strategy_service import strategy_service
from src.web.services.trading_core_service import TradingCoreService
from src.web.services.monitor_service import MonitorService
from src.web.services.position_sync_service import start_position_sync, stop_position_sync, get_position_sync_service
from src.utils.log import get_logger
from src.utils.get_path import get_path_ins
import asyncio

logger = get_logger(__name__)


def ignore_windows_connection_reset(loop, context):
    """
    自定义事件循环异常处理器，用于抑制Windows下的ConnectionResetError
    
    这是一个已知的Windows + asyncio + ProactorEventLoop问题：
    当浏览器在OPTIONS预检请求后立即关闭连接时，asyncio尝试优雅关闭会触发WinError 10054。
    这个错误不影响功能，只是日志噪音。
    
    参考: https://github.com/encode/uvicorn/issues/1369
    """
    exception = context.get('exception')
    
    # 忽略Windows的ConnectionResetError (WinError 10054)
    if isinstance(exception, ConnectionResetError):
        # 这是预期行为，不需要记录
        return
    
    # 其他异常仍然需要记录
    loop.default_exception_handler(context)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("=" * 60)
    logger.info("Homalos Web应用启动")
    logger.info("=" * 60)
    
    # 设置事件循环异常处理器（Windows专用）
    import sys
    if sys.platform == 'win32':
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(ignore_windows_connection_reset)
        logger.info("已配置Windows ConnectionResetError抑制器")
    
    # 初始化数据库
    await init_db()
    
    # 初始化交易核心服务（不自动启动）
    try:
        trading_core = TradingCoreService.get_instance()
        logger.info("交易核心服务已创建（未启动）")
        logger.info("提示：通过控制台面板手动启动交易核心")
    except Exception as e:
        logger.error(f"交易核心服务创建失败: {e}", exc_info=True)
        raise
    
    # 初始化Web层告警管理器（用于Web通知）
    from src.core.alarm_manager import AlarmManager
    from src.core.notifiers import EmailNotifier, WebSocketNotifier
    from src.web.api.alarm import broadcast_alarm
    
    web_alarm_mgr = None
    try:
        loop = asyncio.get_running_loop()
        db_path = str(get_path_ins.join_path("data", "homalos_web.db"))
        
        # 创建Web层告警管理器
        web_alarm_mgr = AlarmManager(db_path=db_path, loop=loop)
        await web_alarm_mgr.startup()
        
        # 注册WebSocket通知器
        ws_notifier = WebSocketNotifier(broadcast_func=broadcast_alarm)
        web_alarm_mgr.register_notifier(ws_notifier)
        
        # 注册邮件通知器
        async def get_email_config():
            """获取邮件配置的回调函数"""
            from src.web.services.system_config_service import SystemConfigService
            try:
                # 使用 get_notification_config 获取通知配置，包含邮件配置
                result = SystemConfigService.get_notification_config()
                if result.get('success'):
                    # 返回邮件配置部分
                    return result.get('config', {}).get('email', {})
                return {}
            except Exception as err:
                logger.error(f"获取邮件配置失败: {err}")
                return {}
        
        email_notifier = EmailNotifier(config_getter=get_email_config)
        web_alarm_mgr.register_notifier(email_notifier)
        
        # 设置全局告警管理器实例
        alarm.alarm_manager = web_alarm_mgr
        
        # 关联告警管理器到监控服务
        MonitorService.set_alarm_manager(web_alarm_mgr)
        
        logger.info("Web告警管理器初始化成功")
    except Exception as e:
        logger.error(f"Web告警管理器初始化失败: {e}", exc_info=True)
    
    # 初始化策略服务（关联到交易核心）
    try:
        loop = asyncio.get_running_loop()
        
        # 将交易核心传递给策略服务
        strategy_service.set_trading_core(trading_core)
        
        # 将策略服务传递给交易核心（用于停止核心时停止所有策略）
        trading_core.set_strategy_service(strategy_service)
        
        # 初始化策略管理器（即使核心未启动也可以初始化）
        await strategy_service.initialize_manager(loop)
        
        logger.info("策略服务已初始化")
        logger.info("注意：启动策略前需要先启动交易核心")
    except Exception as e:
        logger.error(f"策略服务初始化失败: {e}", exc_info=True)
    
    # 启动持仓同步服务
    try:
        await start_position_sync()
        logger.info("持仓同步服务已启动")
    except Exception as e:
        logger.warning("启动持仓同步服务失败（可能策略管理器未启动）: " + str(e))
    
    yield
    
    # 关闭时执行
    logger.info("=" * 60)
    logger.info("Homalos Web应用关闭")
    logger.info("=" * 60)
    
    # 1. 先关闭交易核心（如果正在运行）
    #    这会先停止所有策略，因此必须在 strategy_service.shutdown() 之前执行
    try:
        trading_core = TradingCoreService.get_instance()
        core_status = trading_core.get_status()
        
        if core_status['status'] in ['running', 'connecting', 'initializing']:
            logger.info("正在停止交易核心...")
            result = await trading_core.stop_core()
            if result['success']:
                logger.info("交易核心已停止")
            else:
                logger.warning(f"交易核心停止异常: {result['message']}")
        else:
            logger.info("交易核心未运行，跳过停止")
    except Exception as e:
        logger.error(f"关闭交易核心失败: {e}", exc_info=True)
    
    # 2. 再关闭策略服务（清理管理器）
    #    此时策略已被 trading_core.stop_core() 停止，这里只是清理资源
    try:
        await strategy_service.shutdown()
        logger.info("策略服务已关闭")
    except Exception as e:
        logger.error(f"关闭策略服务失败: {e}", exc_info=True)
    
    # 3. 关闭持仓同步服务
    try:
        await stop_position_sync()
        logger.info("持仓同步服务已关闭")
    except Exception as e:
        logger.error("关闭持仓同步服务失败: " + str(e), exc_info=True)
    
    # 4. 关闭Web告警管理器
    try:
        if web_alarm_mgr:
            await web_alarm_mgr.shutdown()
            logger.info("Web告警管理器已关闭")
    except Exception as e:
        logger.error(f"关闭Web告警管理器失败: {e}", exc_info=True)
    
    # 关闭数据库连接
    await close_db()
    
    logger.info("=" * 60)
    logger.info("Homalos Web应用已完全关闭")
    logger.info("=" * 60)


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
app.include_router(admin_auth.router, prefix="/api")      # 管理员认证路由
app.include_router(monitor.router, prefix="/api")
# datacenter.router 已移除 - 数据中心功能已废弃
app.include_router(system_config.router, prefix="/api")
app.include_router(trading_account.router, prefix="/api")
app.include_router(brokerage.router, prefix="/api")       # 用户券商账户路由（新）
app.include_router(users.router, prefix="/api")           # 用户管理路由
app.include_router(strategy.router, prefix="/api")
app.include_router(strategy_db.router)                    # 策略数据库路由
app.include_router(strategy_position.router)              # 策略持仓路由
app.include_router(websocket_position.router)             # WebSocket 持仓推送路由
app.include_router(alarm.router, prefix="/api")
app.include_router(account.router, prefix="/api")
app.include_router(trading_system.router, prefix="/api")  # 旧版（subprocess方式）
app.include_router(trading_core.router, prefix="/api")   # 新版（内嵌核心方式）


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


@app.get("/api/position-sync/stats", tags=["持仓同步"])
async def get_position_sync_stats():
    """
    获取持仓同步统计信息
    
    返回持仓同步服务的统计数据，包括：
    - is_running: 服务是否运行中
    - zmq_url: ZeroMQ 连接地址
    - received: 接收的消息数
    - synced: 成功同步的数量
    - failed: 失败的数量
    - last_sync_time: 最后同步时间
    """
    try:
        service = get_position_sync_service()
        stats = service.get_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error("获取持仓同步统计失败: " + str(e))
        return {
            "success": False,
            "error": str(e)
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

