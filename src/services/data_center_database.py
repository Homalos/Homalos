#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : data_center_database
@Date       : 2025/1/20
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据中心数据库管理器
"""
import sqlite3
import threading
import time
import pandas as pd
from datetime import datetime, date
from pathlib import Path
from queue import Queue, Empty
from typing import List, Dict, Any, Optional

import aiosqlite

from src.core.logger import get_logger
from src.core.object import TickData, BarData

logger = get_logger("DataCenterDatabase")


class DataCenterDatabase:
    """数据中心数据库管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 数据库配置
        db_config = config.get("database", {})
        self.db_path = Path(db_config.get("sqlite", {}).get("path", "data/data_center.db"))
        
        # Parquet配置
        parquet_config = config.get("parquet", {})
        self.parquet_base_path = Path(parquet_config.get("base_path", "data/parquet"))
        self.parquet_compression = parquet_config.get("compression", "snappy")
        
        # 批量写入配置
        batch_write_config = config.get("batch_write", {})
        self.tick_batch_size = batch_write_config.get("tick", {}).get("batch_size", 1000)
        self.tick_flush_interval = batch_write_config.get("tick", {}).get("flush_interval", 5)
        self.bar_batch_size = batch_write_config.get("bar", {}).get("batch_size", 10)
        self.bar_flush_interval = db_config.get("bar", {}).get("flush_interval", 5)
        self.flush_interval = self.tick_flush_interval  # 添加这个属性

        # 批量写入缓存
        self._tick_batch: List[Dict[str, Any]] = []
        self._bar_batch: List[Dict[str, Any]] = []
        self._batch_lock = threading.Lock()
        
        # Parquet缓存
        self._tick_parquet_buffer: List[Dict[str, Any]] = []
        self._bar_parquet_buffer: List[Dict[str, Any]] = []
        self._parquet_lock = threading.Lock()

        # 后台写入线程
        self._write_queue = Queue()
        self._write_thread = None
        self._parquet_thread = None
        self._running = False

        self._init_database()
        self._init_parquet_storage()

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

                # 数据中心只需要行情数据表，不需要交易相关表（orders、positions、trades）

                # 创建索引（仅为行情数据表创建索引）
                indices = [
                    "CREATE INDEX IF NOT EXISTS idx_tick_symbol_time ON tick_data(symbol, datetime)",
                    "CREATE INDEX IF NOT EXISTS idx_bar_symbol_time ON bar_data(symbol, datetime)"
                ]

                for idx in indices:
                    conn.execute(idx)

                conn.commit()

            logger.info(f"SQLite数据库初始化成功: {self.db_path}")

        except Exception as e:
            logger.error(f"SQLite数据库初始化失败: {e}")
            raise
    
    def _init_parquet_storage(self):
        """初始化Parquet存储"""
        try:
            # 确保Parquet目录存在
            self.parquet_base_path.mkdir(parents=True, exist_ok=True)
            
            # 创建子目录
            (self.parquet_base_path / "tick_data").mkdir(exist_ok=True)
            (self.parquet_base_path / "bar_data").mkdir(exist_ok=True)
            
            logger.info(f"Parquet存储初始化成功: {self.parquet_base_path}")
            
        except Exception as e:
            logger.error(f"Parquet存储初始化失败: {e}")
            raise

    def start(self):
        """启动后台写入线程"""
        if self._running:
            return

        self._running = True
        
        # 启动SQLite写入线程
        self._write_thread = threading.Thread(target=self._background_writer, daemon=True)
        self._write_thread.start()
        
        # 启动Parquet写入线程
        self._parquet_thread = threading.Thread(target=self._background_parquet_writer, daemon=True)
        self._parquet_thread.start()
        
        logger.info("数据库写入线程已启动（SQLite + Parquet）")

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
        self._flush_all_parquet_buffers()

        logger.info("数据库写入线程已停止（SQLite + Parquet）")
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据库状态"""
        try:
            return {
                'running': self._running,
                'db_path': str(self.db_path),
                'parquet_path': str(self.parquet_base_path),
                'tick_batch_size': len(self._tick_batch),
                'bar_batch_size': len(self._bar_batch),
                'tick_parquet_buffer_size': len(self._tick_parquet_buffer),
                'bar_parquet_buffer_size': len(self._bar_parquet_buffer),
                'write_queue_size': self._write_queue.qsize(),
                'write_thread_alive': self._write_thread.is_alive() if self._write_thread else False,
                'parquet_thread_alive': self._parquet_thread.is_alive() if self._parquet_thread else False
            }
        except Exception as e:
            logger.error(f"获取数据库状态失败: {e}")
            return {'error': str(e)}

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
    
    def _background_parquet_writer(self):
        """Parquet后台写入线程"""
        last_flush = time.time()
        
        while self._running:
            try:
                # 检查是否需要定时刷新
                current_time = time.time()
                if current_time - last_flush >= max(self.tick_flush_interval, self.bar_flush_interval):
                    self._flush_all_parquet_buffers()
                    last_flush = current_time
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Parquet后台写入线程异常: {e}")
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

    def save_tick_data(self, tick_data):
        """保存tick数据（同步版本）"""
        # 支持TickData对象和字典两种格式
        if hasattr(tick_data, 'symbol'):  # TickData对象
            tick_dict = {
                'symbol': tick_data.symbol,
                'exchange': tick_data.exchange.value if hasattr(tick_data.exchange, 'value') else str(tick_data.exchange),
                'datetime': tick_data.datetime.isoformat() if hasattr(tick_data.datetime, 'isoformat') else str(tick_data.datetime),
                'last_price': tick_data.last_price,
                'volume': tick_data.volume,
                'turnover': tick_data.turnover,
                'open_interest': tick_data.open_interest,
                'bid_price_1': tick_data.bid_price_1,
                'ask_price_1': tick_data.ask_price_1,
                'bid_volume_1': tick_data.bid_volume_1,
                'ask_volume_1': tick_data.ask_volume_1
            }
        else:  # 字典格式
            tick_dict = tick_data.copy()
            # 处理枚举值转换
            if 'exchange' in tick_dict and hasattr(tick_dict['exchange'], 'value'):
                tick_dict['exchange'] = tick_dict['exchange'].value
            if 'datetime' in tick_dict and hasattr(tick_dict['datetime'], 'isoformat'):
                tick_dict['datetime'] = tick_dict['datetime'].isoformat()

        self._write_queue.put({"type": "tick", "data": tick_dict})
        
        # 同时添加到Parquet缓冲区
        self._add_tick_to_parquet_buffer(tick_dict)
    
    async def save_tick_data_async(self, tick_data: TickData):
        """异步保存tick数据"""
        self.save_tick_data(tick_data)

    def save_bar_data(self, bar_data):
        """保存bar数据（同步版本）"""
        # 支持BarData对象和字典两种格式
        if hasattr(bar_data, 'symbol'):  # BarData对象
            bar_dict = {
                'symbol': bar_data.symbol,
                'exchange': bar_data.exchange.value if hasattr(bar_data.exchange, 'value') else str(bar_data.exchange),
                'interval': bar_data.interval.value if hasattr(bar_data.interval, 'value') else str(bar_data.interval) if bar_data.interval else '1m',
                'datetime': bar_data.datetime.isoformat(),
                'open_price': bar_data.open_price,
                'high_price': bar_data.high_price,
                'low_price': bar_data.low_price,
                'close_price': bar_data.close_price,
                'volume': bar_data.volume,
                'turnover': bar_data.turnover,
                'open_interest': bar_data.open_interest
            }
        else:  # 字典格式
            bar_dict = bar_data.copy()
            # 处理枚举值转换
            if 'exchange' in bar_dict and hasattr(bar_dict['exchange'], 'value'):
                bar_dict['exchange'] = bar_dict['exchange'].value
            if 'interval' in bar_dict and hasattr(bar_dict['interval'], 'value'):
                bar_dict['interval'] = bar_dict['interval'].value
            if 'datetime' in bar_dict and hasattr(bar_dict['datetime'], 'isoformat'):
                bar_dict['datetime'] = bar_dict['datetime'].isoformat()

        self._write_queue.put({"type": "bar", "data": bar_dict})
        
        # 同时添加到Parquet缓冲区
        self._add_bar_to_parquet_buffer(bar_dict)
    
    async def save_bar_data_async(self, bar_data: BarData):
        """异步保存bar数据"""
        self.save_bar_data(bar_data)

    def query_tick_data(self, symbol: str, exchange: str,
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
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"查询tick数据失败: {e}")
            return []
    
    async def query_tick_data_async(self, symbol: str, exchange: str,
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None,
                              limit: int = 1000) -> List[Dict[str, Any]]:
        """查询tick数据（异步版本）"""
        return self.query_tick_data(symbol, exchange, start_time, end_time, limit)

    def query_bar_data(self, symbol: str, exchange: str, interval: str,
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
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"查询bar数据失败: {e}")
            return []
    
    async def query_bar_data_async(self, symbol: str, exchange: str, interval: str,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             limit: int = 1000) -> List[Dict[str, Any]]:
        """查询bar数据（异步版本）"""
        return self.query_bar_data(symbol, exchange, interval, start_time, end_time, limit)

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
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            if len(self._tick_batch) >= self.tick_batch_size:
                self._flush_tick_batch()

    def _add_bar_to_batch(self, data):
        with self._batch_lock:
            self._bar_batch.append(data)
            if len(self._bar_batch) >= self.bar_batch_size:
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
    
    def _add_tick_to_parquet_buffer(self, data: Dict[str, Any]):
        """添加tick数据到Parquet缓冲区"""
        with self._parquet_lock:
            self._tick_parquet_buffer.append(data)
            if len(self._tick_parquet_buffer) >= self.tick_batch_size:
                self._flush_tick_parquet_buffer()
    
    def _add_bar_to_parquet_buffer(self, data: Dict[str, Any]):
        """添加bar数据到Parquet缓冲区"""
        with self._parquet_lock:
            self._bar_parquet_buffer.append(data)
            if len(self._bar_parquet_buffer) >= self.bar_batch_size:
                self._flush_bar_parquet_buffer()
    
    def _flush_all_parquet_buffers(self):
        """刷新所有Parquet缓冲区"""
        with self._parquet_lock:
            try:
                if self._tick_parquet_buffer:
                    self._flush_tick_parquet_buffer()
                if self._bar_parquet_buffer:
                    self._flush_bar_parquet_buffer()
            except Exception as e:
                logger.error(f"Parquet批量刷新失败: {e}")
    
    def _flush_tick_parquet_buffer(self):
        """刷新tick数据Parquet缓冲区"""
        if not self._tick_parquet_buffer:
            return
        
        try:
            # 按日期分组
            date_groups = {}
            for data in self._tick_parquet_buffer:
                dt = datetime.fromisoformat(data['datetime'])
                date_key = dt.date()
                if date_key not in date_groups:
                    date_groups[date_key] = []
                date_groups[date_key].append(data)
            
            # 分别写入每个日期的文件
            for date_key, date_data in date_groups.items():
                df = pd.DataFrame(date_data)
                file_path = self.parquet_base_path / "tick_data" / f"tick_{date_key.strftime('%Y%m%d')}.parquet"
                
                # 如果文件已存在，追加数据
                if file_path.exists():
                    existing_df = pd.read_parquet(file_path)
                    df = pd.concat([existing_df, df], ignore_index=True)
                    # 去重并排序
                    df = df.drop_duplicates(subset=['symbol', 'exchange', 'datetime']).sort_values('datetime')
                
                df.to_parquet(file_path, compression=self.parquet_compression, index=False)
            
            buffer_count = len(self._tick_parquet_buffer)
            self._tick_parquet_buffer.clear()
            logger.debug(f"Tick Parquet数据写入完成，共{buffer_count}条")
            
        except Exception as e:
            logger.error(f"Tick Parquet写入失败: {e}")
    
    def _flush_bar_parquet_buffer(self):
        """刷新bar数据Parquet缓冲区"""
        if not self._bar_parquet_buffer:
            return
        
        try:
            # 按日期分组
            date_groups = {}
            for data in self._bar_parquet_buffer:
                dt = datetime.fromisoformat(data['datetime'])
                date_key = dt.date()
                if date_key not in date_groups:
                    date_groups[date_key] = []
                date_groups[date_key].append(data)
            
            # 分别写入每个日期的文件
            for date_key, date_data in date_groups.items():
                df = pd.DataFrame(date_data)
                file_path = self.parquet_base_path / "bar_data" / f"bar_{date_key.strftime('%Y%m%d')}.parquet"
                
                # 如果文件已存在，追加数据
                if file_path.exists():
                    existing_df = pd.read_parquet(file_path)
                    df = pd.concat([existing_df, df], ignore_index=True)
                    # 去重并排序
                    df = df.drop_duplicates(subset=['symbol', 'exchange', 'interval', 'datetime']).sort_values('datetime')
                
                df.to_parquet(file_path, compression=self.parquet_compression, index=False)
            
            buffer_count = len(self._bar_parquet_buffer)
            self._bar_parquet_buffer.clear()
            logger.debug(f"Bar Parquet数据写入完成，共{buffer_count}条")
            
        except Exception as e:
            logger.error(f"Bar Parquet写入失败: {e}")
