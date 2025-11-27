#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : websocket_manager.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: WebSocket 管理器 - 用于实时推送持仓更新
"""
import json
from typing import Dict, Set, Callable
from fastapi import WebSocket
from src.utils.log import get_logger


class WebSocketManager:
    """
    WebSocket 连接管理器
    
    管理客户端连接，支持广播和单播消息
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        # 活跃的 WebSocket 连接
        # 格式: {client_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 客户端订阅的策略
        # 格式: {client_id: {strategy_id1, strategy_id2, ...}}
        self.client_subscriptions: Dict[str, Set[int]] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """
        客户端连接
        
        Args:
            client_id: 客户端唯一标识
            websocket: WebSocket 连接
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = set()
        self.logger.info("客户端已连接: " + client_id)

    def disconnect(self, client_id: str):
        """
        客户端断开连接
        
        Args:
            client_id: 客户端唯一标识
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
        self.logger.info("客户端已断开连接: " + client_id)

    def subscribe(self, client_id: str, strategy_id: int):
        """
        客户端订阅策略
        
        Args:
            client_id: 客户端唯一标识
            strategy_id: 策略ID
        """
        if client_id not in self.client_subscriptions:
            self.client_subscriptions[client_id] = set()
        self.client_subscriptions[client_id].add(strategy_id)
        self.logger.debug("客户端订阅策略: " + client_id + " -> " + str(strategy_id))

    def unsubscribe(self, client_id: str, strategy_id: int):
        """
        客户端取消订阅策略
        
        Args:
            client_id: 客户端唯一标识
            strategy_id: 策略ID
        """
        if client_id in self.client_subscriptions:
            self.client_subscriptions[client_id].discard(strategy_id)
            self.logger.debug("客户端取消订阅策略: " + client_id + " -> " + str(strategy_id))

    async def broadcast_position_update(self, strategy_id: int, position_data: dict):
        """
        广播持仓更新消息
        
        Args:
            strategy_id: 策略ID
            position_data: 持仓数据
        """
        message = {
            "type": "position_update",
            "strategy_id": strategy_id,
            "data": position_data
        }
        
        # 发送给所有订阅了该策略的客户端
        disconnected_clients = []
        for client_id, subscriptions in self.client_subscriptions.items():
            if strategy_id in subscriptions and client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_json(message)
                except Exception as e:
                    self.logger.error("发送消息失败: " + str(e))
                    disconnected_clients.append(client_id)
        
        # 清理断开连接的客户端
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def send_to_client(self, client_id: str, message: dict):
        """
        发送消息给指定客户端
        
        Args:
            client_id: 客户端唯一标识
            message: 消息数据
        """
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
            except Exception as e:
                self.logger.error("发送消息失败: " + str(e))
                self.disconnect(client_id)

    def get_connected_count(self) -> int:
        """获取连接数"""
        return len(self.active_connections)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "connected_clients": len(self.active_connections),
            "total_subscriptions": sum(len(subs) for subs in self.client_subscriptions.values())
        }


# 全局 WebSocket 管理器实例
_websocket_manager: WebSocketManager = None


def get_websocket_manager() -> WebSocketManager:
    """获取全局 WebSocket 管理器实例"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
