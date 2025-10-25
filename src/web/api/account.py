#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : account.py
@Date       : 2025/10/26
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 账户数据API - 提供实时账户和持仓数据
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.utils.log.logger import get_logger
from src.web.services.trading_core_service import trading_core_service

router = APIRouter(prefix="/account", tags=["账户数据"])
logger = get_logger(__name__)


@router.websocket("/ws")
async def account_websocket(websocket: WebSocket):
    """
    账户数据实时推送 WebSocket
    
    连接后会：
    1. 立即推送最新的账户和持仓数据（如果有）
    2. 订阅实时账户和持仓更新事件
    
    消息格式：
    {
        "type": "account" | "positions",
        "data": {...}
    }
    """
    await websocket.accept()
    logger.info("账户WebSocket连接已建立")
    
    # 创建消息队列
    message_queue: asyncio.Queue = asyncio.Queue()
    
    try:
        # 注册到TradingCoreService（会立即推送缓存数据）
        await trading_core_service.register_account_ws(message_queue)
        
        # 主循环：从队列读取消息并推送到WebSocket
        while True:
            try:
                # 等待消息，设置超时以便定期检查连接状态
                message = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                
                # 发送消息
                await websocket.send_json(message)
            
            except asyncio.TimeoutError:
                # 超时后发送ping消息保持连接
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    # WebSocket已断开
                    break
            
            except WebSocketDisconnect:
                logger.info("账户WebSocket连接断开")
                break
            
            except Exception as e:
                logger.error(f"账户WebSocket消息处理异常: {e}", exc_info=True)
                break
    
    finally:
        # 注销WebSocket
        trading_core_service.unregister_account_ws()
        logger.info("账户WebSocket连接已关闭")


@router.get("/latest")
async def get_latest_account_data():
    """
    获取最新的账户和持仓数据（HTTP接口）
    
    Returns:
        dict: {
            "account": {...},
            "positions": [...]
        }
    """
    return {
        "account": trading_core_service.get_latest_account_data(),
        "positions": trading_core_service.get_latest_positions()
    }

