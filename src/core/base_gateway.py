#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : base_gateway.py
@Date       : 2025/9/9 16:11
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 抽象网关类用于外部系统连接。
每个网关都应该继承这个类，
并且应该有一个唯一的网关名称。
"""
from abc import ABC

from src.core.event import EventType, Event
from src.core.event_bus import EventBus
from src.core.object import TickData, OrderData, PositionData, AccountData, ContractData


class BaseGateway(ABC):

    def __init__(self, event_bus: EventBus, gateway_name: str = "BaseGateway") -> None:
        self.event_bus: EventBus = event_bus
        self.gateway_name: str = gateway_name
        # 直接回调机制，绕过事件总线处理高频tick
        self.tick_callback = None

    def set_tick_callback(self, callback):
        """设置tick直接回调函数"""
        self.tick_callback = callback

    def on_tick(self, tick: TickData) -> None:
        """
        tick行情推送 - 使用事件总线作为主要机制
        :param tick:
        :return:
        """
        # 主要机制：使用事件总线确保数据完整性
        self.event_bus.publish(Event(EventType.TICK, {"code": 0, "data": tick}))

    def on_order(self, order: OrderData) -> None:
        """
        订单推送
        :param order:
        :return:
        """
        self.event_bus.publish(Event(EventType.ORDER, {"code": 0, "data": order}))

    def on_position(self, position: PositionData) -> None:
        """
        持仓推送
        :param position:
        :return:
        """
        self.event_bus.publish(Event(EventType.POSITION, {"code": 0, "data": position}))

    def on_account(self, account: AccountData) -> None:
        """
        账户推送
        :param account:
        :return:
        """
        self.event_bus.publish(Event(EventType.ACCOUNT, {"code": 0, "data": account}))

    def on_contract(self, contract: ContractData) -> None:
        """
        合约推送
        :param contract:
        :return:
        """
        self.event_bus.publish(Event(EventType.CONTRACT, {"code": 0, "data": contract}))
