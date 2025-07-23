#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : order_manager
@Date       : 2025/7/23 00:21
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 订单管理器
"""
import asyncio
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType, create_trading_event
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.core.object import OrderRequest, OrderData, TradeData, Status, OrderInfo

logger = get_logger("OrderManager")


class OrderManager:

    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config

        self.orders: Dict[str, OrderInfo] = {}
        self.strategy_orders: Dict[str, set] = defaultdict(set)  # strategy_id -> order_ids
        # 添加订单ID映射：系统订单ID -> CTP订单ID
        self.system_to_ctp_orderid: Dict[str, str] = {}
        self.ctp_to_system_orderid: Dict[str, str] = {}

        # 注册事件处理器
        self.event_bus.subscribe(EventType.RISK_APPROVED, self._handle_risk_approved)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_order_filled)
        self.event_bus.subscribe(EventType.ORDER_CANCELLED, self._handle_order_cancelled)
        self.event_bus.subscribe("order.place", self._handle_order_request)
        self.event_bus.subscribe("order.cancel", self._handle_cancel_order)

        # 订阅CTP网关回报事件
        self.event_bus.subscribe(EventType.ORDER, self._handle_ctp_order_update)
        self.event_bus.subscribe(EventType.TRADE, self._handle_ctp_trade_update)
        self.event_bus.subscribe("order.sent_to_ctp", self._handle_order_sent_to_ctp)
        self.event_bus.subscribe("order.send_failed", self._handle_order_send_failed)

    async def place_order(self, order_request: OrderRequest, strategy_id: str) -> str:
        """下单"""
        order_id = str(uuid.uuid4())
        current_time = time.time()

        # 创建订单数据
        order_data = order_request.create_order_data(order_id, "TradingEngine")

        # 创建订单信息
        order_info = OrderInfo(
            order_data=order_data,
            strategy_id=strategy_id,
            create_time=current_time,
            update_time=current_time
        )

        self.orders[order_id] = order_info
        self.strategy_orders[strategy_id].add(order_id)

        # 发布下单事件（将由网关处理）
        self.event_bus.publish(create_trading_event(
            EventType.GATEWAY_SEND_ORDER,
            {
                "order_request": order_request,
                "order_data": order_data
            },
            "OrderManager"
        ))

        # 发布订单提交事件（供监控器监听）
        self.event_bus.publish(Event(EventType.ORDER_SUBMITTED, order_data))

        logger.info(f"订单已提交: {order_id} ({strategy_id})")
        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if order_id not in self.orders:
            logger.error(f"订单不存在: {order_id}")
            return False

        order_info = self.orders[order_id]

        # 创建撤单请求
        cancel_request = order_info.order_data.create_cancel_request()

        # 发布撤单事件
        self.event_bus.publish(create_trading_event(
            EventType.GATEWAY_CANCEL_ORDER,
            {"cancel_request": cancel_request},
            "OrderManager"
        ))

        logger.info(f"撤单请求已发送: {order_id}")
        return True

    def _handle_risk_approved(self, event: Event):
        """处理风控通过事件"""
        data = event.data
        order_request = data["order_request"]
        strategy_id = data["strategy_id"]

        # 创建订单
        asyncio.create_task(self.place_order(order_request, strategy_id))

    @staticmethod
    def _handle_order_filled(event: Event):
        """处理订单成交事件"""
        trade_data = event.data
        if isinstance(trade_data, TradeData):
            logger.info(f"订单成交: {trade_data.orderid} - {trade_data.volume}@{trade_data.price}")

    @staticmethod
    def _handle_order_cancelled(event: Event):
        """处理订单撤销事件"""
        order_data = event.data
        if isinstance(order_data, OrderData):
            logger.info(f"订单已撤销: {order_data.orderid}")

    def _handle_order_request(self, event: Event):
        """处理下单请求"""
        data = event.data
        order_request = data.get("order_request")
        strategy_id = data.get("strategy_id")

        if not order_request or not strategy_id:
            logger.error("下单请求数据不完整")
            return

        # 生成订单ID
        order_id = f"{strategy_id}_{int(time.time() * 1000)}"

        # 创建订单数据
        order_data = order_request.create_order_data(order_id, "CTP_TD")
        order_data.datetime = datetime.now()

        # 存储订单信息
        order_info = OrderInfo(
            order_data=order_data,
            strategy_id=strategy_id,
            create_time=time.time(),
            update_time=time.time()
        )
        self.orders[order_id] = order_info
        self.strategy_orders[strategy_id].add(order_id)

        # 发布订单提交事件
        self.event_bus.publish(Event(EventType.ORDER_SUBMITTED, order_data))

        # 转发到CTP网关进行真实下单
        self.event_bus.publish(create_trading_event(
            EventType.GATEWAY_SEND_ORDER,
            {
                "order_request": order_request,
                "order_data": order_data
            },
            "OrderManager"
        ))

        logger.info(
            f"转发下单请求到CTP网关: {order_id} {order_request.symbol} {order_request.direction.value if order_request.direction else 'UNKNOWN'} {order_request.volume}@{order_request.price}")

    def _handle_cancel_order(self, event: Event):
        """处理撤单请求"""
        order_id = event.data["order_id"]
        asyncio.create_task(self.cancel_order(order_id))

    def get_strategy_orders(self, strategy_id: str) -> List[Dict[str, Any]]:
        """获取策略的所有订单"""
        order_ids = self.strategy_orders.get(strategy_id, set())
        return [
            {
                "order_id": order_id,
                "order_data": self.orders[order_id].order_data.__dict__,
                "create_time": self.orders[order_id].create_time,
                "update_time": self.orders[order_id].update_time
            }
            for order_id in order_ids if order_id in self.orders
        ]

    def _handle_ctp_order_update(self, event: Event):
        """处理CTP订单状态更新"""
        order_data = event.data
        if isinstance(order_data, OrderData):
            # 通过CTP订单ID找到系统订单ID
            ctp_order_id = order_data.orderid
            system_order_id = self.ctp_to_system_orderid.get(ctp_order_id)

            if system_order_id and system_order_id in self.orders:
                # 更新系统中的订单信息
                order_info = self.orders[system_order_id]
                order_info.order_data.status = order_data.status
                order_info.order_data.traded = order_data.traded
                order_info.update_time = time.time()

                logger.info(f"订单状态更新: {system_order_id} -> {order_data.status.value}")

                # 转发给策略
                self.event_bus.publish(Event(EventType.ORDER_UPDATED, order_info.order_data))
            else:
                # 可能是其他来源的订单，记录日志
                logger.debug(f"收到未知CTP订单更新: {ctp_order_id}")

    def _handle_ctp_trade_update(self, event: Event):
        """处理CTP成交回报"""
        trade_data = event.data
        if isinstance(trade_data, TradeData):
            # 通过CTP订单ID找到系统订单ID
            ctp_order_id = trade_data.orderid
            system_order_id = self.ctp_to_system_orderid.get(ctp_order_id)

            if system_order_id and system_order_id in self.orders:
                order_info = self.orders[system_order_id]

                logger.info(f"订单成交: {system_order_id} - {trade_data.volume}@{trade_data.price}")

                # 发布成交事件给AccountManager和策略
                self.event_bus.publish(Event(EventType.ORDER_FILLED, trade_data))

                # 更新订单状态
                if order_info.order_data.traded >= order_info.order_data.volume:
                    order_info.order_data.status = Status.ALL_TRADED
                else:
                    order_info.order_data.status = Status.PART_TRADED

                order_info.update_time = time.time()

                # 通知策略
                self.event_bus.publish(Event(EventType.ORDER_UPDATED, order_info.order_data))
            else:
                logger.debug(f"收到未知CTP成交回报: {ctp_order_id}")

    def _handle_order_sent_to_ctp(self, event: Event):
        """处理订单已发送到CTP的确认"""
        data = event.data
        ctp_order_id = data.get("order_id")
        order_data = data.get("order_data")

        if ctp_order_id and order_data:
            system_order_id = order_data.orderid

            # 建立订单ID映射
            self.system_to_ctp_orderid[system_order_id] = ctp_order_id
            self.ctp_to_system_orderid[ctp_order_id] = system_order_id

            # 更新订单状态为已提交
            if system_order_id in self.orders:
                self.orders[system_order_id].order_data.status = Status.SUBMITTING
                self.orders[system_order_id].update_time = time.time()

            logger.info(f"订单已发送到CTP: {system_order_id} -> {ctp_order_id}")

    def _handle_order_send_failed(self, event: Event):
        """处理订单发送失败"""
        data = event.data
        order_data = data.get("order_data")
        reason = data.get("reason", "未知原因")

        if order_data:
            system_order_id = order_data.orderid

            # 更新订单状态为被拒绝
            if system_order_id in self.orders:
                self.orders[system_order_id].order_data.status = Status.REJECTED
                self.orders[system_order_id].update_time = time.time()

                # 通知策略
                self.event_bus.publish(Event(EventType.ORDER_UPDATED, self.orders[system_order_id].order_data))

            logger.error(f"订单发送失败: {system_order_id} - {reason}")
