#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_core.py
@Date       : 2025/10/23
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易核心控制API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.core.database import get_db
from src.web.core.security import get_current_user
from src.web.models.user import User
from src.web.schemas.trading_core import (
    StartCoreRequest,
    StartCoreResponse,
    StopCoreRequest,
    StopCoreResponse,
    ConnectGatewayRequest,
    ConnectGatewayResponse,
    CoreStatusResponse,
    ModulesResponse,
    ModuleStatusInfo,
    BaseResponse,
)
from src.web.services.trading_core_service import TradingCoreService
from src.utils.log.logger import get_logger

router = APIRouter(prefix="/trading-core", tags=["交易核心管理"])
logger = get_logger(__name__)


def check_admin_permission(current_user: User):
    """检查管理员权限"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限才能控制交易核心"
        )


@router.post("/start", response_model=StartCoreResponse, summary="启动交易核心")
async def start_trading_core(
    request: StartCoreRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    启动交易核心模块
    
    需要管理员权限。
    启动后会初始化所有核心模块（EventBus、网关、风控等）。
    """
    check_admin_permission(current_user)
    
    try:
        core_service = TradingCoreService.get_instance()
        
        # 启动核心
        result = await core_service.start_core(
            config=request.config,
            auto_connect_gateway=request.auto_connect_gateway
        )
        
        # 记录审计日志
        from src.web.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            operation_type="start_trading_core",
            target="trading_core",
            details=f"启动结果: {result['message']}",
            success=result['success']
        )
        db.add(audit_log)
        await db.commit()
        
        return StartCoreResponse(
            success=result['success'],
            message=result['message'],
            status=result.get('status'),
            startup_time=result.get('startup_time')
        )
        
    except Exception as e:
        logger.error(f"启动交易核心失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动失败: {str(e)}"
        )


@router.get("/running-strategies-count", summary="获取运行中的策略数量")
async def get_running_strategies_count(
    current_user: User = Depends(get_current_user)
):
    """
    获取运行中的策略数量
    
    用于停止核心前的检查，确保用户了解影响范围。
    """
    try:
        core_service = TradingCoreService.get_instance()
        count = core_service.get_running_strategies_count()
        
        return {
            "success": True,
            "count": count
        }
        
    except Exception as e:
        logger.error(f"获取运行中策略数量失败: {e}", exc_info=True)
        return {
            "success": False,
            "count": 0,
            "message": str(e)
        }


@router.post("/stop", response_model=StopCoreResponse, summary="停止交易核心")
async def stop_trading_core(
    request: StopCoreRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    停止交易核心模块
    
    需要管理员权限。
    停止后会关闭所有核心模块并清理资源。
    如果有运行中的策略，会自动停止所有策略。
    """
    check_admin_permission(current_user)
    
    try:
        core_service = TradingCoreService.get_instance()
        
        # 检查运行中的策略数量（用于前端警告提示）
        running_count = core_service.get_running_strategies_count()
        
        # 停止核心（会自动停止所有运行中的策略）
        result = await core_service.stop_core(
            force=request.force,
            timeout=request.timeout
        )
        
        # 记录审计日志
        from src.web.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            operation_type="stop_trading_core",
            target="trading_core",
            details=f"停止结果: {result['message']}, force={request.force}, 停止策略数: {result.get('stopped_strategies_count', 0)}",
            success=result['success']
        )
        db.add(audit_log)
        await db.commit()
        
        return StopCoreResponse(
            success=result['success'],
            message=result['message'],
            shutdown_time=result.get('shutdown_time'),
            stopped_strategies_count=result.get('stopped_strategies_count', 0)
        )
        
    except Exception as e:
        logger.error(f"停止交易核心失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止失败: {str(e)}"
        )


@router.post("/restart", response_model=StartCoreResponse, summary="重启交易核心")
async def restart_trading_core(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    重启交易核心
    
    需要管理员权限。
    先停止再启动核心。
    """
    check_admin_permission(current_user)
    
    try:
        core_service = TradingCoreService.get_instance()
        
        # 先停止
        stop_result = await core_service.stop_core()
        if not stop_result['success']:
            raise Exception(f"停止失败: {stop_result['message']}")
        
        # 再启动
        start_result = await core_service.start_core()
        
        # 记录审计日志
        from src.web.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            operation_type="restart_trading_core",
            target="trading_core",
            details=f"重启结果: {start_result['message']}",
            success=start_result['success']
        )
        db.add(audit_log)
        await db.commit()
        
        return StartCoreResponse(
            success=start_result['success'],
            message=f"重启成功: {start_result['message']}",
            status=start_result.get('status'),
            startup_time=start_result.get('startup_time')
        )
        
    except Exception as e:
        logger.error(f"重启交易核心失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重启失败: {str(e)}"
        )


@router.get("/status", response_model=CoreStatusResponse, summary="获取核心状态")
async def get_trading_core_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取交易核心详细状态
    
    包括：
    - 核心运行状态
    - 网关连接状态
    - 各模块状态
    - 统计信息
    """
    try:
        core_service = TradingCoreService.get_instance()
        status_data = core_service.get_status()
        
        return CoreStatusResponse(**status_data)
        
    except Exception as e:
        logger.error(f"获取核心状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取状态失败: {str(e)}"
        )


@router.post("/gateway/connect", response_model=ConnectGatewayResponse, summary="连接CTP网关")
async def connect_gateway(
    request: ConnectGatewayRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    连接CTP网关
    
    需要管理员权限。
    前提：交易核心必须已启动。
    """
    check_admin_permission(current_user)
    
    try:
        core_service = TradingCoreService.get_instance()
        
        # 检查核心是否运行
        status_data = core_service.get_status()
        if status_data['status'] != 'running':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"交易核心未运行（当前状态：{status_data['status']}），无法连接网关"
            )
        
        # 连接网关
        result = await core_service.connect_gateway(request.broker_config)
        
        # 记录审计日志
        from src.web.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            operation_type="connect_gateway",
            target="trading_core",
            details=f"连接结果: {result['message']}",
            success=result['success']
        )
        db.add(audit_log)
        await db.commit()
        
        return ConnectGatewayResponse(
            success=result['success'],
            message=result['message'],
            gateway=result.get('gateway'),
            connection_time=result.get('connection_time')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"连接网关失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"连接失败: {str(e)}"
        )


@router.post("/gateway/disconnect", response_model=BaseResponse, summary="断开CTP网关")
async def disconnect_gateway(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    断开CTP网关连接
    
    需要管理员权限。
    """
    check_admin_permission(current_user)
    
    try:
        core_service = TradingCoreService.get_instance()
        
        # 断开网关
        result = await core_service.disconnect_gateway()
        
        # 记录审计日志
        from src.web.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            operation_type="disconnect_gateway",
            target="trading_core",
            details=f"断开结果: {result['message']}",
            success=result['success']
        )
        db.add(audit_log)
        await db.commit()
        
        return BaseResponse(
            success=result['success'],
            message=result['message']
        )
        
    except Exception as e:
        logger.error(f"断开网关失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"断开失败: {str(e)}"
        )


@router.get("/modules", response_model=ModulesResponse, summary="获取模块状态列表")
async def get_core_modules(
    current_user: User = Depends(get_current_user)
):
    """
    获取所有核心模块的状态列表
    
    包括：EventBus、网关、风控、信号处理器等。
    """
    try:
        core_service = TradingCoreService.get_instance()
        status_data = core_service.get_status()
        
        # 转换为列表格式
        modules = []
        module_descriptions = {
            "event_bus": "事件总线",
            "alarm_manager": "告警管理器",
            "subscription_manager": "订阅管理器",
            "trade_signal_handler": "交易信号处理器",
            "risk_manager": "风险管理器",
            "market_gateway": "行情网关",
            "trader_gateway": "交易网关",
            "bar_generator": "K线合成器"
        }
        
        for module_name, module_status in status_data.get('modules', {}).items():
            modules.append(ModuleStatusInfo(
                name=module_name,
                status=module_status,
                description=module_descriptions.get(module_name, module_name)
            ))
        
        return ModulesResponse(
            success=True,
            modules=modules
        )
        
    except Exception as e:
        logger.error(f"获取模块列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取失败: {str(e)}"
        )

