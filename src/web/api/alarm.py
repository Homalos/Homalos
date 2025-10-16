#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : alarm.py
@Date       : 2025/10/16 18:35
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 告警管理API路由
"""
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends
from typing import Optional
import asyncio
import json

from src.web.core.security import get_current_user
from src.web.models.user import User
from src.web.schemas.alarm import (
    AlarmListResponse,
    AlarmRecord,
    AlarmStatsResponse,
    AlarmConfigResponse,
    AlarmConfigUpdate,
    TestAlarmRequest,
    OperationResponse
)
from src.utils.log.logger import get_logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.alarm_manager import AlarmManager

logger = get_logger(__name__)
router = APIRouter(prefix="/alarms", tags=["告警管理"])

# 全局告警管理器实例（由main.py设置）
alarm_manager: Optional["AlarmManager"] = None


def get_alarm_manager():
    """获取告警管理器实例"""
    if alarm_manager is None:
        raise HTTPException(status_code=503, detail="告警管理器未初始化")
    return alarm_manager


# ========== 告警查询端点 ==========

@router.get("", response_model=AlarmListResponse, summary="查询告警列表")
async def query_alarms(
    status: Optional[str] = Query(None, description="状态筛选 (active/acknowledged/resolved)"),
    severity: Optional[str] = Query(None, description="严重程度筛选 (info/warning/error/critical)"),
    alarm_type: Optional[str] = Query(None, description="类型筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 (ISO格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (ISO格式)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user)
):
    """
    查询告警列表，支持多种筛选条件和分页
    
    需要登录认证
    """
    try:
        manager = get_alarm_manager()
        result = await manager.query_alarms(
            status=status,
            severity=severity,
            alarm_type=alarm_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )
        return AlarmListResponse(**result)
    except Exception as e:
        logger.error(f"查询告警列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/{alarm_id}", response_model=AlarmRecord, summary="获取告警详情")
async def get_alarm_detail(
    alarm_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取指定告警的详细信息
    
    需要登录认证
    """
    try:
        manager = get_alarm_manager()
        alarm = await manager.get_alarm_detail(alarm_id)
        if not alarm:
            raise HTTPException(status_code=404, detail="告警不存在")
        return AlarmRecord(**alarm)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取告警详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/stats/summary", response_model=AlarmStatsResponse, summary="获取告警统计")
async def get_alarm_stats(
    current_user: User = Depends(get_current_user)
):
    """
    获取告警统计信息，包括按状态、严重程度、类型的统计
    
    需要登录认证
    """
    try:
        manager = get_alarm_manager()
        stats = await manager.get_alarm_stats()
        return AlarmStatsResponse(**stats)
    except Exception as e:
        logger.error(f"获取告警统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


# ========== 告警操作端点 ==========

@router.post("/{alarm_id}/acknowledge", response_model=OperationResponse, summary="确认告警")
async def acknowledge_alarm(
    alarm_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    确认告警，将状态从 active 改为 acknowledged
    
    需要登录认证
    """
    try:
        manager = get_alarm_manager()
        success = await manager.acknowledge_alarm(alarm_id)
        if success:
            return OperationResponse(status="success", message=f"告警 {alarm_id} 已确认")
        else:
            raise HTTPException(status_code=400, detail="确认失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认告警失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"确认失败: {str(e)}")


@router.post("/{alarm_id}/resolve", response_model=OperationResponse, summary="解决告警")
async def resolve_alarm(
    alarm_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    解决告警，将状态改为 resolved
    
    需要登录认证
    """
    try:
        manager = get_alarm_manager()
        success = await manager.resolve_alarm(alarm_id)
        if success:
            return OperationResponse(status="success", message=f"告警 {alarm_id} 已解决")
        else:
            raise HTTPException(status_code=400, detail="解决失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解决告警失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"解决失败: {str(e)}")


# ========== 告警配置端点 ==========

@router.get("/config/settings", response_model=AlarmConfigResponse, summary="获取告警配置")
async def get_alarm_config(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前告警配置
    
    需要登录认证
    """
    try:
        manager = get_alarm_manager()
        config = await manager.get_config()
        
        # 处理email_enabled可能是布尔值或字符串
        email_enabled_value = config.get("email_enabled", "true")
        if isinstance(email_enabled_value, bool):
            email_enabled = email_enabled_value
        else:
            email_enabled = str(email_enabled_value).lower() == "true"
        
        return AlarmConfigResponse(
            cpu_threshold=int(config.get("cpu_threshold", 80)),
            memory_threshold=int(config.get("memory_threshold", 85)),
            retention_days=int(config.get("retention_days", 30)),
            email_enabled=email_enabled
        )
    except Exception as e:
        logger.error(f"获取告警配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/config/settings", response_model=OperationResponse, summary="更新告警配置")
async def update_alarm_config(
    config_update: AlarmConfigUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    更新告警配置
    
    需要登录认证
    """
    try:
        manager = get_alarm_manager()
        
        # 构建更新字典（只包含非None的字段）
        update_dict = {}
        if config_update.cpu_threshold is not None:
            update_dict["cpu_threshold"] = config_update.cpu_threshold
        if config_update.memory_threshold is not None:
            update_dict["memory_threshold"] = config_update.memory_threshold
        if config_update.retention_days is not None:
            update_dict["retention_days"] = config_update.retention_days
        if config_update.email_enabled is not None:
            update_dict["email_enabled"] = "true" if config_update.email_enabled else "false"
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="没有提供任何更新字段")
        
        success = await manager.update_config(update_dict)
        if success:
            return OperationResponse(status="success", message="告警配置已更新")
        else:
            raise HTTPException(status_code=400, detail="更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


# ========== 测试端点 ==========

@router.post("/test", response_model=OperationResponse, summary="手动触发测试告警")
async def trigger_test_alarm(
    request: TestAlarmRequest,
    current_user: User = Depends(get_current_user)
):
    """
    手动触发一条测试告警，用于测试告警系统和通知功能
    
    需要登录认证
    """
    try:
        manager = get_alarm_manager()
        alarm_id = await manager.trigger_alarm(
            alarm_type=request.alarm_type,
            severity=request.severity,
            source="manual_test",
            message=request.message,
            target=current_user.username,
            details={"test": True, "triggered_by": current_user.username}
        )
        
        if alarm_id:
            return OperationResponse(
                status="success",
                message=f"测试告警已触发，ID: {alarm_id}"
            )
        else:
            return OperationResponse(
                status="skipped",
                message="告警被去重机制跳过"
            )
    except Exception as e:
        logger.error(f"触发测试告警失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


# ========== WebSocket端点 ==========

# WebSocket连接池
ws_connections = set()


@router.websocket("/ws")
async def alarm_websocket(websocket: WebSocket):
    """
    告警WebSocket连接，用于实时推送告警到前端
    
    消息格式：
    {
        "type": "alarm",
        "data": {
            "alarm_id": "...",
            "alarm_type": "...",
            "severity": "...",
            "message": "..."
        }
    }
    """
    await websocket.accept()
    ws_connections.add(websocket)
    logger.info(f"告警WebSocket连接已建立，当前连接数: {len(ws_connections)}")
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "告警推送已连接"
        })
        
        # 保持连接并处理心跳
        while True:
            try:
                # 等待客户端消息（心跳或其他）
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)
                
                # 处理心跳
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # 发送心跳检测
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        logger.info("告警WebSocket连接断开")
    except Exception as e:
        logger.error(f"告警WebSocket错误: {e}", exc_info=True)
    finally:
        ws_connections.discard(websocket)
        logger.info(f"告警WebSocket连接已移除，当前连接数: {len(ws_connections)}")


async def broadcast_alarm(alarm_data: dict):
    """
    广播告警到所有WebSocket连接
    
    Args:
        alarm_data: 告警数据
    """
    if not ws_connections:
        return
    
    message = {
        "type": "alarm",
        "data": alarm_data
    }
    
    # 并发发送到所有连接
    tasks = []
    for ws in list(ws_connections):
        tasks.append(_send_to_ws(ws, message))
    
    await asyncio.gather(*tasks, return_exceptions=True)


async def _send_to_ws(websocket: WebSocket, message: dict):
    """发送消息到单个WebSocket连接"""
    try:
        await websocket.send_json(message)
    except Exception as e:
        logger.error(f"发送WebSocket消息失败: {e}")
        ws_connections.discard(websocket)

