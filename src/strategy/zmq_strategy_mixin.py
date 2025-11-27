#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : zmq_strategy_mixin.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: ZeroMQ 策略混入类 - 为策略添加持仓同步功能
"""
import json
import zmq
from typing import Optional
from src.utils.log import get_logger


class ZeroMQStrategyMixin:
    """
    ZeroMQ 策略混入类
    
    为策略添加通过 ZeroMQ 发布持仓更新的功能
    
    使用方式：
        class MyStrategy(SpecificStrategy, ZeroMQStrategyMixin):
            pass
    """

    def __init__(self, zmq_host: str = "localhost", zmq_port: int = 5555):
        """
        初始化 ZeroMQ 发布者
        
        Args:
            zmq_host: ZeroMQ 服务器地址
            zmq_port: ZeroMQ 服务器端口
        """
        self.logger = get_logger(self.__class__.__name__)
        self.zmq_host = zmq_host
        self.zmq_port = zmq_port
        self.zmq_url = f"tcp://{zmq_host}:{zmq_port}"
        
        # ZeroMQ 上下文和套接字
        self.zmq_context: Optional[zmq.Context] = None
        self.position_pub: Optional[zmq.Socket] = None
        
        # 发布统计
        self._published_count = 0

    def init_zmq_publisher(self):
        """
        初始化 ZeroMQ Publisher
        
        在策略启动时调用
        """
        try:
            self.zmq_context = zmq.Context()
            self.position_pub = self.zmq_context.socket(zmq.PUB)
            
            # 连接到持仓同步服务
            self.position_pub.connect(self.zmq_url)
            
            # 给订阅者一点时间连接
            import time
            time.sleep(0.1)
            
            self.logger.info("ZeroMQ Publisher 已初始化，连接到: " + self.zmq_url)
        
        except Exception as e:
            self.logger.error("初始化 ZeroMQ Publisher 失败: " + str(e), exc_info=True)

    def close_zmq_publisher(self):
        """
        关闭 ZeroMQ Publisher
        
        在策略停止时调用
        """
        try:
            if self.position_pub:
                self.position_pub.close()
            
            if self.zmq_context:
                self.zmq_context.term()
            
            self.logger.info("ZeroMQ Publisher 已关闭，共发布 {} 条消息".format(self._published_count))
        
        except Exception as e:
            self.logger.error("关闭 ZeroMQ Publisher 失败: " + str(e))

    def publish_position_update(
        self,
        strategy_id: str,
        symbol: str,
        direction: str,
        volume: int,
        avg_price: float,
        exchange: str = "",
        offset: str = "OPEN"
    ):
        """
        发布持仓更新消息
        
        Args:
            strategy_id: 策略ID
            symbol: 合约代码
            direction: 持仓方向 (LONG/SHORT)
            volume: 持仓数量
            avg_price: 平均价格
            exchange: 交易所代码
            offset: 操作类型 (OPEN/CLOSE)
        """
        if not self.position_pub:
            self.logger.warning("ZeroMQ Publisher 未初始化，无法发布消息")
            return
        
        try:
            # 构建消息数据
            message_data = {
                "strategy_id": strategy_id,
                "symbol": symbol,
                "direction": direction,
                "volume": volume,
                "avg_price": avg_price,
                "exchange": exchange,
                "offset": offset
            }
            
            # 序列化为 JSON
            message_json = json.dumps(message_data)
            
            # 发送消息（格式：topic + space + json_data）
            message = f"position_update {message_json}"
            self.position_pub.send_string(message)
            
            self._published_count += 1
            
            self.logger.debug("发布持仓更新: {} {} {} {}".format(
                symbol, direction, volume, avg_price
            ))
        
        except Exception as e:
            self.logger.error("发布持仓更新失败: " + str(e), exc_info=True)

    def get_published_count(self) -> int:
        """获取已发布的消息数"""
        return self._published_count
