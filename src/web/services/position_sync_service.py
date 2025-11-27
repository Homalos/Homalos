#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : position_sync_service.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略持仓同步服务 - 使用ZeroMQ接收持仓更新并同步到数据库
"""
import asyncio
import json
import zmq
from typing import Optional, Dict, Any
from datetime import datetime

from src.web.services.strategy_position_service import StrategyPositionService
from src.web.services.websocket_manager import get_websocket_manager
from src.web.schemas.strategy_position import StrategyPositionCreate
from src.web.core.database import async_session_maker
from src.utils.log import get_logger


class PositionSyncService:
    """
    策略持仓同步服务
    
    使用 ZeroMQ PUB/SUB 模式：
    - 策略进程作为 Publisher，发布持仓更新
    - 本服务作为 Subscriber，订阅并处理持仓更新
    """

    def __init__(self, zmq_host: str = "127.0.0.1", zmq_port: int = 5555):
        """
        初始化持仓同步服务
        
        Args:
            zmq_host: ZeroMQ 连接地址（连接到策略管理器的 Publisher）
            zmq_port: ZeroMQ 连接端口
        """
        self.logger = get_logger(self.__class__.__name__)
        self.zmq_host = zmq_host
        self.zmq_port = zmq_port
        self.zmq_url = f"tcp://{zmq_host}:{zmq_port}"
        
        # ZeroMQ 上下文和套接字
        self.zmq_context: Optional[zmq.Context] = None
        self.position_sub: Optional[zmq.Socket] = None
        
        # 服务状态
        self.is_running = False
        self._listen_task: Optional[asyncio.Task] = None
        
        # 位置服务
        self.position_service = StrategyPositionService()
        
        # 统计信息
        self.stats = {
            "received": 0,
            "synced": 0,
            "failed": 0,
            "last_sync_time": None
        }

    def start(self):
        """启动 ZeroMQ Subscriber"""
        try:
            self.zmq_context = zmq.Context()
            self.position_sub = self.zmq_context.socket(zmq.SUB)
            
            # 连接到策略管理器的 Publisher
            # 注意：策略管理器在启动时会创建 Publisher，所以这里直接连接
            self.position_sub.connect(self.zmq_url)
            
            # 订阅所有持仓更新消息
            self.position_sub.setsockopt_string(zmq.SUBSCRIBE, "position_update")
            
            # 设置为非阻塞模式
            self.position_sub.setsockopt(zmq.RCVTIMEO, 100)  # 100ms 超时
            
            self.is_running = True
            self.logger.info("持仓同步服务已启动，连接到: " + self.zmq_url)
        
        except Exception as e:
            # 连接失败时记录警告但不抛出异常，允许应用继续启动
            self.logger.warning("启动持仓同步服务失败（可能策略管理器未启动）: " + str(e))
            self.is_running = False

    def stop(self):
        """停止 ZeroMQ Subscriber"""
        try:
            self.is_running = False
            
            if self.position_sub:
                self.position_sub.close()
            
            if self.zmq_context:
                self.zmq_context.term()
            
            self.logger.info("持仓同步服务已停止")
        
        except Exception as e:
            self.logger.error("停止持仓同步服务失败: " + str(e))

    async def start_listening(self):
        """
        启动异步监听循环
        
        持续监听 ZeroMQ 消息并处理持仓更新
        """
        if not self.is_running:
            self.start()
        
        self._listen_task = asyncio.create_task(self._listen_loop())
        self.logger.info("持仓同步监听循环已启动")

    async def stop_listening(self):
        """停止异步监听循环"""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        self.stop()
        self.logger.info("持仓同步监听循环已停止")

    async def _listen_loop(self):
        """
        异步监听循环
        
        持续接收 ZeroMQ 消息并处理
        """
        while self.is_running:
            try:
                # 非阻塞接收消息
                try:
                    message = self.position_sub.recv_string(zmq.NOBLOCK)
                except zmq.Again:
                    # 没有消息，短暂休眠
                    await asyncio.sleep(0.01)
                    continue
                
                # 解析消息
                self.stats["received"] += 1
                await self._process_message(message)
            
            except asyncio.CancelledError:
                self.logger.info("持仓同步监听循环被取消")
                break
            
            except Exception as e:
                self.logger.error("监听循环异常: " + str(e), exc_info=True)
                await asyncio.sleep(1)  # 异常后休眠1秒

    async def _process_message(self, message: str):
        """
        处理 ZeroMQ 消息
        
        Args:
            message: ZeroMQ 消息字符串 (格式: "topic {json_data}")
        """
        try:
            # 分离 topic 和 data
            parts = message.split(" ", 1)
            if len(parts) != 2:
                self.logger.warning("消息格式错误: " + message)
                return
            
            topic, data_str = parts
            
            # 解析 JSON 数据
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError as e:
                self.logger.error("JSON 解析失败: " + str(e))
                return
            
            # 处理持仓更新
            if topic == "position_update":
                await self._handle_position_update(data)
            else:
                self.logger.warning("未知的消息主题: " + topic)
        
        except Exception as e:
            self.logger.error("处理消息异常: " + str(e), exc_info=True)
            self.stats["failed"] += 1

    async def _handle_position_update(self, data: Dict[str, Any]):
        """
        处理持仓更新消息
        
        Args:
            data: 持仓数据字典
        """
        try:
            strategy_id = data.get("strategy_id")
            symbol = data.get("symbol")
            direction = data.get("direction")
            volume = data.get("volume")
            avg_price = data.get("avg_price")
            offset = data.get("offset", "OPEN")
            
            if not all([strategy_id, symbol, direction, volume, avg_price]):
                self.logger.warning("持仓数据不完整: " + str(data))
                return
            
            # 获取数据库会话
            async with async_session_maker() as db:
                # 判断是开仓还是平仓
                if offset in ["OPEN", "开仓"]:
                    # 开仓：创建或更新持仓
                    position_data = StrategyPositionCreate(
                        strategy_id=strategy_id,
                        symbol=symbol,
                        exchange=data.get("exchange"),
                        direction=direction,
                        volume=volume,
                        avg_price=avg_price
                    )
                    result = await self.position_service.create_or_update_position(db, position_data)
                
                else:
                    # 平仓：减少持仓
                    result = await self.position_service.close_position(
                        db,
                        strategy_id=strategy_id,
                        symbol=symbol,
                        direction=direction,
                        close_volume=volume,
                        close_price=avg_price
                    )
            
            self.stats["synced"] += 1
            self.stats["last_sync_time"] = datetime.utcnow()
            
            msg = "持仓同步成功: {} {} {} {}".format(symbol, direction, volume, avg_price)
            self.logger.info(msg)
            
            # 推送 WebSocket 消息给订阅了该策略的客户端
            try:
                ws_manager = get_websocket_manager()
                await ws_manager.broadcast_position_update(strategy_id, data)
            except Exception as e:
                self.logger.error("WebSocket 推送失败: " + str(e))
        
        except Exception as e:
            self.logger.error("处理持仓更新失败: " + str(e), exc_info=True)
            self.stats["failed"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        return {
            "is_running": self.is_running,
            "zmq_url": self.zmq_url,
            "received": self.stats["received"],
            "synced": self.stats["synced"],
            "failed": self.stats["failed"],
            "last_sync_time": self.stats["last_sync_time"].isoformat() if self.stats["last_sync_time"] else None
        }


# 全局实例
_position_sync_service: Optional[PositionSyncService] = None


def get_position_sync_service() -> PositionSyncService:
    """获取全局持仓同步服务实例"""
    global _position_sync_service
    if _position_sync_service is None:
        _position_sync_service = PositionSyncService()
    return _position_sync_service


async def start_position_sync():
    """启动全局持仓同步服务"""
    service = get_position_sync_service()
    await service.start_listening()


async def stop_position_sync():
    """停止全局持仓同步服务"""
    service = get_position_sync_service()
    await service.stop_listening()
