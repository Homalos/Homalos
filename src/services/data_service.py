#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : data_service
@Date       : 2025/7/6 21:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 统一数据服务 - 集成行情和存储
"""
import asyncio
import sqlite3
import aiosqlite
import time
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
import threading
from queue import Queue, Empty

from src.config.config_manager import ConfigManager
from src.core.event_bus import EventBus
from src.core.event import Event, EventType, create_market_event, create_log_event
from src.core.object import TickData, BarData, SubscribeRequest
from src.config.constant import Interval
from typing import DefaultDict
from src.core.logger import get_logger


logger = get_logger("DataService")


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.db_path = Path(config.get("database.path", "data/trading.db"))
        self.batch_size = config.get("database.batch_size", 100)
        self.flush_interval = config.get("database.flush_interval", 5)
        
        # 批量写入缓存
        self._tick_batch: List[Dict[str, Any]] = []
        self._bar_batch: List[Dict[str, Any]] = []
        self._batch_lock = threading.Lock()
        
        # 后台写入线程
        self._write_queue = Queue()
        self._write_thread = None
        self._running = False
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        try:
            # 确保目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建数据表
            with sqlite3.connect(str(self.db_path)) as conn:
                # 启用WAL模式提高并发性能
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=-64000")  # 64MB缓存
                
                # Tick数据表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS tick_data (
                        symbol TEXT NOT NULL,
                        exchange TEXT NOT NULL,
                        datetime TEXT NOT NULL,
                        last_price REAL,
                        volume REAL,
                        turnover REAL,
                        open_interest REAL,
                        bid_price_1 REAL,
                        ask_price_1 REAL,
                        bid_volume_1 REAL,
                        ask_volume_1 REAL,
                        PRIMARY KEY (symbol, exchange, datetime)
                    )
                ''')
                
                # Bar数据表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS bar_data (
                        symbol TEXT NOT NULL,
                        exchange TEXT NOT NULL,
                        interval TEXT NOT NULL,
                        datetime TEXT NOT NULL,
                        open_price REAL,
                        high_price REAL,
                        low_price REAL,
                        close_price REAL,
                        volume REAL,
                        turnover REAL,
                        open_interest REAL,
                        PRIMARY KEY (symbol, exchange, interval, datetime)
                    )
                ''')
                
                # 订单数据表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id TEXT PRIMARY KEY,
                        strategy_id TEXT,
                        symbol TEXT,
                        exchange TEXT,
                        direction TEXT,
                        offset TEXT,
                        price REAL,
                        volume REAL,
                        traded REAL,
                        status TEXT,
                        create_time TEXT,
                        update_time TEXT
                    )
                ''')
                
                # 成交数据表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id TEXT PRIMARY KEY,
                        order_id TEXT,
                        strategy_id TEXT,
                        symbol TEXT,
                        exchange TEXT,
                        direction TEXT,
                        offset TEXT,
                        price REAL,
                        volume REAL,
                        datetime TEXT
                    )
                ''')
                
                # 持仓数据表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        strategy_id TEXT,
                        symbol TEXT,
                        exchange TEXT,
                        direction TEXT,
                        volume REAL,
                        frozen REAL,
                        price REAL,
                        pnl REAL,
                        yd_volume REAL,
                        update_time TEXT,
                        PRIMARY KEY (strategy_id, symbol, exchange, direction)
                    )
                ''')
                
                # 创建索引
                indices = [
                    "CREATE INDEX IF NOT EXISTS idx_tick_symbol_time ON tick_data(symbol, datetime)",
                    "CREATE INDEX IF NOT EXISTS idx_bar_symbol_time ON bar_data(symbol, datetime)",
                    "CREATE INDEX IF NOT EXISTS idx_orders_strategy ON orders(strategy_id)",
                    "CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_id)",
                    "CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy_id)"
                ]
                
                for idx in indices:
                    conn.execute(idx)
                
                conn.commit()
                
            logger.info(f"数据库初始化成功: {self.db_path}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def start(self):
        """启动后台写入线程"""
        if self._running:
            return
        
        self._running = True
        self._write_thread = threading.Thread(target=self._background_writer, daemon=True)
        self._write_thread.start()
        logger.info("数据库写入线程已启动")
    
    def stop(self):
        """停止后台写入线程"""
        if not self._running:
            return
        
        self._running = False
        
        # 等待写入队列清空
        while not self._write_queue.empty():
            time.sleep(0.1)
        
        # 刷新剩余批次
        self._flush_all_batches()
        
        logger.info("数据库写入线程已停止")
    
    def _background_writer(self):
        """后台写入线程"""
        last_flush = time.time()
        
        while self._running:
            try:
                # 检查是否需要定时刷新
                current_time = time.time()
                if current_time - last_flush >= self.flush_interval:
                    self._flush_all_batches()
                    last_flush = current_time
                
                # 处理写入队列
                try:
                    task = self._write_queue.get(timeout=1.0)
                    self._execute_write_task(task)
                except Empty:
                    continue
                    
            except Exception as e:
                logger.error(f"后台写入线程异常: {e}")
                time.sleep(1)
    
    def _execute_write_task(self, task: Dict[str, Any]):
        """执行写入任务"""
        try:
            task_type = task["type"]
            data = task["data"]
            
            if task_type == "tick":
                self._add_tick_to_batch(data)
            elif task_type == "bar":
                self._add_bar_to_batch(data)
            elif task_type == "direct_sql":
                self._execute_direct_sql(data)
                
        except Exception as e:
            logger.error(f"写入任务执行失败: {e}")
    
    async def save_tick_data(self, tick_data: TickData):
        """异步保存tick数据"""
        tick_dict = {
            'symbol': tick_data.symbol,
            'exchange': tick_data.exchange.value,
            'datetime': tick_data.datetime.isoformat(),
            'last_price': tick_data.last_price,
            'volume': tick_data.volume,
            'turnover': tick_data.turnover,
            'open_interest': tick_data.open_interest,
            'bid_price_1': tick_data.bid_price_1,
            'ask_price_1': tick_data.ask_price_1,
            'bid_volume_1': tick_data.bid_volume_1,
            'ask_volume_1': tick_data.ask_volume_1
        }
        
        self._write_queue.put({"type": "tick", "data": tick_dict})
    
    async def save_bar_data(self, bar_data: BarData):
        """异步保存bar数据"""
        bar_dict = {
            'symbol': bar_data.symbol,
            'exchange': bar_data.exchange.value,
            'interval': bar_data.interval.value if bar_data.interval else '1m',
            'datetime': bar_data.datetime.isoformat(),
            'open_price': bar_data.open_price,
            'high_price': bar_data.high_price,
            'low_price': bar_data.low_price,
            'close_price': bar_data.close_price,
            'volume': bar_data.volume,
            'turnover': bar_data.turnover,
            'open_interest': bar_data.open_interest
        }
        
        self._write_queue.put({"type": "bar", "data": bar_dict})
    
    async def query_tick_data(self, symbol: str, exchange: str, 
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None,
                              limit: int = 1000) -> List[Dict[str, Any]]:
        """查询tick数据"""
        conditions = ["symbol = ? AND exchange = ?"]
        params = [symbol, exchange]
        
        if start_time:
            conditions.append("datetime >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("datetime <= ?")
            params.append(end_time.isoformat())
        
        sql = f'''
            SELECT * FROM tick_data 
            WHERE {" AND ".join(conditions)}
            ORDER BY datetime DESC 
            LIMIT ?
        '''
        params.append(limit)
        
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                async with conn.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"查询tick数据失败: {e}")
            return []
    
    async def query_bar_data(self, symbol: str, exchange: str, interval: str,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             limit: int = 1000) -> List[Dict[str, Any]]:
        """查询bar数据"""
        conditions = ["symbol = ? AND exchange = ? AND interval = ?"]
        params = [symbol, exchange, interval]
        
        if start_time:
            conditions.append("datetime >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("datetime <= ?")
            params.append(end_time.isoformat())
        
        sql = f'''
            SELECT * FROM bar_data 
            WHERE {" AND ".join(conditions)}
            ORDER BY datetime DESC 
            LIMIT ?
        '''
        params.append(limit)
        
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                async with conn.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"查询bar数据失败: {e}")
            return []

    def _flush_all_batches(self):
        """批量刷新所有缓存到数据库"""
        with self._batch_lock:
            try:
                if self._tick_batch:
                    self._flush_tick_batch()
                if self._bar_batch:
                    self._flush_bar_batch()
            except Exception as e:
                logger.error(f"批量刷新失败: {e}")

    def _flush_tick_batch(self):
        if not self._tick_batch:
            return
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.executemany('''
                    INSERT OR REPLACE INTO tick_data (
                        symbol, exchange, datetime, last_price, volume, turnover, open_interest,
                        bid_price_1, ask_price_1, bid_volume_1, ask_volume_1
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [(
                    d['symbol'], d['exchange'], d['datetime'], d['last_price'], d['volume'], d['turnover'],
                    d['open_interest'], d['bid_price_1'], d['ask_price_1'], d['bid_volume_1'], d['ask_volume_1']
                ) for d in self._tick_batch])
                conn.commit()
            self._tick_batch.clear()
        except Exception as e:
            logger.error(f"Tick批量写入失败: {e}")

    def _flush_bar_batch(self):
        if not self._bar_batch:
            return
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.executemany('''
                    INSERT OR REPLACE INTO bar_data (
                        symbol, exchange, interval, datetime, open_price, high_price, low_price, close_price,
                        volume, turnover, open_interest
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [(
                    d['symbol'], d['exchange'], d['interval'], d['datetime'], d['open_price'], d['high_price'],
                    d['low_price'], d['close_price'], d['volume'], d['turnover'], d['open_interest']
                ) for d in self._bar_batch])
                conn.commit()
            self._bar_batch.clear()
        except Exception as e:
            logger.error(f"Bar批量写入失败: {e}")

    def _add_tick_to_batch(self, data):
        with self._batch_lock:
            self._tick_batch.append(data)
            if len(self._tick_batch) >= self.batch_size:
                self._flush_tick_batch()

    def _add_bar_to_batch(self, data):
        with self._batch_lock:
            self._bar_batch.append(data)
            if len(self._bar_batch) >= self.batch_size:
                self._flush_bar_batch()

    def _execute_direct_sql(self, sql_data):
        try:
            sql = sql_data.get('sql')
            params = sql_data.get('params', [])
            if not sql:
                logger.error("未提供SQL语句")
                return
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(sql, params)
                conn.commit()
        except Exception as e:
            logger.error(f"执行直接SQL失败: {e}")


class BarGenerator:
    """单symbol单周期K线合成器"""
    def __init__(self, symbol: str, exchange, interval_minutes: int):
        self.symbol = symbol
        self.exchange = exchange
        self.interval_minutes = interval_minutes
        self.current_bar: BarData | None = None
        self.last_bar_end: datetime | None = None

    def on_tick(self, tick: TickData) -> BarData | None:
        dt = tick.datetime.replace(second=0, microsecond=0)
        # 计算当前tick属于哪个bar周期
        minute = (dt.minute // self.interval_minutes) * self.interval_minutes
        bar_start = dt.replace(minute=minute)
        if self.last_bar_end is None or bar_start > self.last_bar_end:
            # 新K线周期，输出上一根K线
            finished_bar = self.current_bar
            interval_type = Interval.MINUTE if self.interval_minutes == 1 else Interval.MINUTE  # 先全部用MINUTE
            self.current_bar = BarData(
                symbol=self.symbol,
                exchange=self.exchange,
                datetime=bar_start,
                gateway_name=tick.gateway_name,
                interval=interval_type,
                open_price=tick.last_price,
                high_price=tick.last_price,
                low_price=tick.last_price,
                close_price=tick.last_price,
                volume=tick.volume,
                turnover=tick.turnover,
                open_interest=tick.open_interest
            )
            self.last_bar_end = bar_start
            return finished_bar
        else:
            # 更新当前K线
            bar = self.current_bar
            if bar:
                bar.close_price = tick.last_price
                bar.high_price = max(bar.high_price, tick.last_price)
                bar.low_price = min(bar.low_price, tick.last_price)
                bar.volume = tick.volume
                bar.turnover = tick.turnover
                bar.open_interest = tick.open_interest
        return None

class BarManager:
    """多symbol多周期K线管理器"""
    def __init__(self, intervals: list[int]):
        self.intervals = intervals
        self.generators: DefaultDict[str, dict[int, BarGenerator]] = defaultdict(dict)

    def on_tick(self, tick: TickData) -> list[BarData]:
        bars: list[BarData] = []
        symbol = tick.symbol
        exchange = tick.exchange
        logger.debug(f"BarManager收到tick: {symbol} {tick.datetime} {tick.last_price}")
        for interval in self.intervals:
            if interval not in self.generators[symbol]:
                self.generators[symbol][interval] = BarGenerator(symbol, exchange, interval)
            bar = self.generators[symbol][interval].on_tick(tick)
            if bar is not None:
                logger.info(f"BarManager生成K线: {bar.symbol} {bar.datetime} O:{bar.open_price} H:{bar.high_price} L:{bar.low_price} C:{bar.close_price}")
                bars.append(bar)
        return bars


class DataService:
    """统一的数据服务 - 整合行情和存储"""
    
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        
        # 数据库管理器
        self.db_manager = DatabaseManager(config)
        
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
        self.enable_persistence = config.get("data.market.enable_persistence", True)
        
        # K线合成管理
        self.bar_manager = BarManager([1, 5, 10])  # 支持1m/5m/10m
        
        # 性能统计
        self.stats = {
            "tick_count": 0,
            "bar_count": 0,
            "last_tick_time": 0,
            "processing_rate": 0
        }
        
        # 注册事件处理器
        self._setup_event_handlers()
        
        logger.info("数据服务初始化完成")
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        # 行情数据处理
        self.event_bus.subscribe("market.tick.raw", self._handle_raw_tick)
        self.event_bus.subscribe("market.bar.raw", self._handle_raw_bar)
        
        # 订阅管理
        self.event_bus.subscribe("data.subscribe", self._handle_data_subscribe)
        self.event_bus.subscribe("data.unsubscribe", self._handle_data_unsubscribe)
        
        # 数据查询
        self.event_bus.subscribe("data.query.tick", self._handle_query_tick)
        self.event_bus.subscribe("data.query.bar", self._handle_query_bar)
        
        # 持久化控制
        self.event_bus.subscribe("data.persist", self._handle_persist_data)
    
    async def initialize(self):
        """初始化数据服务"""
        try:
            # 启动数据库管理器
            self.db_manager.start()
            
            logger.info("数据服务初始化成功")
            return True
        except Exception as e:
            logger.error(f"数据服务初始化失败: {e}")
            return False
    
    async def shutdown(self):
        """关闭数据服务"""
        try:
            # 停止数据库管理器
            self.db_manager.stop()
            
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
                from src.core.event import create_trading_event
                
                gateway_event = create_trading_event(
                    "gateway.subscribe",
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
        """检查订阅超时"""
        try:
            await asyncio.sleep(10)  # 等待10秒
            
            for symbol in symbols:
                key = f"{symbol}_{strategy_id}"
                if hasattr(self, 'subscription_states') and key in self.subscription_states:
                    state_info = self.subscription_states[key]
                    
                    if state_info["state"] == "requested":
                        logger.warning(f"订阅超时: {symbol} (策略: {strategy_id})")
                        
                        # 标记为超时并重试
                        state_info["state"] = "timeout"
                        state_info["retry_count"] += 1
                        
                        if state_info["retry_count"] < 3:
                            logger.info(f"重试订阅: {symbol} (第{state_info['retry_count']}次)")
                            self._retry_subscription(symbol, strategy_id)
                        else:
                            logger.error(f"订阅重试次数超限: {symbol}")
                            state_info["state"] = "failed"
                            
        except Exception as e:
            logger.error(f"检查订阅超时失败: {e}")

    def _retry_subscription(self, symbol: str, strategy_id: str) -> None:
        """重试订阅"""
        try:
            logger.info(f"重试订阅: {symbol} (策略: {strategy_id})")
            
            # 重新发布订阅事件
            if self.event_bus:
                from src.core.event import create_trading_event
                
                gateway_event = create_trading_event(
                    "gateway.subscribe",
                    {
                        "symbols": [symbol],
                        "strategy_id": strategy_id
                    },
                    source="DataService.Retry"
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
        """处理原始tick数据"""
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
                logger.info(f"📊 数据流统计: 已处理{self.stats['tick_count']}个tick, 当前合约={tick_data.symbol}, 订阅策略数={len(self.subscribers.get(tick_data.symbol, set()))}")
            
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
                logger.info(f"📤 Tick分发: {symbol} @ {tick_data.last_price} → {subscriber_count}个策略")
            else:
                logger.debug(f"⚠️ 无订阅策略: {symbol} tick数据未分发")

            # 同时保持通用事件的发布，用于全局监听器
            self.event_bus.publish(create_market_event(
                EventType.MARKET_TICK,
                tick_data,
                "DataService"
            ))
            
            # 异步持久化
            if self.enable_persistence:
                asyncio.create_task(self.db_manager.save_tick_data(tick_data))
                
            # K线合成
            bars = self.bar_manager.on_tick(tick_data)
            for bar in bars:
                logger.info(f"分发MARKET_BAR: {bar.symbol} {bar.datetime} O:{bar.open_price} H:{bar.high_price} L:{bar.low_price} C:{bar.close_price}")
                self.event_bus.publish(Event("market.bar", bar))
                
        except Exception as e:
            logger.error(f"处理tick数据失败: {e}")
    
    def _handle_raw_bar(self, event: Event):
        """处理原始bar数据"""
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
            
            # 异步持久化
            if self.enable_persistence:
                asyncio.create_task(self.db_manager.save_bar_data(bar_data))
                
        except Exception as e:
            logger.error(f"处理bar数据失败: {e}")
    
    def _handle_data_subscribe(self, event: Event):
        """处理订阅请求 - 增强版本"""
        try:
            data = event.data
            symbols = data.get("symbols", [])
            strategy_id = data.get("strategy_id", "unknown")
            
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
                        "data.subscribe.success",
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
                        "data.subscribe.failed",
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
                from src.core.event import create_trading_event
                
                gateway_event = create_trading_event(
                    "gateway.unsubscribe",
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
            
            if symbol and strategy_id:
                self.on_subscription_success(symbol, strategy_id)
            else:
                # 如果没有指定strategy_id，为所有订阅此合约的策略更新状态
                if symbol and symbol in self.subscribers:
                    for strategy in self.subscribers[symbol]:
                        self.on_subscription_success(symbol, strategy)
                        
        except Exception as e:
            logger.error(f"处理网关订阅成功事件失败: {e}")

    def _setup_data_event_handlers(self):
        """设置数据服务事件处理器"""
        try:
            # 订阅数据相关事件
            self.event_bus.subscribe("data.subscribe", self._handle_data_subscribe)
            self.event_bus.subscribe("data.unsubscribe", self._handle_data_unsubscribe)
            
            # 订阅网关相关事件
            self.event_bus.subscribe("gateway.subscription.success", self._handle_gateway_subscription_success)
            self.event_bus.subscribe("gateway.subscription.failed", self._handle_gateway_subscription_failed)
            
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
            
            asyncio.create_task(self.unsubscribe_market_data(symbols, strategy_id))
            
        except Exception as e:
            logger.error(f"处理取消订阅请求失败: {e}")

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
        data = event.data
        asyncio.create_task(self._process_tick_query(data))
    
    def _handle_query_bar(self, event: Event):
        """处理bar数据查询"""
        data = event.data
        asyncio.create_task(self._process_bar_query(data))
    
    async def _process_tick_query(self, query_params: Dict[str, Any]):
        """处理tick查询请求"""
        try:
            result = await self.db_manager.query_tick_data(**query_params)
            
            # 发布查询结果
            self.event_bus.publish(create_market_event(
                "data.query.tick.result",
                {"query_params": query_params, "result": result},
                "DataService"
            ))
        except Exception as e:
            logger.error(f"tick查询失败: {e}")
    
    async def _process_bar_query(self, query_params: Dict[str, Any]):
        """处理bar查询请求"""
        try:
            result = await self.db_manager.query_bar_data(**query_params)
            
            # 发布查询结果
            self.event_bus.publish(create_market_event(
                "data.query.bar.result",
                {"query_params": query_params, "result": result},
                "DataService"
            ))
        except Exception as e:
            logger.error(f"bar查询失败: {e}")
    
    def _handle_persist_data(self, event: Event):
        """处理数据持久化请求"""
        data = event.data
        if isinstance(data, TickData):
            asyncio.create_task(self.db_manager.save_tick_data(data))
        elif isinstance(data, BarData):
            asyncio.create_task(self.db_manager.save_bar_data(data))
    
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
            "db_path": str(self.db_manager.db_path)
        } 