#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : event.py
@Date       : 2025/9/8 09:54
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件类, 封装事件数据
"""
import uuid
from typing import Any

from src.core.constants import SubscribeAction, RspCode
from src.core.pack_payload import PackPayload


class Event(object):
    """
    事件类，封装事件数据。
    Attributes:
        event_type (str): 事件类型。
        payload (Any): 事件数据。
        source (str): 事件来源，如果没有提供来源，则默认为"unknown"
        trace_id (str): 事件追踪ID，如果没有提供追踪ID，则生成一个新的UUID。
    """
    def __init__(
            self,
            event_type: str,
            payload: dict[str, Any] | None = None,
            source: str | None = None,
            trace_id: str | None = None
    ):
        self.event_type: str = event_type                   # 事件类型
        """
        payload 数据结构：
        {
            "code": code,                           # 返回码
            "message": message,                     # 信息
            "data": data,                           # 事件数据
            "timestamp": int(time.time() * 1000)    # 时间戳
        }
        """
        self.payload: dict[str, Any] | None = payload       # 事件相关数据
        self.source: str = source or "unknown"              # 事件来源，如果没有提供来源，则默认为"unknown"
        self.trace_id: str = trace_id or str(uuid.uuid4())  # 事件追踪ID，如果没有提供追踪ID，则生成一个新的UUID

    def __repr__(self) -> str:
        """
        返回事件对象的字符串表示形式。
        Args:
            无。
        Returns:
            str: 事件对象的字符串表示形式，包含事件类型、事件源和追踪ID。
        """
        return f"Event(event_type={self.event_type}, source={self.source}, trace_id={self.trace_id})"

    @classmethod
    def create(cls, event_type: str, payload: dict[str, Any] | None = None,
               source: str = "unknown") -> "Event":
        """
        通用事件创建方法

        Args:
            event_type (str): 事件类型
            payload (dict[str, Any] | None): 事件数据，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: 事件对象
        """
        return cls(event_type=event_type, payload=payload, source=source)

    @classmethod
    def tick(cls, payload: dict[str, Any] | None = None, source: str = "unknown") -> "Event":
        """
        创建 Tick 事件

        Args:
            payload (dict[str, Any] | None): 事件数据，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: Tick 事件对象
        """
        return cls.create(EventType.TICK, payload, source)

    @classmethod
    def bar(cls, payload: dict[str, Any] | None = None, source: str = "unknown") -> "Event":
        """
        创建 K线事件

        Args:
            payload (dict[str, Any] | None): K线数据，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: K线事件对象
        """
        return cls.create(EventType.BAR, payload, source)

    @classmethod
    def order(cls, payload: dict[str, Any] | None = None, source: str = "unknown") -> "Event":
        """
        创建订单事件

        Args:
            payload (dict[str, Any] | None): 订单数据，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: 订单事件对象
        """
        return cls.create(EventType.ORDER, payload, source)

    @classmethod
    def position(cls, payload: dict[str, Any] | None = None, source: str = "unknown") -> "Event":
        """
        创建持仓事件

        Args:
            payload (dict[str, Any] | None): 持仓数据，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: 持仓事件对象
        """
        return cls.create(EventType.POSITION, payload, source)

    @classmethod
    def account(cls, payload: dict[str, Any] | None = None, source: str = "unknown") -> "Event":
        """
        创建账户事件

        Args:
            payload (dict[str, Any] | None): 账户数据，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: 账户事件对象
        """
        return cls.create(EventType.ACCOUNT, payload, source)

    @classmethod
    def contract(cls, payload: dict[str, Any] | None = None, source: str = "unknown") -> "Event":
        """
        创建合约事件

        Args:
            payload (dict[str, Any] | None): 合约数据，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: 合约事件对象
        """
        return cls.create(EventType.CONTRACT, payload, source)

    @classmethod
    def timer(cls, payload: dict[str, Any] | None = None, source: str = "unknown") -> "Event":
        """
        创建定时器事件

        Args:
            payload (dict[str, Any] | None): 定时器间隔等数据，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: 定时器事件对象
        """
        return cls.create(EventType.TIMER, payload, source)

    @classmethod
    def alarm(cls, payload: dict[str, Any] | None = None, source: str = "unknown") -> "Event":
        """
        创建系统告警事件

        Args:
            payload (dict[str, Any] | None): 告警数据，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: 系统告警事件对象
        """
        return cls.create(EventType.SYSTEM_ALARM, payload, source)

    @classmethod
    def subscription(cls, code: RspCode = RspCode.SUCCESS, message: str = "success",
                    instruments: list[str] | None = None, action: SubscribeAction | None = None,
                    source: str = "unknown") -> "Event":
        """
        创建订阅事件

        Args:
            code (RspCode): 返回码，默认为 RspCode.SUCCESS
            message (str): 订阅请求信息，默认为 "success"
            instruments (list[str] | None): 订阅合约列表，默认为 None
            action (SubscribeAction | None): 订阅操作，枚举类型，默认为 None
            source (str): 事件来源，默认为 "unknown"

        Returns:
            Event: 订阅事件对象
        """
        data = {
            "instruments": instruments,
            "action": action.value if action else None
        }
        payload = (
            PackPayload.success(message=message, data=data)
            if code == RspCode.SUCCESS
            else PackPayload.fail(code=code, message=message, data=data)
        )
        return cls.create(EventType.MARKET_SUBSCRIBE_REQUEST, payload, source)


class EventType(object):
    """事件类型常量"""
    EVENT_BUS_SHUTDOWN = "event_bus.shutdown"  # event_bus停止事件

    TIMER = "timer"  # 定时器事件

    # ===== 行情数据事件 =====
    TICK = "market.tick"  # Tick事件
    BAR = "market.bar"  # K线事件
    
    # ===== 基础业务事件 =====
    ORDER = "order"  # 订单事件
    POSITION = "position"  # 持仓事件
    ACCOUNT = "account"  # 账户事件
    CONTRACT = "contract"  # 合约事件

    # ===== 网关连接事件 =====
    MD_GATEWAY_CONNECT = "md_gateway.connect"  # 行情接口连接事件(成功/断开)
    MD_GATEWAY_LOGIN = "md_gateway.login"  # 行情登录
    TD_GATEWAY_LOGIN = "td_gateway.login"  # 交易登录
    TD_QRY_INS = "td.qry.ins"  # 交易网关查询合约事件
    TD_CONFIRM_SUCCESS = "td.confirm.success"  # 结算单确认成功(也代表交易网关就绪)
    TD_ALREADY_CONFIRMED = "td.already.confirmed"  # 结算单已经确认过事件(也代表交易网关就绪)

    # ===== 数据中心事件 =====
    DATA_CENTER_START = "data_center.start"  # 数据中心启动事件
    DATA_CENTER_STOP = "data_center.stop"  # 数据中心停止事件
    DATA_CENTER_QRY_INS = "data_center.qry_ins"  # 数据中心查询合约事件

    # ===== 策略管理事件 =====
    STRATEGY_LOADED = "strategy.loaded"  # 策略加载完成
    STRATEGY_UNLOADED = "strategy.unloaded"  # 策略卸载完成
    STRATEGY_SUBSCRIPTION_UPDATE = "strategy.subscription.update"  # 策略订阅信息更新
    STRATEGY_TRADE_SIGNAL = "strategy.trade.signal"  # 策略交易信号
    STRATEGY_SIGNAL_RESULT = "strategy.signal.result"  # 策略信号执行结果通知

    # ===== 订阅管理事件 =====
    MARKET_SUBSCRIBE_REQUEST = "market.subscribe.request"  # 行情订阅请求
    KLINE_CONFIG_UPDATE = "kline.config.update"  # K线配置更新

    # ===== 交易信号流事件 =====
    TRADE_SIGNAL = "trade.signal"  # 交易信号（发送给风控）
    TRADE_ORDER_APPROVED = "trade.order.approved"  # 订单风控通过
    TRADE_ORDER_REJECTED = "trade.order.rejected"  # 订单风控拒绝

    # ===== 订单执行事件 =====
    ORDER_SUBMIT_REQUEST = "order.submit.request"  # 订单提交请求
    ORDER_CANCEL_REQUEST = "order.cancel.request"  # 订单撤销请求
    ORDER_STATUS_UPDATE = "order.status.update"  # 订单状态更新
    TRADE_EXECUTION = "trade.execution"  # 成交回报

    # ===== 持仓和资金事件 =====
    POSITION_UPDATE = "position.update"  # 持仓更新
    ACCOUNT_UPDATE = "account.update"  # 账户资金更新

    # ===== 风险管理事件 =====
    RISK_ALARM = "risk.alarm"  # 风险告警

    # ===== 系统告警事件 =====
    SYSTEM_ALARM = "system.alarm"  # 系统告警
    PROCESS_ALARM = "process.alarm"  # 进程告警

    # ===== 配置更新事件 =====
    CONFIG_UPDATE = "config.update"  # 配置更新事件
