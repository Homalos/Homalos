#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : websocket_notifier.py
@Date       : 2025/10/16 18:20
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: WebSocket通知器 - 推送告警到前端
"""
from typing import Dict, Any, Callable, Awaitable

from src.utils.log.logger import get_logger


class WebSocketNotifier:
    """
    WebSocket通知器
    
    功能：
    - 通过WebSocket推送告警到前端通知中心
    - 支持使用告警API的广播功能
    """
    
    def __init__(self, broadcast_func: Callable[[dict], Awaitable[None]]):
        """
        Args:
            broadcast_func: 广播函数，用于推送告警到WebSocket连接
        """
        self.logger = get_logger("WebSocketNotifier")
        self.broadcast_func = broadcast_func
    
    async def send_alarm(self, alarm_data: Dict[str, Any]):
        """
        推送告警到所有连接的前端
        
        Args:
            alarm_data: 告警数据字典
        """
        try:
            # 构建WebSocket消息数据
            ws_data = {
                "alarm_id": alarm_data.get("alarm_id"),
                "alarm_type": alarm_data.get("alarm_type"),
                "severity": alarm_data.get("alarm_type"),
                "source": alarm_data.get("source"),
                "target": alarm_data.get("target"),
                "message": alarm_data.get("message"),
                "created_at": alarm_data.get("created_at")
            }
            
            # 调用广播函数
            await self.broadcast_func(ws_data)
            self.logger.debug(f"告警已推送到WebSocket: {alarm_data['alarm_id']}")
        
        except Exception as e:
            self.logger.error(f"推送告警到WebSocket失败: {e}", exc_info=True)

