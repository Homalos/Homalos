#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy.py
@Date       : 2025/10/16
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略管理 API Router

提供以下接口:
- GET `/` - 列出所有注册策略
- POST `/{sid}/start` - 启动策略
- POST `/{sid}/stop` - 停止策略
- POST `/{sid}/reload` - 重载策略
- POST `/{sid}/enable` - 启用策略
- POST `/{sid}/disable` - 禁用策略
- GET `/status` - 查看策略运行状态
- WebSocket `/ws` - 实时接收策略消息（支持 ?filter=sid 查询参数）
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Optional

from src.web.services.strategy_service import strategy_service
from src.web.schemas.strategy import (
    StrategyListResponse,
    StrategyStatusResponse,
    OperationResponse
)
from src.utils.log import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/strategies", tags=["策略管理"])


@router.get("/", response_model=StrategyListResponse, summary="获取策略列表")
async def list_strategies():
    """
    获取所有注册的策略配置
    
    Returns:
        StrategyListResponse: 包含所有策略配置的字典
    """
    try:
        strategies = strategy_service.list_strategies()
        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取策略列表失败: {str(e)}")


@router.post("/{sid}/start", response_model=OperationResponse, summary="启动策略")
async def start_strategy(sid: str):
    """
    启动指定的策略
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        strategy_service.start_strategy(sid)
        return {
            "status": "started",
            "sid": sid,
            "message": f"策略 {sid} 已成功启动"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"启动策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动策略失败: {str(e)}")


@router.post("/{sid}/stop", response_model=OperationResponse, summary="停止策略")
async def stop_strategy(sid: str):
    """
    停止指定的策略
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        strategy_service.stop_strategy(sid)
        return {
            "status": "stopped",
            "sid": sid,
            "message": f"策略 {sid} 已停止"
        }
    except Exception as e:
        logger.error(f"停止策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"停止策略失败: {str(e)}")


@router.post("/{sid}/reload", response_model=OperationResponse, summary="重载策略")
async def reload_strategy(sid: str):
    """
    重载指定的策略（保存状态、重启、恢复状态）
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        await strategy_service.reload_strategy(sid)
        return {
            "status": "reloaded",
            "sid": sid,
            "message": f"策略 {sid} 已重载"
        }
    except Exception as e:
        logger.error(f"重载策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重载策略失败: {str(e)}")


@router.post("/{sid}/enable", response_model=OperationResponse, summary="启用策略")
async def enable_strategy(sid: str):
    """
    在注册中心启用策略（下次启动时自动加载）
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        strategy_service.enable_strategy(sid)
        return {
            "status": "enabled",
            "sid": sid,
            "message": f"策略 {sid} 已启用"
        }
    except Exception as e:
        logger.error(f"启用策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启用策略失败: {str(e)}")


@router.post("/{sid}/disable", response_model=OperationResponse, summary="禁用策略")
async def disable_strategy(sid: str):
    """
    在注册中心禁用策略（下次启动时不自动加载）
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        strategy_service.disable_strategy(sid)
        return {
            "status": "disabled",
            "sid": sid,
            "message": f"策略 {sid} 已禁用"
        }
    except Exception as e:
        logger.error(f"禁用策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"禁用策略失败: {str(e)}")


@router.delete("/{sid}/unload", response_model=OperationResponse, summary="卸载策略")
async def unload_strategy(sid: str):
    """
    卸载指定的策略（停止运行并从管理器中移除）
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        strategy_service.unload_strategy(sid)
        return {
            "status": "unloaded",
            "sid": sid,
            "message": f"策略 {sid} 已卸载"
        }
    except Exception as e:
        logger.error(f"卸载策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"卸载策略失败: {str(e)}")


@router.get("/debug/reloading", summary="获取正在reload的策略（调试）")
async def get_reloading_strategies():
    """获取当前正在reload的策略列表（用于调试）"""
    reloading = strategy_service.get_reloading_strategies()
    return {"reloading": reloading}


@router.post("/debug/clear-lock/{sid}", summary="清除reload锁（调试）")
async def clear_reload_lock(sid: str):
    """清除策略的reload锁（用于恢复卡住的状态）"""
    result = strategy_service.clear_reload_lock(sid)
    if result:
        return {"status": "cleared", "sid": sid, "message": f"已清除 {sid} 的reload锁"}
    else:
        return {"status": "not_found", "sid": sid, "message": f"{sid} 没有reload锁"}


# ========== 状态持久化相关端点 ==========

@router.post("/{sid}/state/save", summary="手动保存策略状态")
async def save_strategy_state(sid: str):
    """
    手动保存指定策略的当前状态到文件
    
    Args:
        sid: 策略ID
        
    Returns:
        操作结果
    """
    try:
        success = await strategy_service.save_strategy_state(sid)
        if success:
            return {
                "status": "saved",
                "sid": sid,
                "message": f"策略 {sid} 的状态已保存"
            }
        else:
            return {
                "status": "failed",
                "sid": sid,
                "message": f"策略 {sid} 的状态保存失败"
            }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"保存策略 {sid} 状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存状态失败: {str(e)}")


@router.get("/{sid}/state", summary="获取策略状态")
async def get_strategy_state(
    sid: str,
    timestamp: Optional[str] = Query(None, description="可选：指定时间戳（格式：20251016_143000）")
):
    """
    获取策略的保存状态
    
    Args:
        sid: 策略ID
        timestamp: 可选，指定时间戳获取历史状态
        
    Returns:
        策略状态数据
    """
    try:
        state = await strategy_service.load_strategy_state(sid, timestamp or "")
        if state is None:
            raise HTTPException(status_code=404, detail=f"策略 {sid} 没有保存的状态")
        
        return {
            "sid": sid,
            "timestamp": timestamp or "latest",
            "state": state
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略 {sid} 状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/{sid}/state/history", summary="获取状态历史列表")
async def get_state_history(
    sid: str,
    limit: int = Query(10, ge=1, le=100, description="返回最近N条记录")
):
    """
    获取策略的状态历史列表（不包含状态数据，只有元信息）
    
    Args:
        sid: 策略ID
        limit: 返回最近N条记录
        
    Returns:
        历史记录列表
    """
    try:
        history = await strategy_service.get_state_history(sid, limit)
        return {
            "sid": sid,
            "count": len(history),
            "history": history
        }
    except Exception as e:
        logger.error(f"获取策略 {sid} 历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.delete("/states/cleanup", summary="清理旧状态")
async def cleanup_old_states(
    days: int = Query(30, ge=1, le=365, description="保留最近N天的状态")
):
    """
    清理超过指定天数的旧状态文件
    
    Args:
        days: 保留最近N天
        
    Returns:
        清理结果
    """
    try:
        await strategy_service.cleanup_old_states(days)
        return {
            "status": "success",
            "message": f"已清理超过 {days} 天的旧状态",
            "days": days
        }
    except Exception as e:
        logger.error(f"清理旧状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/states/storage-info", summary="获取存储信息")
async def get_storage_info():
    """
    获取状态存储的统计信息
    
    Returns:
        存储统计数据
    """
    try:
        info = strategy_service.get_storage_info()
        return info
    except Exception as e:
        logger.error(f"获取存储信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取存储信息失败: {str(e)}")


@router.get("/status", response_model=StrategyStatusResponse, summary="获取策略运行状态")
async def get_strategy_status():
    """
    获取所有运行中策略的状态信息
    
    Returns:
        StrategyStatusResponse: 运行状态字典
    """
    try:
        status = strategy_service.get_status()
        return {"running": status}
    except Exception as e:
        logger.error(f"获取策略状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取策略状态失败: {str(e)}")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    filter: Optional[str] = Query(None, description="可选：只接收指定策略ID的消息")
):
    """
    WebSocket 端点，用于实时接收策略消息
    
    Args:
        websocket: WebSocket连接
        filter: 可选，指定策略ID进行消息过滤
        
    消息格式:
        {
            "type": "log"|"error"|"status"|"order"|"trade",
            "sid": "策略ID",
            "payload": "消息内容",
            "trace": "错误堆栈（仅error类型）"
        }
    """
    await websocket.accept()
    logger.info(f"WebSocket连接已建立, filter={filter}")
    
    # 创建消息队列
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    
    try:
        # 注册队列到策略服务
        strategy_service.register_ws_queue(q)
        
        # 持续接收并转发消息
        while True:
            msg = await q.get()
            
            # 可选过滤
            if filter and msg.get("sid") != filter:
                continue
            
            # 发送消息
            await websocket.send_json(msg)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接已断开, filter={filter}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}", exc_info=True)
    finally:
        # 清理：注销队列
        strategy_service.unregister_ws_queue(q)
        try:
            await websocket.close()
        except Exception:
            pass

