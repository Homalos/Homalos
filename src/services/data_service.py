#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : data_service
@Date       : 2025/7/6 21:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据服务 - 整合行情
"""
import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Optional, Any, Set

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType, create_market_event, create_trading_event
from src.core.event_bus import EventBus as EventBus
from src.core.logger import get_logger
from src.core.object import TickData, BarData
from src.function.bar_manager import BarManager


logger = get_logger("DataService")


class DataService:
    """数据服务 - 整合行情"""
    
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        
        # 数据中心连接（通过事件总线通信）
        self.data_center_available = False
        
        # 行情数据缓存
        self.tick_buffer: Dict[str, TickData] = {}
        self.bar_buffer: Dict[str, Dict[str, BarData]] = defaultdict(dict)  # symbol -> interval -> bar
        
        # 订阅管理
        self.subscribers: Dict[str, Set[str]] = defaultdict(set)  # symbol -> set(strategy_ids)
        self.strategy_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # strategy_id -> symbols
        
        # 订阅状态跟踪
        self.subscription_states: Dict[str, Dict] = {}
        
        # 配置参数
        self.buffer_size = config.get("data.market.buffer_size", 1000)
        self.enable_data_center = config.get("data.market.enable_data_center", True)
        
        # K线合成管理
        self.bar_manager = BarManager([1, 5, 10])  # 支持1m/5m/10m
        
        # 性能统计
        self.stats: Dict[str, Any] = {
            "tick_count": 0,
            "bar_count": 0,
            "last_tick_time": 0,
            "processing_rate": 0
        }
        
        # 注册事件处理器
        self._setup_event_handlers()
        self._setup_data_event_handlers()
        
        logger.info("数据服务初始化完成")
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        # 行情数据处理
        self.event_bus.subscribe(EventType.MARKET_TICK_RAW, self._handle_raw_tick)
        self.event_bus.subscribe(EventType.MARKET_BAR_RAW, self._handle_raw_bar)
        
        # 订阅管理
        self.event_bus.subscribe(EventType.DATA_SUBSCRIBE, self._handle_data_subscribe)
        self.event_bus.subscribe(EventType.DATA_UNSUBSCRIBE, self._handle_data_unsubscribe)
        
        # 数据查询
        self.event_bus.subscribe(EventType.DATA_QUERY_TICK, self._handle_query_tick)
        self.event_bus.subscribe(EventType.DATA_QUERY_BAR, self._handle_query_bar)
        
    async def initialize(self):
        """初始化数据服务"""
        try:
            # 检查数据中心连接
            if self.enable_data_center:
                self._check_data_center_connection()
            
            logger.info("数据服务初始化成功")
            return True
        except Exception as e:
            logger.error(f"数据服务初始化失败: {e}")
            return False

    @staticmethod
    async def shutdown():
        """关闭数据服务"""
        try:
            logger.info("数据服务已关闭")
        except Exception as e:
            logger.error(f"数据服务关闭失败: {e}")
    
    def subscribe_market_data(self, symbols: List[str], strategy_id: str) -> bool:
        """
        订阅行情数据 - 增强状态管理
        
        Args:
            symbols: 合约代码列表
            strategy_id: 策略ID
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            logger.info(f"策略 {strategy_id} 订阅行情: {symbols}")
            
            # 记录订阅关系
            for symbol in symbols:
                if symbol not in self.subscribers:
                    self.subscribers[symbol] = set()
                self.subscribers[symbol].add(strategy_id)
                
                # 记录到订阅状态表
                self._record_subscription_state(symbol, strategy_id, "requested")
            
            # 发布网关订阅事件
            if self.event_bus:
                gateway_event = create_trading_event(
                    EventType.GATEWAY_SUBSCRIBE,
                    {
                        "symbols": symbols,
                        "strategy_id": strategy_id
                    },
                    source="DataService"
                )
                
                self.event_bus.publish(gateway_event)
                logger.debug(f"已发布网关订阅事件: {symbols}")
                
                # 设置订阅超时检查
                asyncio.create_task(self._check_subscription_timeout(symbols, strategy_id))
                
            return True
            
        except Exception as e:
            logger.error(f"订阅行情失败: {e}")
            return False

    def _record_subscription_state(self, symbol: str, strategy_id: str, state: str) -> None:
        """记录订阅状态"""
        try:
            if not hasattr(self, 'subscription_states'):
                self.subscription_states = {}
            
            key = f"{symbol}_{strategy_id}"
            self.subscription_states[key] = {
                "symbol": symbol,
                "strategy_id": strategy_id,
                "state": state,
                "timestamp": time.time(),
                "retry_count": 0
            }
            
            logger.debug(f"记录订阅状态: {key} -> {state}")
            
        except Exception as e:
            logger.error(f"记录订阅状态失败: {e}")

    async def _check_subscription_timeout(self, symbols: List[str], strategy_id: str) -> None:
        """检查订阅超时 - 增强版本，支持交易时间判断"""
        try:
            await asyncio.sleep(10)  # 等待10秒
            
            # 检查是否为交易时间
            is_trading_time = self._is_trading_hours()
            
            for symbol in symbols:
                key = f"{symbol}_{strategy_id}"
                if hasattr(self, 'subscription_states') and key in self.subscription_states:
                    state_info = self.subscription_states[key]
                    
                    if state_info["state"] == "requested":
                        # 根据交易时间调整超时处理策略
                        if is_trading_time:
                            logger.warning(f"交易时间订阅超时: {symbol} (策略: {strategy_id}) - 可能存在行情数据问题")
                        else:
                            logger.info(f"非交易时间订阅超时: {symbol} (策略: {strategy_id}) - 属于正常现象")
                        
                        # 标记为超时并重试
                        state_info["state"] = "timeout"
                        state_info["retry_count"] += 1
                        state_info["is_trading_time"] = is_trading_time
                        
                        # 只在交易时间或重试次数较少时进行重试
                        if (is_trading_time and state_info["retry_count"] < 5) or (not is_trading_time and state_info["retry_count"] < 2):
                            logger.info(f"重试订阅: {symbol} (第{state_info['retry_count']}次, 交易时间={is_trading_time})")
                            self._retry_subscription(symbol, strategy_id)
                        else:
                            logger.error(f"订阅重试次数超限: {symbol} (交易时间={is_trading_time})")
                            state_info["state"] = "failed"
                            
        except Exception as e:
            logger.error(f"检查订阅超时失败: {e}")

    @staticmethod
    def _is_trading_hours() -> bool:
        """判断当前是否为交易时间"""
        try:
            import datetime
            now = datetime.datetime.now()
            hour = now.hour
            minute = now.minute
            weekday = now.weekday()  # 0=Monday, 6=Sunday
            
            # 检查是否为工作日（周一到周五）
            if weekday >= 5:  # 周六、周日
                return False
            
            # 期货交易时间段
            # 日盘：9:00-11:30, 13:30-15:00
            # 夜盘：21:00-次日2:30（部分品种到1:00或23:30）
            
            # 日盘时间
            morning_session = (9 <= hour < 11) or (hour == 11 and minute <= 30)
            afternoon_session = (13 <= hour < 15) or (hour == 13 and minute >= 30)
            
            # 夜盘时间（简化处理，大部分品种到2:30）
            night_session = (21 <= hour <= 23) or (0 <= hour <= 2) or (hour == 2 and minute <= 30)
            
            is_trading = morning_session or afternoon_session or night_session
            
            # 特别记录FG509相关的交易时间判断
            if hour in [9, 13, 21, 2]:  # 关键时间点
                logger.debug(f"交易时间判断: {now.strftime('%H:%M')} 工作日={weekday < 5} 交易时间={is_trading}")
            
            return is_trading
            
        except Exception as e:
            logger.error(f"判断交易时间失败: {e}")
            return True  # 出错时默认认为是交易时间，避免误判

    def _retry_subscription(self, symbol: str, strategy_id: str) -> None:
        """重试订阅"""
        try:
            logger.info(f"重试订阅: {symbol} (策略: {strategy_id})")
            
            # 重新发布订阅事件
            if self.event_bus:
                gateway_event = create_trading_event(
                    EventType.GATEWAY_SUBSCRIBE,
                    {
                        "symbols": [symbol],
                        "strategy_id": strategy_id
                    },
                    source="DataService"
                )
                
                self.event_bus.publish(gateway_event)
                
                # 更新状态
                self._record_subscription_state(symbol, strategy_id, "retry")
                
        except Exception as e:
            logger.error(f"重试订阅失败: {e}")

    def on_subscription_success(self, symbol: str, strategy_id: str) -> None:
        """订阅成功回调"""
        try:
            logger.info(f"订阅成功确认: {symbol} (策略: {strategy_id})")
            self._record_subscription_state(symbol, strategy_id, "active")
            
        except Exception as e:
            logger.error(f"处理订阅成功回调失败: {e}")

    def get_subscription_status(self) -> Dict[str, Dict]:
        """获取订阅状态"""
        try:
            if hasattr(self, 'subscription_states'):
                return dict(self.subscription_states)
            return {}
            
        except Exception as e:
            logger.error(f"获取订阅状态失败: {e}")
            return {}
    
    def _handle_raw_tick(self, event: Event):
        """处理原始tick数据，分发给订阅的策略"""
        tick_data = event.data
        if not isinstance(tick_data, TickData):
            return
        
        try:
            logger.debug(f"DataService收到tick: {tick_data.symbol} {tick_data.datetime} {tick_data.last_price}")
            # 更新统计
            self.stats["tick_count"] += 1
            self.stats["last_tick_time"] = time.time()
            
            # 定期输出数据流统计 (每100个tick输出一次)
            if self.stats["tick_count"] % 100 == 0:
                logger.info(f"数据流统计: 已处理{self.stats['tick_count']}个tick, "
                            f"当前合约={tick_data.symbol}, "
                            f"订阅策略数={len(self.subscribers.get(tick_data.symbol, set()))}")
            
            # 更新内存缓存
            symbol = tick_data.symbol
            self.tick_buffer[symbol] = tick_data
            
            # 分发给订阅的策略 - 发布策略专用事件
            subscriber_count = 0
            for strategy_id in self.subscribers.get(symbol, set()):
                # 发布策略专用事件：market.tick.{strategy_id}
                self.event_bus.publish(create_market_event(
                    f"{EventType.MARKET_TICK}.{strategy_id}",
                    tick_data,
                    "DataService"
                ))
                logger.debug(f"为策略 {strategy_id} 发布tick事件: {symbol}")
                subscriber_count += 1

            # 输出分发统计
            if subscriber_count > 0:
                logger.info(f"Tick分发: {symbol} @ {tick_data.last_price} → {subscriber_count}个策略")
            else:
                logger.debug(f"无订阅策略: {symbol} tick数据未分发")

            # 同时保持通用事件的发布，用于全局监听器
            self.event_bus.publish(create_market_event(
                EventType.MARKET_TICK,
                tick_data,
                "DataService"
            ))
            
            # # 如果启用数据中心，发送数据到数据中心
            # if self.enable_data_center and self.data_center_available:
            #     self._send_tick_to_data_center(tick_data)
                
            # K线合成
            bars = self.bar_manager.on_tick(tick_data)
            for bar in bars:
                logger.info(f"分发MARKET_BAR: {bar.symbol} {bar.datetime} O:{bar.open_price} H:{bar.high_price} L:{bar.low_price} C:{bar.close_price}")
                self.event_bus.publish(Event(EventType.MARKET_BAR, bar))
                
        except Exception as e:
            logger.error(f"处理tick数据失败: {e}")
    
    def _handle_raw_bar(self, event: Event):
        """处理原始bar数据，分发给订阅的策略"""
        bar_data = event.data
        if not isinstance(bar_data, BarData):
            return
        
        try:
            # 更新统计
            self.stats["bar_count"] += 1
            
            # 更新内存缓存
            symbol = bar_data.symbol
            interval = bar_data.interval.value if bar_data.interval else '1m'
            self.bar_buffer[symbol][interval] = bar_data
            
            # 分发给订阅的策略 - 发布策略专用事件
            for strategy_id in self.subscribers.get(symbol, set()):
                # 发布策略专用事件：market.bar.{strategy_id}
                self.event_bus.publish(create_market_event(
                    f"{EventType.MARKET_BAR}.{strategy_id}",
                    bar_data,
                    "DataService"
                ))
                logger.debug(f"为策略 {strategy_id} 发布bar事件: {symbol}")

                # 同时保持通用事件的发布
                self.event_bus.publish(create_market_event(
                    EventType.MARKET_BAR,
                    bar_data,
                    "DataService"
                ))
            
            # # 如果启用数据中心，发送数据到数据中心
            # if self.enable_data_center and self.data_center_available:
            #     self._send_bar_to_data_center(bar_data)
                
        except Exception as e:
            logger.error(f"处理bar数据失败: {e}")
    
    def _handle_data_subscribe(self, event: Event):
        """处理订阅请求 - 增强版本"""
        try:
            data = event.data
            symbols = data.get("symbols", [])
            strategy_id = data.get("strategy_id", "unknown")

            # 暂时忽略空合约订阅请求，后期可优化到全合约订阅
            if not symbols:
                logger.warning(f"收到空的订阅请求: {strategy_id}")
                return
            
            logger.info(f"处理数据订阅请求: 策略={strategy_id}, 合约={symbols}")
            
            # 调用增强的订阅方法
            success = self.subscribe_market_data(symbols, strategy_id)
            
            if success:
                logger.info(f"订阅处理成功: 策略={strategy_id}, 合约={symbols}")
                
                # 发布订阅成功事件
                if self.event_bus:
                    from src.core.event import create_trading_event

                    success_event = create_trading_event(
                        EventType.DATA_SUBSCRIBE_SUCCESS,
                        {
                            "symbols": symbols,
                            "strategy_id": strategy_id,
                            "timestamp": time.time()
                        },
                        source="DataService"
                    )
                    
                    self.event_bus.publish(success_event)
            else:
                logger.error(f"订阅处理失败: 策略={strategy_id}, 合约={symbols}")
                
                # 发布订阅失败事件
                if self.event_bus:
                    from src.core.event import create_trading_event
                    
                    failure_event = create_trading_event(
                        EventType.DATA_SUBSCRIBE_FAILED,
                        {
                            "symbols": symbols,
                            "strategy_id": strategy_id,
                            "timestamp": time.time(),
                            "reason": "订阅处理失败"
                        },
                        source="DataService"
                    )
                    
                    self.event_bus.publish(failure_event)
                    
        except Exception as e:
            logger.error(f"处理订阅请求失败: {e}")

    async def unsubscribe_market_data(self, symbols: List[str], strategy_id: str):
        """取消订阅行情数据 - 增强版本"""
        try:
            for symbol in symbols:
                self.subscribers[symbol].discard(strategy_id)
                self.strategy_subscriptions[strategy_id].discard(symbol)
                
                # 更新订阅状态
                key = f"{symbol}_{strategy_id}"
                if hasattr(self, 'subscription_states') and key in self.subscription_states:
                    self.subscription_states[key]["state"] = "unsubscribed"
                    self.subscription_states[key]["timestamp"] = time.time()
            
            # 发布取消订阅事件到网关
            if self.event_bus:
                gateway_event = create_trading_event(
                    EventType.GATEWAY_UNSUBSCRIBE,
                    {
                        "symbols": symbols,
                        "strategy_id": strategy_id
                    },
                    source="DataService"
                )
                
                self.event_bus.publish(gateway_event)
            
            logger.info(f"策略 {strategy_id} 取消订阅行情: {symbols}")
            
        except Exception as e:
            logger.error(f"取消订阅失败: {e}")

    def _handle_gateway_subscription_success(self, event: Event):
        """处理网关订阅成功事件"""
        try:
            data = event.data
            symbol = data.get("symbol")
            strategy_id = data.get("strategy_id")
            
            logger.info(f"DataService收到网关订阅成功事件: symbol={symbol}, strategy_id={strategy_id}")
            
            if symbol and strategy_id:
                logger.info(f"为特定策略更新订阅状态: {symbol} -> {strategy_id}")
                self.on_subscription_success(symbol, strategy_id)
            else:
                # 如果没有指定strategy_id，为所有订阅此合约的策略更新状态
                if symbol and symbol in self.subscribers:
                    strategies = list(self.subscribers[symbol])
                    logger.info(f"为所有订阅策略更新状态: {symbol} -> {strategies}")
                    for strategy in strategies:
                        self.on_subscription_success(symbol, strategy)
                        logger.info(f"已更新策略 {strategy} 的订阅状态: {symbol}")
                else:
                    logger.warning(f"合约 {symbol} 没有找到订阅的策略")
                        
        except Exception as e:
            logger.error(f"处理网关订阅成功事件失败: {e}")

    def _setup_data_event_handlers(self):
        """设置数据服务事件处理器"""
        try:
            # 订阅数据相关事件
            self.event_bus.subscribe(EventType.DATA_SUBSCRIBE, self._handle_data_subscribe)
            self.event_bus.subscribe(EventType.DATA_UNSUBSCRIBE, self._handle_data_unsubscribe)
            
            # 订阅网关相关事件
            self.event_bus.subscribe(EventType.GATEWAY_SUBSCRIPTION_SUCCESS, self._handle_gateway_subscription_success)
            self.event_bus.subscribe(EventType.GATEWAY_SUBSCRIPTION_FAILED, self._handle_gateway_subscription_failed)
            
            # 数据中心连接事件
            self.event_bus.subscribe(EventType.DATA_CENTER_CONNECTED, self._handle_data_center_connected)
            self.event_bus.subscribe(EventType.DATA_CENTER_DISCONNECTED, self._handle_data_center_disconnected)
            
            logger.info("数据服务事件处理器已注册")
            
        except Exception as e:
            logger.error(f"设置数据服务事件处理器失败: {e}")

    def _handle_data_unsubscribe(self, event: Event):
        """处理取消订阅请求"""
        try:
            data = event.data
            symbols = data.get("symbols", [])
            strategy_id = data.get("strategy_id", "unknown")
            
            logger.info(f"处理取消订阅请求: 策略={strategy_id}, 合约={symbols}")
            
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.unsubscribe_market_data(symbols, strategy_id))
            except RuntimeError:
                # 没有运行的事件循环，直接调用同步版本
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    executor.submit(self._unsubscribe_market_data, symbols, strategy_id)
            
        except Exception as e:
            logger.error(f"处理取消订阅请求失败: {e}")
    
    def _unsubscribe_market_data(self, symbols: List[str], strategy_id: str):
        """取消订阅行情数据"""
        try:
            for symbol in symbols:
                self.subscribers[symbol].discard(strategy_id)
                self.strategy_subscriptions[strategy_id].discard(symbol)
                
                # 更新订阅状态
                key = f"{symbol}_{strategy_id}"
                if hasattr(self, 'subscription_states') and key in self.subscription_states:
                    self.subscription_states[key]["state"] = "unsubscribed"
                    self.subscription_states[key]["timestamp"] = time.time()
            
            # 发布取消订阅事件到网关
            if self.event_bus:
                from src.core.event import create_trading_event
                
                gateway_event = create_trading_event(
                    EventType.GATEWAY_UNSUBSCRIBE,
                    {
                        "symbols": symbols,
                        "strategy_id": strategy_id
                    },
                    source="DataService"
                )
                
                self.event_bus.publish(gateway_event)
            
            logger.info(f"策略 {strategy_id} 取消订阅行情: {symbols}")
            
        except Exception as e:
            logger.error(f"同步取消订阅失败: {e}")

    def _handle_gateway_subscription_failed(self, event: Event):
        """处理网关订阅失败事件"""
        try:
            data = event.data
            symbol = data.get("symbol")
            strategy_id = data.get("strategy_id", "unknown")
            reason = data.get("reason", "未知原因")
            
            logger.warning(f"网关订阅失败: {symbol} (策略: {strategy_id}) - {reason}")
            
            # 更新订阅状态
            if symbol and strategy_id:
                self._record_subscription_state(symbol, strategy_id, "failed")
                
                # 尝试重试
                self._retry_subscription(symbol, strategy_id)
                
        except Exception as e:
            logger.error(f"处理网关订阅失败事件失败: {e}")
    
    def _handle_query_tick(self, event: Event):
        """处理tick数据查询"""
        try:
            query_params = event.data
            
            # 转发查询请求到数据中心
            if self.data_center_available:
                self.event_bus.publish(create_market_event(
                    EventType.DATA_CENTER_QUERY_TICK,
                    query_params,
                    "DataService"
                ))
            else:
                # 数据中心不可用，返回错误
                self.event_bus.publish(create_market_event(
                    EventType.DATA_CENTER_TICK_RESULT,
                    {
                        "symbol": query_params.get("symbol"),
                        "data": [],
                        "error": "数据中心不可用",
                        "query_id": query_params.get("query_id")
                    },
                    "DataService"
                ))
            
        except Exception as e:
            logger.error(f"tick查询失败: {e}")
    
    def _handle_query_bar(self, event: Event):
        """处理bar数据查询"""
        try:
            query_params = event.data
            
            # 转发查询请求到数据中心
            if self.data_center_available:
                self.event_bus.publish(create_market_event(
                    EventType.DATA_CENTER_QUERY_BAR,
                    query_params,
                    "DataService"
                ))
            else:
                # 数据中心不可用，返回错误
                self.event_bus.publish(create_market_event(
                    EventType.DATA_CENTER_BAR_RESULT,
                    {
                        "symbol": query_params.get("symbol"),
                        "interval": query_params.get("interval"),
                        "data": [],
                        "error": "数据中心不可用",
                        "query_id": query_params.get("query_id")
                    },
                    "DataService"
                ))
            
        except Exception as e:
            logger.error(f"bar查询失败: {e}")
    
    def _handle_data_center_connected(self, event: Event):
        """处理数据中心连接事件"""
        try:
            self.data_center_available = True
            logger.info("数据中心连接成功")
        except Exception as e:
            logger.error(f"处理数据中心连接事件失败: {e}")
    
    def _handle_data_center_disconnected(self, event: Event):
        """处理数据中心断开事件"""
        try:
            self.data_center_available = False
            logger.warning("数据中心连接断开")
        except Exception as e:
            logger.error(f"处理数据中心断开事件失败: {e}")
    
    def _check_data_center_connection(self):
        """检查数据中心连接"""
        try:
            # 发布数据中心连接检查事件
            self.event_bus.publish(create_market_event(
                EventType.DATA_CENTER_CHECK,
                {},
                "DataService"
            ))
            logger.info("已发送数据中心连接检查请求")
        except Exception as e:
            logger.error(f"检查数据中心连接失败: {e}")
    
    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """获取最新tick数据"""
        return self.tick_buffer.get(symbol)
    
    def get_latest_bar(self, symbol: str, interval: str = "1m") -> Optional[BarData]:
        """获取最新bar数据"""
        return self.bar_buffer.get(symbol, {}).get(interval)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        current_time = time.time()
        if current_time > self.stats["last_tick_time"]:
            time_diff = current_time - self.stats["last_tick_time"]
            self.stats["processing_rate"] = self.stats["tick_count"] / max(time_diff, 1)
        
        return {
            "tick_count": self.stats["tick_count"],
            "bar_count": self.stats["bar_count"],
            "processing_rate": self.stats["processing_rate"],
            "buffer_size": len(self.tick_buffer),
            "subscribers_count": sum(len(subs) for subs in self.subscribers.values()),
            "data_center_available": self.data_center_available
        }
