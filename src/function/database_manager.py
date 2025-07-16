#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : database_manager
@Date       : 2025/7/16 14:58
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据库管理器
"""
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from typing import List, Dict, Any, Optional

import aiosqlite

from src.config.config_manager import ConfigManager
from src.core.logger import get_logger
from src.core.object import TickData, BarData

logger = get_logger("DatabaseManager")


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
        params.append(str(limit))

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
        params.append(str(limit))

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
