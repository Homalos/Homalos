#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : base_strategy.py
@Date       : 2025/9/10 16:44
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略基类
特点：
- 双层：管理层(BaseStrategy) + 合约层(SpecificStrategy)，BaseStrategy 管理策略元信息与全局状态（如持仓、风险参数）。
SpecificStrategy 是每个合约的策略实例，独立运行。
- 每个合约对应独立策略对象 SpecificStrategy，天然隔离
- 每个 SpecificStrategy 可自行管理多个周期（更灵活）
- 每个合约独立策略实例，状态隔离强，可独立持久化
- 完整工程体系，支持状态保存、恢复、装饰器校验、订阅控制
- 抽象层清晰，可组合不同 SpecificStrategy
- 多实例封装，每合约独立执行
优点：职责分离清晰、支持策略文件动态加载、支持分合约调度。
"""
import datetime
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Any

from src.core.constants import Interval
from src.core.object import TickData, BarData, OrderData, TradeData
from src.strategy.decorators import check_on_bar, check_on_tick


class BaseStrategy(object):
    """策略基类"""
    def __init__(self):
        # 策略基本信息
        self.strategy_id: str = str(uuid.uuid4())   # 策略ID
        self.strategy_name: str = ""                # 策略名称
        self.strategy_content: str = ""             # 策略内容介绍
        self.author: str = ""                       # 作者
        self.instruments: list[str] = []            # 订阅的合约，例如 ["rb2601", "ru2601"]
        # 每个合约对应的周期枚举列表，如：{"rb2601": [Interval.MINUTE, Interval.MINUTE5], "ru2601": [Interval.MINUTE]}
        self.bar_intervals: dict[str, list[Interval]] = {}  # 订阅K线类型
        self.specific_strategy_map: dict[str, SpecificStrategy] = {}  # 初始化策略详情数据

        # ========= 集中管理持仓和订单 =========
        self.positions: list[dict[str, Any]] = []  # 策略当前持仓
        self.orders: list[dict[str, Any]] = []  # 策略当前挂单
        self.entrusts: list[dict[str, Any]] = []  # 策略当前委托
        self.trades: list[dict[str, Any]] = []  # 策略当前成交
        # 策略风控参数(策略级别风控参数)，合约级别风控参数在合约相关配置文件中设置
        self.risk_control: dict[str, Any] = {}  # 策略风控参数
        self.strategy_params: dict[str, Any] = {}  # 策略参数
        self.data_cache: dict[str, Any] = {}  # 任意缓存（如bar序列、信号等）
        self.historical_data: dict[str, Any] = {}  # 用于存储合约的历史数据

        # 生命周期管理
        self.is_running: bool = False
        self.is_stop: bool = False

    # ---- 生命周期管理 ----
    def on_start(self) -> None:
        """策略启动时调用"""
        print(f"Strategy {self.strategy_name} started at {datetime.datetime.now()}")
        self.is_running = True

    def on_stop(self) -> None:
        """策略停止时调用"""
        print(f"Strategy {self.strategy_name} stopped at {datetime.datetime.now()}")
        self.is_running = False

    def load_historical_data(self, data: Any) -> None:
        """
        加载历史数据，模拟从文件、数据库或API中加载
        """
        instrument_id = data.get("instrument_id")
        if instrument_id not in self.historical_data:
            self.historical_data[instrument_id] = data
            print(f"Historical data loaded for {instrument_id}")

    # ---- 定时器回调（如1分钟执行一次） ----
    def one_min(self, now: datetime) -> None:
        """每分钟调用一次执行"""
        print("Executing strategy at", now)

    def is_subscribed(self, instrument_id: str) -> bool:
        """检查是否订阅了指定合约"""
        return instrument_id in self.instruments

    def get_subscribed_instruments(self) -> list[str]:
        """获取订阅的合约列表"""
        return self.instruments.copy()

    def get_position(self) -> list[dict[str, Any]]:
        """获取当前持仓"""
        return self.positions

    def update_position(self, position_data: dict) -> None:
        """添加一个新的的持仓，注意：在这里某些持仓字段的值需要根据某种算法计算出来，例如止盈价、止损价"""
        self.positions.append(position_data)

    def get_orders(self) -> list[dict[str, Any]]:
        """获取所有订单"""
        return self.orders

    def update_order(self, order_data: dict) -> None:
        """添加一个新的订单到订单跟踪中"""
        self.orders.append(order_data)

    def get_entrusts(self) -> list[dict[str, Any]]:
        """获取所有委托"""
        return self.entrusts

    def update_entrust(self, entrust_data: dict) -> None:
        """添加一个新的委托到委托跟踪中"""
        self.entrusts.append(entrust_data)

    def get_trades(self) -> list[dict[str, Any]]:
        """获取所有成交"""
        return self.trades

    def update_trade(self, trade_data: dict) -> None:
        """添加一个新的成交到成交跟踪中"""
        self.trades.append(trade_data)

    def get_risk_control(self) -> dict[str, Any]:
        """获取策略风控参数"""
        return self.risk_control

    def get_strategy_params(self) -> dict[str, Any]:
        """获取策略参数"""
        return self.strategy_params

    def get_data_cache(self) -> dict[str, Any]:
        """获取任意缓存"""
        return self.data_cache

    def send_order(self, order_data: dict):
        # 这里模拟发送到交易平台的逻辑
        instrument_id = order_data.get("instrument_id")
        direction = order_data.get("direction")
        price = order_data.get("price")
        self.update_entrust(order_data)  # 模拟更新委托
        print(f"Executed trade for {instrument_id}: {direction} contracts at {price}")
        self.update_order(order_data)   # 模拟更新订单
        self.update_position(order_data)    # 模拟更新持仓
        self.update_trade(order_data)  # 模拟更新成交历史


class SpecificStrategy(ABC):
    """策略详情基类"""
    def __init__(
            self,
            base_strategy: BaseStrategy,
            instrument_id: str,
            bar_intervals: list[Interval]
    ):
        self.base_strategy = base_strategy  # 使用传入的 BaseStrategy 对象
        self.instrument_id: str = instrument_id
        self.bar_intervals: list[Interval] = bar_intervals or {}
        self.kline_lock = None
        self.bar_data: Optional[BarData] = None

    # ---- 生命周期回调 ----
    @abstractmethod
    def on_init(self) -> None:
        """开盘前执行"""
        pass

    @abstractmethod
    def on_close(self) -> None:
        """收盘后执行"""
        pass

    # ---- 行情 & K线事件 ----
    @check_on_tick
    @abstractmethod
    def on_tick(self, tick: TickData) -> None:
        """有新的tick产生时执行"""
        pass

    @check_on_bar
    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        """有新的Bar产生时执行"""
        pass

    # ---- 交易相关事件 ----
    @abstractmethod
    def on_trade(self, trade: TradeData) -> None:
        """有订单成交时执行"""
        pass

    @abstractmethod
    def on_order(self, order: OrderData) -> None:
        """订单状态发生改变时执行"""
        pass

    @abstractmethod
    def on_alarm(self) -> None:
        """到达设置闹钟时间时执行"""
        pass
    
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
                    "prices": self.prices[-10:],  # 只保存最近10个价格
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
                    self.prices = state.get("prices", [])
                    self.positions = state.get("positions", {})
                    self.last_signal = state.get("last_signal")
                    print(f"[{self.strategy_id}] 已恢复状态: counter={self.counter}")
        
        注意：
            - 应该提供默认值，以防某些字段不存在
            - 在恢复状态后，可以记录日志便于调试
            - 如果状态数据损坏或格式不正确，应该妥善处理异常
        """
        pass

