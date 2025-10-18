#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : refactor_base_strategy.py
@Date       : 2025/10/18 21:02
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 重构后的策略基类
"""
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.core.constants import Interval
from src.core.object import TickData, BarData, OrderData, TradeData, OrderRequest


class BaseStrategy(ABC):
    """
    策略基类
    """
    def __init__(self) -> None:
        """
        初始化
        """
        # 策略基本信息
        self.strategy_id: str = str(uuid.uuid4())   # 策略ID
        self.strategy_name: str = ""                # 策略名称
        self.description: str = ""                  # 策略描述
        self.author: str = ""                       # 作者
        self.instruments: list[str] = []            # 订阅的合约列表，例如 ["rb2601", "ru2601"]
        # # 每个合约对应的周期枚举列表，如：{"rb2601": [Interval.MINUTE, Interval.MINUTE5], "ru2601": [Interval.MINUTE]}
        self.bar_intervals: dict[str, list[Interval]] = {}

        # 策略数据
        """
        策略当前持仓，举例：
        [
            {
                "position_id": "123456789",     # 持仓ID(作为持仓唯一标识)
                "instrument": "rb2601",         # 合约
                "direction": "long",            # 多空方向
                "available_total": "10/10",     # 可用/总仓
                "average_open_price": 450.50,   # 开仓均价
                "latest_price": 462.30,         # 最新价
                "trans_profit_loss": 1200.50,   # 逐笔浮盈
                "profit_spread": 11.80,         # 盈利价差
                "profit_ratio": 0.0267,         # 浮盈比例
                "margin": 45,050,               # 保证金
                "market_cap": 462,300,          # 市值
                "mtm_profit_loss": 1180.00,     # 盯市盈亏
                "take_profit_price": 460.00,    # 止盈价
                "stop_loss_price": 445.00       # 止损价
            },
            ...
        ]
        """
        self.positions: list[dict[str, Any]] = []
        """
        策略当前挂单，举例：
        [
            {
                "order_id": "123456789",        # 挂单ID(作为挂单唯一标识)
                "instrument": "rb2601",         # 合约
                "direction": "long",            # 多空方向
                "entrust_price": 5200.00,       # 委托价
                "entrust_volume": 25,           # 委托量
                "order_volume": 5               # 挂单量
            }
        ]
        """
        self.orders: list[dict[str, Any]] = []
        """
        策略当前委托，举例：
        [
            {
                "entrust_id": "123456789",          # 委托ID(作为委托唯一标识)
                "instrument": "au2601",             # 合约
                "state": "all_complete",            # 状态
                "direction": "long",                # 多空方向
                "open_close": "open",               # 开平
                "entrust_price": 450.50,            # 委托价
                "entrust_volume": 10,               # 委托量
                "completed": 10,                    # 已成交
                "canceled": 0,                      # 已撤单
                "cancelable": 0,                    # 可撤单
                "sold_price": 450.50,               # 成交价
                "datetime": "2025-10-08 09:15:20"   # 时间
                
            }
        ]
        """
        self.entrusts: list[dict[str, Any]] = []
        """
        策略当前成交，举例：
        [
            {
                "trade_id": "123456789",                # 成交ID(作为成交唯一标识)
                "instrument": "rb2601",                 # 合约
                "direction": "long",                    # 多空方向
                "open_close": "open",                   # 开平
                "sold_price": 450.50,                   # 成交价
                "volume": 10,                           # 成交量
                "profit_loss": 0,                       # 平仓盈亏
                "handling_fees": 22.53,                 # 手续费
                "trade_serial": "T202510080915320001",  # 成交编号
                "datetime": "2025-10-08 09:15:20"       # 时间
            }
        ]
        """
        self.trades: list[dict[str, Any]] = []
        """
        策略风控参数(策略级别风控参数)，合约级别风控参数可在风控配置文件中设置，举例：
        {
            "max_position":20,
            "stop_loss_ratio":0.02,
            "take_profit_ratio":0.03,
            "max_draw_down":0.1
        }
        """
        self.risk_control: dict[str, Any] = {}
        self.strategy_params: dict[str, Any] = {}   # 策略参数
        self.data_cache: dict[str, Any] = {}        # 任意缓存（如bar序列、信号等）

    # ---- 生命周期回调 ----
    @abstractmethod
    def on_init(self) -> None:
        """策略初始化，开盘前执行"""
        pass

    @abstractmethod
    def on_close(self) -> None:
        """策略收盘后执行"""
        pass

    # ---- 行情 & K线事件 ----
    @abstractmethod
    def on_tick(self,tick: TickData) -> None:
        """收到tick行情执行"""
        pass

    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        """收到K线数据执行"""
        pass

    # ---- 交易相关事件 ----
    @abstractmethod
    def on_order(self, order: OrderData) -> None:
        """订单状态更新执行"""
        pass

    @abstractmethod
    def on_trade(self, trade: TradeData) -> None:
        """成交回报执行"""
        pass

    # ---- 定时器回调（如1分钟执行一次） ----
    @abstractmethod
    def on_min(self, now: datetime) -> None:
        """每分钟调用一次执行"""
        pass

    @abstractmethod
    def on_alarm(self) -> None:
        """到达设置闹钟时间时执行"""
        pass

    # ---- 下单接口（由策略调用，引擎实现） ----
    def send_order(self, order_req: OrderRequest):
        """模拟下单"""
        order_req_dict = {
            "instrument_id": order_req.instrument_id,
            "exchange_id": order_req.exchange_id,
            "direction": order_req.direction,
            "order_type": order_req.order_type,
            "volume": order_req.volume,
            "price": order_req.price,
            "offset": order_req.offset
        }
        self.orders.append(order_req_dict)

    def is_subscribed(self, instrument_id: str) -> bool:
        """
        检查是否订阅了指定合约

        Args:
            instrument_id: 合约ID

        Returns:
            bool: 如果订阅了该合约返回True，否则返回False
        """
        return instrument_id in self.instruments

    def get_subscribed_instruments(self) -> list[str]:
        """
        获取订阅的合约列表

        Returns:
            list[str]: 订阅的合约ID列表
        """
        return self.instruments.copy()

    # ========== 状态持久化方法（可选实现） ==========

    def save_state(self) -> dict:
        """
        保存策略状态（可选实现）

        系统会定期调用此方法（每5分钟）保存策略状态到文件。
        在策略重载或系统重启时，保存的状态会自动恢复。

        返回一个字典，包含需要持久化的状态数据。
        如果策略不需要状态持久化，可以不实现此方法（返回None）。

        示例：
            def save_state(self):
                return {
                    "counter": self.counter,
                    "positions": self.positions,
                    "last_signal": self.last_signal
                }

        Returns:
            dict: 状态数据，必须是可序列化的（支持msgpack格式）
                 - 支持：int, float, str, list, dict, bool, None
                 - 不支持：自定义对象、函数、文件句柄等

        注意：
            - 状态数据应该精简，只保存必要的信息
            - 建议单个状态文件不超过10MB
            - 系统会自动保留24小时内的历史快照
            - 超过30天的旧状态会被自动清理
        """
        return {}

    def load_state(self, state: dict):
        """
        加载策略状态（可选实现）

        在策略启动时，如果存在持久化状态，系统会自动调用此方法恢复状态。

        参数：
            state: 上次保存的状态数据（dict类型）

        示例：
            def load_state(self, state):
                if state:
                    self.counter = state.get("counter", 0)
                    self.positions = state.get("positions", {})
                    self.last_signal = state.get("last_signal")
                    print(f"[{self.strategy_id}] 已恢复状态: counter={self.counter}")

        注意：
            - 应该提供默认值，以防某些字段不存在
            - 在恢复状态后，可以记录日志便于调试
            - 如果状态数据损坏或格式不正确，应该妥善处理异常
        """
        pass
