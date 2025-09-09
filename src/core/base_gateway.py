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

    def __init__(self, event_bus: EventBus, gateway_name: str) -> None:
        self.event_bus: EventBus = event_bus
        self.gateway_name: str = gateway_name

    def on_tick(self, tick: TickData) -> None:
        """
        tick行情推送
        :param tick:
        :return:
        """
        self.event_bus.publish(Event(EventType.TICK, tick))

    def on_order(self, order: OrderData) -> None:
        """
        订单推送
        :param order:
        :return:
        """
        self.event_bus.publish(Event(EventType.ORDER, order))

    def on_position(self, position: PositionData) -> None:
        """
        持仓推送
        :param position:
        :return:
        """
        self.event_bus.publish(Event(EventType.POSITION, position))

    def on_account(self, account: AccountData) -> None:
        """
        账户推送
        :param account:
        :return:
        """
        self.event_bus.publish(Event(EventType.ACCOUNT, account))

    def on_contract(self, contract: ContractData) -> None:
        """
        合约推送
        :param contract:
        :return:
        """
        self.event_bus.publish(Event(EventType.CONTRACT, contract))

