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
from collections import defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path
from queue import Queue, Empty
from typing import List, Dict, Any, Optional

import pandas as pd

from src.core.logger import get_logger
from src.core.object import TickData, BarData

logger = get_logger("DataCenterDatabase")


class DataCenterDatabase:
    """数据中心数据库管理器
    
    按合约分表存储tick和bar数据，每个合约独立建表。
    数据库文件结构：
    - tick_db/tick_YYYYMMDD.db：存储每日tick数据，每个合约一个表
    - bar_db/bar_YYYYMMDD.db：存储每日bar数据，每个合约一个表
    
    表命名规范：
    - tick表：tick_{symbol}_{exchange}
    - bar表：bar_{symbol}_{exchange}
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 数据库配置
        db_config = config.get("database", {})
        sqlite_config = db_config.get("sqlite", {})
        
        # 表结构策略
        self.table_strategy = db_config.get("table_strategy", "per_contract")
        
        # 合约表配置
        contract_tables_config = db_config.get("contract_tables", {})
        self.tick_table_format = contract_tables_config.get("tick_table_format", "tick_{symbol}_{exchange}")
        self.bar_table_format = contract_tables_config.get("bar_table_format", "bar_{symbol}_{exchange}")
        self.auto_create_tables = contract_tables_config.get("auto_create", True)
        self.table_cache_size = contract_tables_config.get("table_cache_size", 1000)
        self.parallel_write = contract_tables_config.get("parallel_write", True)
        self.max_parallel_workers = contract_tables_config.get("max_parallel_workers", 4)
        
        # 数据库路径配置
        tick_db_config = sqlite_config.get("tick_db", {})
        bar_db_config = sqlite_config.get("bar_db", {})
        
        self.tick_db_path = Path(tick_db_config.get("path", "data/tick_db"))
        self.bar_db_path = Path(bar_db_config.get("path", "data/bar_db"))
        
        # 数据库连接配置
        self.tick_db_config = tick_db_config
        self.bar_db_config = bar_db_config
        
        # Parquet配置
        parquet_config = config.get("parquet", {})
        self.parquet_base_path = Path(parquet_config.get("base_path", "data"))
        self.parquet_compression = parquet_config.get("compression", "snappy")
        
        # 批量写入配置
        batch_write_config = config.get("batch_write", {})
        self.tick_batch_size = batch_write_config.get("tick", {}).get("batch_size", 1000)
        self.tick_flush_interval = batch_write_config.get("tick", {}).get("flush_interval", 5)
        self.bar_batch_size = batch_write_config.get("bar", {}).get("batch_size", 500)
        self.bar_flush_interval = batch_write_config.get("bar", {}).get("flush_interval", 10)
        self.flush_interval = self.tick_flush_interval

        # 按合约和日期分组的批量写入缓存
        self._tick_batches = defaultdict(lambda: defaultdict(list))  # {date_str: {contract_key: [data_list]}}
        self._bar_batches = defaultdict(lambda: defaultdict(list))   # {date_str: {contract_key: [data_list]}}
        self._batch_lock = threading.Lock()
        
        # Parquet缓存
        self._tick_parquet_buffer: List[Dict[str, Any]] = []
        self._bar_parquet_buffer: List[Dict[str, Any]] = []
        self._parquet_lock = threading.Lock()

        # 表缓存 - 记录已创建的表
        self._created_tables = set()  # {(data_type, date_str, table_name)}
        self._table_cache_lock = threading.Lock()

        # 后台写入线程
        self._write_queue = Queue()
        self._write_thread = None
        self._parquet_thread = None
        self._running = False

        self._init_database_dirs()
        self._init_parquet_storage()

    def _init_database_dirs(self):
        """初始化数据库目录"""
        try:
            # 确保数据库目录存在
            self.tick_db_path.mkdir(parents=True, exist_ok=True)
            self.bar_db_path.mkdir(parents=True, exist_ok=True)
            logger.info("数据中心数据库目录初始化完成")
        except Exception as e:
            logger.error(f"数据库目录初始化失败: {e}")
    
    def _get_db_path(self, data_type: str, trade_date: date) -> Path:
        """获取指定日期和数据类型的数据库文件路径"""
        date_str = trade_date.strftime('%Y%m%d')
        if data_type == 'tick':
            return self.tick_db_path / f"tick_{date_str}.db"
        elif data_type == 'bar':
            return self.bar_db_path / f"bar_{date_str}.db"
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")
    
    def _get_contract_key(self, symbol: str, exchange: str) -> str:
        """生成合约唯一标识"""
        return f"{symbol}_{exchange}"
    
    def _get_table_name(self, data_type: str, symbol: str, exchange: str) -> str:
        """生成表名 - 直接使用合约名作为表名"""
        # 直接使用合约名作为表名，不再添加前缀
        return symbol
    
    def _create_contract_table(self, data_type: str, symbol: str, exchange: str, trade_date: date):
        """为指定合约创建表"""
        db_path = self._get_db_path(data_type, trade_date)
        table_name = self._get_table_name(data_type, symbol, exchange)
        date_str = trade_date.strftime('%Y%m%d')
        
        # 检查表是否已创建（加上数据类型以区分不同数据库）
        table_key = (data_type, date_str, table_name)
        with self._table_cache_lock:
            if table_key in self._created_tables:
                return
        
        # 获取对应数据类型的配置
        if data_type == 'tick':
            db_config = self.tick_db_config
        elif data_type == 'bar':
            db_config = self.bar_db_config
        else:
            db_config = {"wal_mode": True, "cache_size": 10000, "timeout": 30}
        
        try:
            with sqlite3.connect(str(db_path), timeout=db_config.get('timeout', 30)) as conn:
                # 根据配置启用WAL模式
                if db_config.get('wal_mode', True):
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                else:
                    conn.execute("PRAGMA journal_mode=DELETE")
                    conn.execute("PRAGMA synchronous=FULL")
                
                # 设置缓存大小
                cache_size = db_config.get('cache_size', 10000)
                if cache_size > 0:
                    conn.execute(f"PRAGMA cache_size=-{cache_size}")  # 负数表示KB
                else:
                    conn.execute(f"PRAGMA cache_size={cache_size}")  # 正数表示页数
                
                # 创建统一的合约表（包含tick和bar数据）
                conn.execute(f'''
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        data_type TEXT NOT NULL,
                        datetime TEXT NOT NULL,
                        interval TEXT,
                        last_price REAL,
                        open_price REAL,
                        high_price REAL,
                        low_price REAL,
                        close_price REAL,
                        volume REAL,
                        turnover REAL,
                        open_interest REAL,
                        bid_price_1 REAL,
                        ask_price_1 REAL,
                        bid_volume_1 REAL,
                        ask_volume_1 REAL,
                        PRIMARY KEY (data_type, datetime, interval)
                    )
                ''')
                
                # 创建索引
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_datetime ON {table_name}(datetime)')
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_data_type ON {table_name}(data_type)')
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_interval ON {table_name}(interval)')
                
                conn.commit()
                
                # 标记表已创建（包含数据类型）
                with self._table_cache_lock:
                    self._created_tables.add(table_key)
                    
                logger.debug(f"{data_type}表创建完成 - 合约: {symbol}.{exchange}, 表名: {table_name}, 日期: {trade_date}")
                    
        except Exception as e:
            logger.error(f"创建{data_type}表失败 - 合约: {symbol}.{exchange}, 日期: {trade_date}, 错误: {e}")
            raise
    
    def _init_parquet_storage(self):
        """初始化Parquet存储"""
        try:
            # 确保Parquet目录存在
            self.parquet_base_path.mkdir(parents=True, exist_ok=True)
            
            # 创建主目录
            (self.parquet_base_path / "tick_parquet").mkdir(exist_ok=True)
            (self.parquet_base_path / "bar_parquet").mkdir(exist_ok=True)
            
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
            # 计算所有合约批次的总大小
            total_tick_batch_size = 0
            total_bar_batch_size = 0
            tick_batches_by_contract = {}
            bar_batches_by_contract = {}
            
            for contract_key, date_batches in self._tick_batches.items():
                contract_total = sum(len(batch) for batch in date_batches.values())
                total_tick_batch_size += contract_total
                tick_batches_by_contract[contract_key] = {
                    'total': contract_total,
                    'by_date': {date_str: len(batch) for date_str, batch in date_batches.items()}
                }
            
            for contract_key, date_batches in self._bar_batches.items():
                contract_total = sum(len(batch) for batch in date_batches.values())
                total_bar_batch_size += contract_total
                bar_batches_by_contract[contract_key] = {
                    'total': contract_total,
                    'by_date': {date_str: len(batch) for date_str, batch in date_batches.items()}
                }
            
            return {
                'running': self._running,
                'table_strategy': self.table_strategy,
                'tick_db_path': str(self.tick_db_path),
                'bar_db_path': str(self.bar_db_path),
                'parquet_path': str(self.parquet_base_path),
                'tick_batch_size': total_tick_batch_size,
                'bar_batch_size': total_bar_batch_size,
                'tick_batches_by_contract': tick_batches_by_contract,
                'bar_batches_by_contract': bar_batches_by_contract,
                'created_tables_count': len(self._created_tables),
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
                # 从队列任务中提取日期和合约信息
                dt = datetime.fromisoformat(data['datetime'])
                trade_date = dt.date()
                date_str = trade_date.strftime('%Y%m%d')
                symbol = data['symbol']
                exchange = data['exchange']
                contract_key = self._get_contract_key(symbol, exchange)
                
                # 确保表已创建
                self._create_contract_table('tick', symbol, exchange, trade_date)
                
                self._add_to_contract_batch('tick', contract_key, date_str, trade_date, data)
            elif task_type == "bar":
                # 从队列任务中提取日期和合约信息
                dt = datetime.fromisoformat(data['datetime'])
                trade_date = dt.date()
                date_str = trade_date.strftime('%Y%m%d')
                symbol = data['symbol']
                exchange = data['exchange']
                contract_key = self._get_contract_key(symbol, exchange)
                
                # 确保表已创建
                self._create_contract_table('bar', symbol, exchange, trade_date)
                
                self._add_to_contract_batch('bar', contract_key, date_str, trade_date, data)
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

        # 获取交易日期和合约信息
        dt = datetime.fromisoformat(tick_dict['datetime'])
        trade_date = dt.date()
        date_str = trade_date.strftime('%Y%m%d')
        symbol = tick_dict['symbol']
        exchange = tick_dict['exchange']
        contract_key = self._get_contract_key(symbol, exchange)
        
        # 确保表已创建
        self._create_contract_table('tick', symbol, exchange, trade_date)
        
        # 添加到按合约和日期分组的批量写入缓存
        self._add_to_contract_batch('tick', contract_key, date_str, trade_date, tick_dict)
        
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

        # 获取交易日期和合约信息
        dt = datetime.fromisoformat(bar_dict['datetime'])
        trade_date = dt.date()
        date_str = trade_date.strftime('%Y%m%d')
        symbol = bar_dict['symbol']
        exchange = bar_dict['exchange']
        contract_key = self._get_contract_key(symbol, exchange)
        
        # 确保表已创建
        self._create_contract_table('bar', symbol, exchange, trade_date)
        
        # 添加到按合约和日期分组的批量写入缓存
        self._add_to_contract_batch('bar', contract_key, date_str, trade_date, bar_dict)
        
        # 同时添加到Parquet缓冲区
        self._add_bar_to_parquet_buffer(bar_dict)
    
    async def save_bar_data_async(self, bar_data: BarData):
        """异步保存bar数据"""
        self.save_bar_data(bar_data)

    def query_tick_data(self, symbol: str, exchange: str,
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None,
                              limit: int = 1000) -> List[Dict[str, Any]]:
        """查询tick数据（跨日期数据库文件，按合约分表）"""
        try:
            # 确定查询的日期范围
            if start_time and end_time:
                date_range = self._get_date_range(start_time.date(), end_time.date())
            elif start_time:
                # 如果只有开始时间，查询从开始时间到今天
                date_range = self._get_date_range(start_time.date(), datetime.now().date())
            elif end_time:
                # 如果只有结束时间，查询最近30天到结束时间
                start_date = (end_time - timedelta(days=30)).date()
                date_range = self._get_date_range(start_date, end_time.date())
            else:
                # 如果没有时间限制，查询最近7天
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=7)
                date_range = self._get_date_range(start_date, end_date)
            
            all_results = []
            table_name = self._get_table_name('tick', symbol, exchange)
            
            for trade_date in date_range:
                db_path = self._get_db_path('tick', trade_date)
                if not db_path.exists():
                    continue
                
                conditions = ["data_type = ?"]
                params = ['tick']
                
                if start_time:
                    conditions.append("datetime >= ?")
                    params.append(start_time.isoformat())
                
                if end_time:
                    conditions.append("datetime <= ?")
                    params.append(end_time.isoformat())
                
                where_clause = f"WHERE {' AND '.join(conditions)}"
                sql = f'''
                    SELECT * FROM {table_name} 
                    {where_clause}
                    ORDER BY datetime DESC
                '''
                
                try:
                    with sqlite3.connect(str(db_path)) as conn:
                        # 检查表是否存在
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                        if not cursor.fetchone():
                            continue
                        
                        cursor = conn.execute(sql, params)
                        rows = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        results = [dict(zip(columns, row)) for row in rows]
                        # 为结果添加symbol和exchange信息
                        for result in results:
                            result['symbol'] = symbol
                            result['exchange'] = exchange
                        all_results.extend(results)
                except Exception as e:
                    logger.error(f"查询tick数据失败 {db_path}: {e}")
                    continue
            
            # 按时间排序并限制结果数量
            all_results.sort(key=lambda x: x['datetime'], reverse=True)
            return all_results[:limit]
            
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
        """查询bar数据（跨日期数据库文件，按合约分表）"""
        try:
            # 确定查询的日期范围
            if start_time and end_time:
                date_range = self._get_date_range(start_time.date(), end_time.date())
            elif start_time:
                # 如果只有开始时间，查询从开始时间到今天
                date_range = self._get_date_range(start_time.date(), datetime.now().date())
            elif end_time:
                # 如果只有结束时间，查询最近30天到结束时间
                start_date = (end_time - timedelta(days=30)).date()
                date_range = self._get_date_range(start_date, end_time.date())
            else:
                # 如果没有时间限制，查询最近7天
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=7)
                date_range = self._get_date_range(start_date, end_date)
            
            all_results = []
            table_name = self._get_table_name('bar', symbol, exchange)
            
            for trade_date in date_range:
                db_path = self._get_db_path('bar', trade_date)
                if not db_path.exists():
                    continue
                
                conditions = ["data_type = ?", "interval = ?"]
                params = ['bar', interval]
                
                if start_time:
                    conditions.append("datetime >= ?")
                    params.append(start_time.isoformat())
                
                if end_time:
                    conditions.append("datetime <= ?")
                    params.append(end_time.isoformat())
                
                where_clause = f"WHERE {' AND '.join(conditions)}"
                sql = f'''
                    SELECT * FROM {table_name} 
                    {where_clause}
                    ORDER BY datetime DESC
                '''
                
                try:
                    with sqlite3.connect(str(db_path)) as conn:
                        # 检查表是否存在
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                        if not cursor.fetchone():
                            continue
                        
                        cursor = conn.execute(sql, params)
                        rows = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        results = [dict(zip(columns, row)) for row in rows]
                        # 为结果添加symbol和exchange信息
                        for result in results:
                            result['symbol'] = symbol
                            result['exchange'] = exchange
                        all_results.extend(results)
                except Exception as e:
                    logger.error(f"查询bar数据失败 {db_path}: {e}")
                    continue
            
            # 按时间排序并限制结果数量
            all_results.sort(key=lambda x: x['datetime'], reverse=True)
            return all_results[:limit]
            
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
                # 刷新所有合约的tick批次
                for contract_key in list(self._tick_batches.keys()):
                    for date_str in list(self._tick_batches[contract_key].keys()):
                        if self._tick_batches[contract_key][date_str]:
                            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
                            self._flush_contract_batch('tick', contract_key, date_str, trade_date)
                
                # 刷新所有合约的bar批次
                for contract_key in list(self._bar_batches.keys()):
                    for date_str in list(self._bar_batches[contract_key].keys()):
                        if self._bar_batches[contract_key][date_str]:
                            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
                            self._flush_contract_batch('bar', contract_key, date_str, trade_date)
                        
            except Exception as e:
                logger.error(f"批量刷新失败: {e}")



    def _add_to_contract_batch(self, data_type: str, contract_key: str, date_str: str, trade_date: date, data: Dict[str, Any]):
        """添加数据到按合约和日期分组的批量写入缓存"""
        with self._batch_lock:
            if data_type == 'tick':
                if contract_key not in self._tick_batches:
                    self._tick_batches[contract_key] = defaultdict(list)
                self._tick_batches[contract_key][date_str].append(data)
                batch_size = len(self._tick_batches[contract_key][date_str])
                threshold = self.tick_batch_size
            else:  # bar
                if contract_key not in self._bar_batches:
                    self._bar_batches[contract_key] = defaultdict(list)
                self._bar_batches[contract_key][date_str].append(data)
                batch_size = len(self._bar_batches[contract_key][date_str])
                threshold = self.bar_batch_size
            
            # 检查是否需要刷新该合约和日期的批次
            if batch_size >= threshold:
                self._flush_contract_batch(data_type, contract_key, date_str, trade_date)
    
    def _flush_contract_batch(self, data_type: str, contract_key: str, date_str: str, trade_date: date):
        """刷新指定合约和日期的批次数据"""
        try:
            # 解析合约信息
            symbol, exchange = contract_key.split('_', 1)
            
            if data_type == 'tick':
                batch_data = self._tick_batches[contract_key][date_str]
                if not batch_data:
                    return
                
                # 确保表已创建
                self._create_contract_table('tick', symbol, exchange, trade_date)
                
                # 获取表名和数据库路径
                table_name = self._get_table_name('tick', symbol, exchange)
                db_path = self._get_db_path('tick', trade_date)
                
                with sqlite3.connect(str(db_path)) as conn:
                    conn.executemany(f'''
                        INSERT OR REPLACE INTO {table_name} (
                            data_type, datetime, last_price, volume, turnover, open_interest,
                            bid_price_1, ask_price_1, bid_volume_1, ask_volume_1
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [(
                        'tick', d['datetime'], d['last_price'], d['volume'], d['turnover'],
                        d['open_interest'], d['bid_price_1'], d['ask_price_1'], d['bid_volume_1'], d['ask_volume_1']
                    ) for d in batch_data])
                    conn.commit()
                
                # 清空该合约和日期的批次
                self._tick_batches[contract_key][date_str].clear()
                logger.debug(f"Tick数据批量写入完成: {contract_key}, {date_str}, 共{len(batch_data)}条")
                
            else:  # bar
                batch_data = self._bar_batches[contract_key][date_str]
                if not batch_data:
                    return
                
                # 确保表已创建
                self._create_contract_table('bar', symbol, exchange, trade_date)
                
                # 获取表名和数据库路径
                table_name = self._get_table_name('bar', symbol, exchange)
                db_path = self._get_db_path('bar', trade_date)
                
                with sqlite3.connect(str(db_path)) as conn:
                    conn.executemany(f'''
                        INSERT OR REPLACE INTO {table_name} (
                            data_type, interval, datetime, open_price, high_price, low_price, close_price,
                            volume, turnover, open_interest
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [(
                        'bar', d['interval'], d['datetime'], d['open_price'], d['high_price'],
                        d['low_price'], d['close_price'], d['volume'], d['turnover'], d['open_interest']
                    ) for d in batch_data])
                    conn.commit()
                
                # 清空该合约和日期的批次
                self._bar_batches[contract_key][date_str].clear()
                logger.debug(f"Bar数据批量写入完成: {contract_key}, {date_str}, 共{len(batch_data)}条")
                
        except Exception as e:
            logger.error(f"{data_type}数据批量写入失败 {contract_key}, {date_str}: {e}")

    def _execute_direct_sql(self, sql_data):
        try:
            sql = sql_data.get('sql')
            params = sql_data.get('params', [])
            db_type = sql_data.get('db_type', 'tick')  # 默认为tick数据库
            trade_date = sql_data.get('trade_date', datetime.now().date())
            
            if not sql:
                logger.error("未提供SQL语句")
                return
            
            # 根据数据库类型获取路径
            db_path = self._get_db_path(db_type, trade_date)
            
            with sqlite3.connect(str(db_path)) as conn:
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
            # 按日期和合约分组
            date_symbol_groups = {}
            for data in self._tick_parquet_buffer:
                dt = datetime.fromisoformat(data['datetime'])
                date_str = dt.strftime('%Y%m%d')
                symbol = data['symbol']
                
                if date_str not in date_symbol_groups:
                    date_symbol_groups[date_str] = {}
                if symbol not in date_symbol_groups[date_str]:
                    date_symbol_groups[date_str][symbol] = []
                
                date_symbol_groups[date_str][symbol].append(data)
            
            # 分别写入每个日期和合约的文件
            for date_str, symbol_groups in date_symbol_groups.items():
                # 创建日期目录
                date_dir = self.parquet_base_path / "tick_parquet" / date_str
                date_dir.mkdir(parents=True, exist_ok=True)
                
                for symbol, symbol_data in symbol_groups.items():
                    df = pd.DataFrame(symbol_data)
                    file_path = date_dir / f"{symbol}.parquet"
                    
                    # 如果文件已存在，追加数据
                    if file_path.exists():
                        try:
                            # 尝试读取现有文件，如果失败则备份并重新创建
                            existing_df = pd.read_parquet(file_path)
                            df = pd.concat([existing_df, df], ignore_index=True)
                            # 去重并排序
                            df = df.drop_duplicates(subset=['symbol', 'exchange', 'datetime']).sort_values('datetime')
                        except Exception as read_error:
                            logger.warning(f"读取现有Parquet文件失败 {file_path}: {read_error}，将备份并重新创建")
                            # 备份损坏的文件
                            backup_path = file_path.with_suffix(f'.backup_{int(time.time())}.parquet')
                            try:
                                file_path.rename(backup_path)
                                logger.info(f"损坏文件已备份到: {backup_path}")
                            except Exception as backup_error:
                                logger.error(f"备份文件失败: {backup_error}")
                                # 如果备份失败，直接删除损坏文件
                                try:
                                    file_path.unlink()
                                    logger.info(f"已删除损坏文件: {file_path}")
                                except Exception as delete_error:
                                    logger.error(f"删除损坏文件失败: {delete_error}")
                            # 使用新数据创建文件
                    
                    # 写入文件（使用临时文件确保原子性）
                    temp_path = file_path.with_suffix('.tmp')
                    try:
                        df.to_parquet(temp_path, compression=self.parquet_compression, index=False)
                        # 原子性移动临时文件到目标位置
                        temp_path.replace(file_path)
                    except Exception as write_error:
                        logger.error(f"写入Parquet文件失败 {file_path}: {write_error}")
                        # 清理临时文件
                        if temp_path.exists():
                            temp_path.unlink()
                        raise
            
            buffer_count = len(self._tick_parquet_buffer)
            self._tick_parquet_buffer.clear()
            logger.debug(f"Tick Parquet数据写入完成，共{buffer_count}条")
            
        except Exception as e:
            logger.error(f"Tick Parquet写入失败: {e}")
            # 不清空缓冲区，让数据在下次尝试时重新写入
            # self._tick_parquet_buffer.clear()
    
    def _flush_bar_parquet_buffer(self):
        """刷新bar数据Parquet缓冲区"""
        if not self._bar_parquet_buffer:
            return
        
        try:
            # 按日期和合约分组
            date_symbol_groups = {}
            for data in self._bar_parquet_buffer:
                dt = datetime.fromisoformat(data['datetime'])
                date_str = dt.strftime('%Y%m%d')
                symbol = data['symbol']
                
                if date_str not in date_symbol_groups:
                    date_symbol_groups[date_str] = {}
                if symbol not in date_symbol_groups[date_str]:
                    date_symbol_groups[date_str][symbol] = []
                
                date_symbol_groups[date_str][symbol].append(data)
            
            # 分别写入每个日期和合约的文件
            for date_str, symbol_groups in date_symbol_groups.items():
                # 创建日期目录
                date_dir = self.parquet_base_path / "bar_parquet" / date_str
                date_dir.mkdir(parents=True, exist_ok=True)
                
                for symbol, symbol_data in symbol_groups.items():
                    df = pd.DataFrame(symbol_data)
                    file_path = date_dir / f"{symbol}.parquet"
                    
                    # 如果文件已存在，追加数据
                    if file_path.exists():
                        try:
                            # 尝试读取现有文件，如果失败则备份并重新创建
                            existing_df = pd.read_parquet(file_path)
                            df = pd.concat([existing_df, df], ignore_index=True)
                            # 去重并排序
                            df = df.drop_duplicates(subset=['symbol', 'exchange', 'interval', 'datetime']).sort_values('datetime')
                        except Exception as read_error:
                            logger.warning(f"读取现有Parquet文件失败 {file_path}: {read_error}，将备份并重新创建")
                            # 备份损坏的文件
                            backup_path = file_path.with_suffix(f'.backup_{int(time.time())}.parquet')
                            try:
                                file_path.rename(backup_path)
                                logger.info(f"损坏文件已备份到: {backup_path}")
                            except Exception as backup_error:
                                logger.error(f"备份文件失败: {backup_error}")
                                # 如果备份失败，直接删除损坏文件
                                try:
                                    file_path.unlink()
                                    logger.info(f"已删除损坏文件: {file_path}")
                                except Exception as delete_error:
                                    logger.error(f"删除损坏文件失败: {delete_error}")
                            # 使用新数据创建文件
                    
                    # 写入文件（使用临时文件确保原子性）
                    temp_path = file_path.with_suffix('.tmp')
                    try:
                        df.to_parquet(temp_path, compression=self.parquet_compression, index=False)
                        # 原子性移动临时文件到目标位置
                        temp_path.replace(file_path)
                    except Exception as write_error:
                        logger.error(f"写入Parquet文件失败 {file_path}: {write_error}")
                        # 清理临时文件
                        if temp_path.exists():
                            temp_path.unlink()
                        raise
            
            buffer_count = len(self._bar_parquet_buffer)
            self._bar_parquet_buffer.clear()
            logger.debug(f"Bar Parquet数据写入完成，共{buffer_count}条")
            
        except Exception as e:
            logger.error(f"Bar Parquet写入失败: {e}")
            # 不清空缓冲区，让数据在下次尝试时重新写入
            # self._bar_parquet_buffer.clear()
    
    def _get_date_range(self, start_date: date, end_date: date) -> List[date]:
        """获取日期范围内的所有日期"""
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        return date_list
