#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : websocket_position.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: WebSocket 持仓推送路由
"""
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from src.web.services.websocket_manager import get_websocket_manager
from src.utils.log import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])
ws_manager = get_websocket_manager()


@router.websocket("/positions")
async def websocket_positions(
    websocket: WebSocket,
    strategy_id: int = Query(None, description="策略ID（可选，用于订阅特定策略）")
):
    """
    WebSocket 持仓推送端点
    
    客户端可以通过此端点订阅持仓更新：
    - ws://localhost:8000/ws/positions?strategy_id=1 - 订阅策略1的持仓更新
    - ws://localhost:8000/ws/positions - 不订阅任何策略，稍后通过消息订阅
    
    客户端消息格式：
    {
        "type": "subscribe",
        "strategy_id": 1
    }
    
    {
        "type": "unsubscribe",
        "strategy_id": 1
    }
    
    服务器推送消息格式：
    {
        "type": "position_update",
        "strategy_id": 1,
        "data": {
            "position_id": 1,
            "symbol": "SA601",
            "direction": "LONG",
            "volume": 10,
            ...
        }
    }
    """
    # 生成客户端唯一标识
    client_id = str(uuid.uuid4())
    
    try:
        # 建立连接
        await ws_manager.connect(client_id, websocket)
        logger.info("WebSocket 客户端已连接: " + client_id)
        
        # 如果指定了策略ID，自动订阅
        if strategy_id:
            ws_manager.subscribe(client_id, strategy_id)
            logger.info("客户端自动订阅策略: " + client_id + " -> " + str(strategy_id))
        
        # 监听客户端消息
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "subscribe":
                    # 订阅策略
                    sid = message.get("strategy_id")
                    if sid:
                        ws_manager.subscribe(client_id, sid)
                        logger.debug("客户端订阅策略: " + client_id + " -> " + str(sid))
                
                elif msg_type == "unsubscribe":
                    # 取消订阅策略
                    sid = message.get("strategy_id")
                    if sid:
                        ws_manager.unsubscribe(client_id, sid)
                        logger.debug("客户端取消订阅策略: " + client_id + " -> " + str(sid))
                
                elif msg_type == "ping":
                    # 心跳检测
                    await ws_manager.send_to_client(client_id, {"type": "pong"})
                
                else:
                    logger.warning("未知的消息类型: " + msg_type)
            
            except json.JSONDecodeError:
                logger.error("JSON 解析失败: " + data)
            except Exception as e:
                logger.error("处理消息异常: " + str(e))
    
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
        logger.info("WebSocket 客户端已断开连接: " + client_id)
    
    except Exception as e:
        logger.error("WebSocket 异常: " + str(e))
        ws_manager.disconnect(client_id)


@router.get("/ws/stats", tags=["websocket"])
async def get_websocket_stats():
    """获取 WebSocket 统计信息"""
    try:
        stats = ws_manager.get_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error("获取 WebSocket 统计失败: " + str(e))
        return {
            "success": False,
            "error": str(e)
        }
