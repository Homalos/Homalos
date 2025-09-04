#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : data_center_database
@Date       : 2025/7/23 00:06
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

import polars as pl

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

        # CSV配置
        csv_config = config.get("csv", {})
        self.csv_base_path = Path(csv_config.get("base_path", "data"))
        self.csv_cache_size = 100  # 缓存100条数据后写入CSV

        # 批量写入配置
        batch_write_config = config.get("batch_write", {})
        self.tick_batch_size = batch_write_config.get("tick", {}).get("batch_size", 1000)
        self.tick_flush_interval = batch_write_config.get("tick", {}).get("flush_interval", 5)
        self.bar_batch_size = batch_write_config.get("bar", {}).get("batch_size", 500)
        self.bar_flush_interval = batch_write_config.get("bar", {}).get("flush_interval", 10)
        self.flush_interval = self.tick_flush_interval

        # 按合约和日期分组的批量写入缓存
        self._tick_batches = defaultdict(lambda: defaultdict(list))  # {date_str: {contract_key: [data_list]}}
        self._bar_batches = defaultdict(lambda: defaultdict(list))  # {date_str: {contract_key: [data_list]}}
        self._batch_lock = threading.Lock()

        # CSV缓存
        self._tick_csv_buffer: List[Dict[str, Any]] = []
        self._bar_csv_buffer: List[Dict[str, Any]] = []
        self._csv_lock = threading.Lock()

        # 表缓存 - 记录已创建的表
        self._created_tables = set()  # {(data_type, date_str, table_name)}
        self._table_cache_lock = threading.Lock()

        # 后台写入线程
        self._write_queue = Queue()
        self._write_thread = None
        self._csv_thread = None
        self._running = False

        self._init_database_dirs()
        self._init_csv_storage()

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

    @staticmethod
    def _get_contract_key(symbol: str, exchange: str) -> str:
        """生成合约唯一标识"""
        return f"{symbol}_{exchange}"

    @staticmethod
    def _get_table_name(data_type: str, symbol: str, exchange: str) -> str:
        """生成表名 - 直接使用合约名作为表名"""
        # 直接使用合约名作为表名，不再添加前缀
        return symbol

    def _create_tick_table(self, symbol: str, exchange: str, trade_date: date):
        """为指定合约创建tick数据表"""
        db_path = self._get_db_path('tick', trade_date)
        table_name = self._get_table_name('tick', symbol, exchange)
        date_str = trade_date.strftime('%Y%m%d')

        # 检查表是否已创建
        table_key = ('tick', date_str, table_name)
        with self._table_cache_lock:
            if table_key in self._created_tables:
                return

        try:
            with sqlite3.connect(str(db_path), timeout=self.tick_db_config.get('timeout', 30)) as conn:
                # 根据配置启用WAL模式
                if self.tick_db_config.get('wal_mode', True):
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                else:
                    conn.execute("PRAGMA journal_mode=DELETE")
                    conn.execute("PRAGMA synchronous=FULL")

                # 设置缓存大小
                cache_size = self.tick_db_config.get('cache_size', 10000)
                if cache_size > 0:
                    conn.execute(f"PRAGMA cache_size=-{cache_size}")  # 负数表示KB
                else:
                    conn.execute(f"PRAGMA cache_size={cache_size}")  # 正数表示页数

                # 创建tick数据表（深度市场行情字段）
                conn.execute(f'''
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        InstrumentID TEXT,
                        ExchangeID TEXT,
                        TradingDay TEXT,
                        UpdateTime TEXT,
                        UpdateMillisec INTEGER,
                        PreSettlementPrice REAL,
                        PreClosePrice REAL,
                        PreOpenInterest REAL,
                        OpenPrice REAL,
                        ClosePrice REAL,
                        SettlementPrice REAL,
                        UpperLimitPrice REAL,
                        LowerLimitPrice REAL,
                        HighestPrice REAL,
                        LowestPrice REAL,
                        LastPrice REAL,
                        Volume REAL,
                        LastVolume REAL,
                        Turnover REAL,
                        OpenInterest REAL,
                        LastOpenInterest REAL,
                        BidPrice1 REAL,
                        BidVolume1 REAL,
                        AskPrice1 REAL,
                        AskVolume1 REAL,
                        BidPrice2 REAL,
                        BidVolume2 REAL,
                        AskPrice2 REAL,
                        AskVolume2 REAL,
                        BidPrice3 REAL,
                        BidVolume3 REAL,
                        AskPrice3 REAL,
                        AskVolume3 REAL,
                        BidPrice4 REAL,
                        BidVolume4 REAL,
                        AskPrice4 REAL,
                        AskVolume4 REAL,
                        BidPrice5 REAL,
                        BidVolume5 REAL,
                        AskPrice5 REAL,
                        AskVolume5 REAL,
                        AveragePrice REAL
                    )
                ''')

                # 创建索引以提高查询性能
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_update_time ON {table_name}(UpdateTime)')
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_last_price ON {table_name}(LastPrice)')
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_volume ON {table_name}(Volume)')

                conn.commit()

                # 标记表已创建
                with self._table_cache_lock:
                    self._created_tables.add(table_key)

                logger.debug(f"tick表创建完成 - 合约: {symbol}.{exchange}, 表名: {table_name}, 日期: {trade_date}")

        except Exception as e:
            logger.error(f"创建tick表失败 - 合约: {symbol}.{exchange}, 日期: {trade_date}, 错误: {e}")
            raise

    def _create_bar_table(self, symbol: str, exchange: str, bar_type: str, trade_date: date):
        """为指定合约和时间周期创建bar数据表"""
        db_path = self._get_db_path('bar', trade_date)
        table_name = f"{symbol}_{bar_type}"
        date_str = trade_date.strftime('%Y%m%d')

        # 检查表是否已创建
        table_key = ('bar', date_str, table_name)
        with self._table_cache_lock:
            if table_key in self._created_tables:
                return

        try:
            with sqlite3.connect(str(db_path), timeout=self.bar_db_config.get('timeout', 30)) as conn:
                # 根据配置启用WAL模式
                if self.bar_db_config.get('wal_mode', True):
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                else:
                    conn.execute("PRAGMA journal_mode=DELETE")
                    conn.execute("PRAGMA synchronous=FULL")

                # 设置缓存大小
                cache_size = self.bar_db_config.get('cache_size', 10000)
                if cache_size > 0:
                    conn.execute(f"PRAGMA cache_size=-{cache_size}")  # 负数表示KB
                else:
                    conn.execute(f"PRAGMA cache_size={cache_size}")  # 正数表示页数

                # 创建bar数据表
                conn.execute(f'''
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        BarType TEXT,
                        UpdateTime TEXT,
                        InstrumentID TEXT,
                        Volume REAL,
                        OpenInterest REAL,
                        OpenPrice REAL,
                        HighestPrice REAL,
                        LowestPrice REAL,
                        ClosePrice REAL,
                        LastVolume REAL
                    )
                ''')

                # 创建索引以提高查询性能
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_update_time ON {table_name}(UpdateTime)')
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_close_price ON {table_name}(ClosePrice)')
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_volume ON {table_name}(Volume)')

                conn.commit()

                # 标记表已创建
                with self._table_cache_lock:
                    self._created_tables.add(table_key)

                logger.debug(f"bar表创建完成 - 合约: {symbol}.{exchange}, 表名: {table_name}, 日期: {trade_date}")

        except Exception as e:
            logger.error(f"创建bar表失败 - 合约: {symbol}.{exchange}, 日期: {trade_date}, 错误: {e}")
            raise

    def _init_csv_storage(self):
        """初始化CSV存储"""
        try:
            # 确保CSV目录存在
            self.csv_base_path.mkdir(parents=True, exist_ok=True)

            # 创建主目录
            (self.csv_base_path / "tick_csv").mkdir(exist_ok=True)
            (self.csv_base_path / "bar_csv").mkdir(exist_ok=True)

            logger.info(f"CSV存储初始化成功: {self.csv_base_path}")

        except Exception as e:
            logger.error(f"CSV存储初始化失败: {e}")
            raise

    def start(self):
        """启动后台写入线程"""
        if self._running:
            return

        self._running = True

        # 启动SQLite写入线程
        self._write_thread = threading.Thread(target=self._background_writer, daemon=True)
        self._write_thread.start()

        # 启动CSV写入线程
        self._csv_thread = threading.Thread(target=self._background_csv_writer, daemon=True)
        self._csv_thread.start()

        logger.info("数据库写入线程已启动（SQLite + CSV）")

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
        self._flush_all_csv_buffers()

        logger.info("数据库写入线程已停止（SQLite + CSV）")

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
                'csv_path': str(self.csv_base_path),
                'tick_batch_size': total_tick_batch_size,
                'bar_batch_size': total_bar_batch_size,
                'tick_batches_by_contract': tick_batches_by_contract,
                'bar_batches_by_contract': bar_batches_by_contract,
                'created_tables_count': len(self._created_tables),
                'tick_csv_buffer_size': len(self._tick_csv_buffer),
                'bar_csv_buffer_size': len(self._bar_csv_buffer),
                'write_queue_size': self._write_queue.qsize(),
                'write_thread_alive': self._write_thread.is_alive() if self._write_thread else False,
                'csv_thread_alive': self._csv_thread.is_alive() if self._csv_thread else False
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

    def _background_csv_writer(self):
        """CSV后台写入线程"""
        last_flush = time.time()

        while self._running:
            try:
                # 检查是否需要定时刷新
                current_time = time.time()
                if current_time - last_flush >= max(self.tick_flush_interval, self.bar_flush_interval):
                    self._flush_all_csv_buffers()
                    last_flush = current_time

                time.sleep(1)

            except Exception as e:
                logger.error(f"CSV后台写入线程异常: {e}")
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
                self._create_tick_table(symbol, exchange, trade_date)

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
                # 从第一个数据项获取bar_type
                bar_type = data.get('BarType', 'min1')
                self._create_bar_table(symbol, exchange, bar_type, trade_date)

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
                # 深度市场行情字段
                'TradingDay': tick_data.trading_day,
                'InstrumentID': tick_data.instrument_id,
                'ExchangeID': tick_data.exchange.value,
                'ExchangeInstID': tick_data.exchange_inst_id,
                'LastPrice': tick_data.last_price,
                'PreSettlementPrice': tick_data.pre_settlement_price,
                'PreClosePrice': tick_data.pre_close_price,
                'PreOpenInterest': tick_data.pre_open_interest,
                'OpenPrice': tick_data.open_price,
                'HighestPrice': tick_data.highest_price,
                'LowestPrice': tick_data.lowest_price,
                'Volume': tick_data.volume,
                'Turnover': tick_data.turnover,
                'OpenInterest': tick_data.open_interest,
                'ClosePrice': tick_data.close_price,
                'SettlementPrice': tick_data.settlement_price,
                'UpperLimitPrice': tick_data.upper_limit_price,
                'LowerLimitPrice': tick_data.lower_limit_price,
                'PreDelta': tick_data.pre_delta,
                'CurrDelta': tick_data.curr_delta,
                'UpdateTime': tick_data.update_time,
                'UpdateMillisec': tick_data.update_millisec,
                'BidPrice1': tick_data.bid_price_1,
                'BidVolume1': tick_data.bid_volume_1,
                'AskPrice1': tick_data.ask_price_1,
                'AskVolume1': tick_data.ask_volume_1,
                'BidPrice2': tick_data.bid_price_2,
                'BidVolume2': tick_data.bid_volume_2,
                'AskPrice2': tick_data.ask_price_2,
                'AskVolume2': tick_data.ask_volume_2,
                'BidPrice3': tick_data.bid_price_3,
                'BidVolume3': tick_data.bid_volume_3,
                'AskPrice3': tick_data.ask_price_3,
                'AskVolume3': tick_data.ask_volume_3,
                'BidPrice4': tick_data.bid_price_4,
                'BidVolume4': tick_data.bid_volume_4,
                'AskPrice4': tick_data.ask_price_4,
                'AskVolume4': tick_data.ask_volume_4,
                'BidPrice5': tick_data.bid_price_5,
                'BidVolume5': tick_data.bid_volume_5,
                'AskPrice5': tick_data.ask_price_5,
                'AskVolume5': tick_data.ask_volume_5,
                'AveragePrice': tick_data.average_price,
                'ActionDay': tick_data.action_day,
                'BandingUpperPrice': tick_data.banding_upper_price,
                'BandingLowerPrice': tick_data.banding_lower_price,

                # 保留用于内部处理的字段
                'symbol': tick_data.symbol,
                'exchange': tick_data.exchange.value if hasattr(tick_data.exchange, 'value') else str(
                    tick_data.exchange),
                'datetime': tick_data.datetime
            }
        else:  # 字典格式
            tick_dict = tick_data.copy()
            # 处理枚举值转换
            if 'exchange' in tick_dict and hasattr(tick_dict['exchange'], 'value'):
                tick_dict['exchange'] = tick_dict['exchange'].value

        # 获取交易日期和合约信息
        dt = tick_dict['datetime']
        trade_date = tick_dict['trading_day']
        date_str = trade_date.strftime('%Y%m%d')
        symbol = tick_dict['symbol']
        exchange = tick_dict['exchange']
        contract_key = self._get_contract_key(symbol, exchange)

        # 确保表已创建
        self._create_tick_table(symbol, exchange, trade_date)

        # 添加到按合约和日期分组的批量写入缓存
        self._add_to_contract_batch('tick', contract_key, date_str, trade_date, tick_dict)

        # 同时添加到CSV缓冲区
        self._add_tick_to_csv_buffer(tick_dict)

    async def save_tick_data_async(self, tick_data: TickData):
        """异步保存tick数据"""
        self.save_tick_data(tick_data)

    def save_bar_data(self, bar_data, bar_type='min1'):
        """保存bar数据（同步版本）"""
        # 支持BarData对象和字典两种格式
        if hasattr(bar_data, 'symbol'):  # BarData对象
            # 从datetime中提取UpdateTime（保持完整的ISO格式用于CSV）
            update_time = bar_data.datetime

            # 从interval属性获取bar_type，如果没有则使用传入的bar_type
            if hasattr(bar_data, 'interval') and bar_data.interval:
                if hasattr(bar_data.interval, 'value'):
                    bar_type = bar_data.interval.value
                else:
                    bar_type = str(bar_data.interval)

            bar_dict = {
                'BarType': bar_type,
                'UpdateTime': update_time,
                'InstrumentID': bar_data.symbol,
                'Volume': bar_data.volume,
                'OpenInterest': bar_data.open_interest,
                'OpenPrice': bar_data.open_price,
                'HighestPrice': bar_data.high_price,
                'LowestPrice': bar_data.low_price,
                'ClosePrice': bar_data.close_price,
                'LastVolume': getattr(bar_data, 'last_volume', 0.0),

                # 保留用于内部处理的字段
                'symbol': bar_data.symbol,
                'exchange': bar_data.exchange.value if hasattr(bar_data.exchange, 'value') else str(bar_data.exchange),
                'datetime': str(bar_data.datetime)
            }
        else:  # 字典格式
            bar_dict = bar_data.copy()
            # 处理枚举值转换
            if 'exchange' in bar_dict and hasattr(bar_dict['exchange'], 'value'):
                bar_dict['exchange'] = bar_dict['exchange'].value

            # 重新构建bar_dict以符合新的表结构
            new_bar_dict = {
                'BarType': bar_type,
                'UpdateTime': bar_dict.get('datetime', ''),
                'InstrumentID': bar_dict.get('symbol', ''),
                'Volume': bar_dict.get('volume', 0.0),
                'OpenInterest': bar_dict.get('open_interest', 0.0),
                'OpenPrice': bar_dict.get('open_price', 0.0),
                'HighestPrice': bar_dict.get('high_price', 0.0),
                'LowestPrice': bar_dict.get('low_price', 0.0),
                'ClosePrice': bar_dict.get('close_price', 0.0),
                'LastVolume': bar_dict.get('last_volume', 0.0),

                # 保留用于内部处理的字段
                'symbol': bar_dict.get('symbol', ''),
                'exchange': bar_dict.get('exchange', ''),
                'datetime': bar_dict.get('datetime', '')
            }
            bar_dict = new_bar_dict

        # 获取交易日期和合约信息
        dt = bar_dict['datetime']
        trade_date = bar_dict['trading_day']
        date_str = trade_date.strftime('%Y%m%d')
        symbol = bar_dict['symbol']
        exchange = bar_dict['exchange']
        contract_key = self._get_contract_key(symbol, exchange)

        # 确保表已创建
        self._create_bar_table(symbol, exchange, bar_type, trade_date)

        # 添加到按合约和日期分组的批量写入缓存
        self._add_to_contract_batch('bar', contract_key, date_str, trade_date, bar_dict)

        # 同时添加到CSV缓冲区
        self._add_bar_to_csv_buffer(bar_dict)

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

                conditions = []
                params = []

                if start_time:
                    conditions.append("UpdateTime >= ? AND UpdateMillisec >= ?")
                    params.extend([start_time.strftime('%H:%M:%S'), start_time.microsecond // 1000])

                if end_time:
                    conditions.append("UpdateTime <= ? AND UpdateMillisec <= ?")
                    params.extend([end_time.strftime('%H:%M:%S'), end_time.microsecond // 1000])

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                sql = f'''
                    SELECT * FROM {table_name} 
                    {where_clause}
                    ORDER BY UpdateTime DESC, UpdateMillisec DESC
                '''

                try:
                    with sqlite3.connect(str(db_path)) as conn:
                        # 检查表是否存在
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                                              (table_name,))
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
            all_results.sort(key=lambda x: (x['UpdateTime'], x['UpdateMillisec']), reverse=True)
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
            # 将interval转换为BarType格式
            bar_type = interval.replace('m', 'min')  # 例如：1m -> min1, 3m -> min3

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
            table_name = f"{symbol}_{bar_type}"  # 新的表名格式

            for trade_date in date_range:
                db_path = self._get_db_path('bar', trade_date)
                if not db_path.exists():
                    continue

                conditions = ["BarType = ?"]
                params = [bar_type]

                if start_time:
                    conditions.append("UpdateTime >= ?")
                    params.append(start_time.strftime('%H:%M:%S'))

                if end_time:
                    conditions.append("UpdateTime <= ?")
                    params.append(end_time.strftime('%H:%M:%S'))

                where_clause = f"WHERE {' AND '.join(conditions)}"
                sql = f'''
                    SELECT * FROM {table_name} 
                    {where_clause}
                    ORDER BY UpdateTime DESC
                '''

                try:
                    with sqlite3.connect(str(db_path)) as conn:
                        # 检查表是否存在
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                                              (table_name,))
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
            all_results.sort(key=lambda x: x['UpdateTime'], reverse=True)
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

    def _add_to_contract_batch(self, data_type: str, contract_key: str, date_str: str, trade_date: date,
                               data: Dict[str, Any]):
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
                self._create_tick_table(symbol, exchange, trade_date)

                # 获取表名和数据库路径
                table_name = self._get_table_name('tick', symbol, exchange)
                db_path = self._get_db_path('tick', trade_date)

                with sqlite3.connect(str(db_path)) as conn:
                    conn.executemany(f'''
                        INSERT OR REPLACE INTO {table_name} (
                            InstrumentID, ExchangeID, TradingDay, UpdateTime, UpdateMillisec,
                            PreSettlementPrice, PreClosePrice, PreOpenInterest, OpenPrice, ClosePrice,
                            SettlementPrice, UpperLimitPrice, LowerLimitPrice, HighestPrice, LowestPrice,
                            LastPrice, Volume, LastVolume, Turnover, OpenInterest, LastOpenInterest,
                            BidPrice1, BidVolume1, AskPrice1, AskVolume1,
                            BidPrice2, BidVolume2, AskPrice2, AskVolume2,
                            BidPrice3, BidVolume3, AskPrice3, AskVolume3,
                            BidPrice4, BidVolume4, AskPrice4, AskVolume4,
                            BidPrice5, BidVolume5, AskPrice5, AskVolume5,
                            AveragePrice
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [(
                        d.get('InstrumentID', d.get('symbol', '')),
                        d.get('ExchangeID', d.get('exchange', '')),
                        d.get('TradingDay', ''),
                        d.get('UpdateTime', ''),
                        d.get('UpdateMillisec', 0),
                        d.get('PreSettlementPrice', 0.0),
                        d.get('PreClosePrice', 0.0),
                        d.get('PreOpenInterest', 0.0),
                        d.get('OpenPrice', 0.0),
                        d.get('ClosePrice', 0.0),
                        d.get('SettlementPrice', 0.0),
                        d.get('UpperLimitPrice', 0.0),
                        d.get('LowerLimitPrice', 0.0),
                        d.get('HighestPrice', 0.0),
                        d.get('LowestPrice', 0.0),
                        d.get('LastPrice', d.get('last_price', 0.0)),
                        d.get('Volume', d.get('volume', 0.0)),
                        d.get('LastVolume', 0.0),
                        d.get('Turnover', d.get('turnover', 0.0)),
                        d.get('OpenInterest', d.get('open_interest', 0.0)),
                        d.get('LastOpenInterest', 0.0),
                        d.get('BidPrice1', d.get('bid_price_1', 0.0)),
                        d.get('BidVolume1', d.get('bid_volume_1', 0.0)),
                        d.get('AskPrice1', d.get('ask_price_1', 0.0)),
                        d.get('AskVolume1', d.get('ask_volume_1', 0.0)),
                        d.get('BidPrice2', 0.0),
                        d.get('BidVolume2', 0.0),
                        d.get('AskPrice2', 0.0),
                        d.get('AskVolume2', 0.0),
                        d.get('BidPrice3', 0.0),
                        d.get('BidVolume3', 0.0),
                        d.get('AskPrice3', 0.0),
                        d.get('AskVolume3', 0.0),
                        d.get('BidPrice4', 0.0),
                        d.get('BidVolume4', 0.0),
                        d.get('AskPrice4', 0.0),
                        d.get('AskVolume4', 0.0),
                        d.get('BidPrice5', 0.0),
                        d.get('BidVolume5', 0.0),
                        d.get('AskPrice5', 0.0),
                        d.get('AskVolume5', 0.0),
                        d.get('AveragePrice', 0.0)
                    ) for d in batch_data])
                    conn.commit()

                # 清空该合约和日期的批次
                self._tick_batches[contract_key][date_str].clear()
                logger.debug(f"Tick数据批量写入完成: {contract_key}, {date_str}, 共{len(batch_data)}条")

            else:  # bar
                batch_data = self._bar_batches[contract_key][date_str]
                if not batch_data:
                    return

                # 从第一个数据项获取bar_type
                bar_type = batch_data[0].get('BarType', 'min1') if batch_data else 'min1'

                # 确保表已创建
                self._create_bar_table(symbol, exchange, bar_type, trade_date)

                # 获取表名和数据库路径
                table_name = f"{symbol}_{bar_type}"
                db_path = self._get_db_path('bar', trade_date)

                with sqlite3.connect(str(db_path)) as conn:
                    conn.executemany(f'''
                        INSERT OR REPLACE INTO {table_name} (
                            BarType, UpdateTime, InstrumentID, Volume, OpenInterest,
                            OpenPrice, HighestPrice, LowestPrice, ClosePrice, LastVolume
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [(
                        d.get('BarType', 'min1'),
                        d.get('UpdateTime', ''),
                        d.get('InstrumentID', ''),
                        d.get('Volume', 0.0),
                        d.get('OpenInterest', 0.0),
                        d.get('OpenPrice', 0.0),
                        d.get('HighestPrice', 0.0),
                        d.get('LowestPrice', 0.0),
                        d.get('ClosePrice', 0.0),
                        d.get('LastVolume', 0.0)
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

    def _add_tick_to_csv_buffer(self, data: Dict[str, Any]):
        """添加tick数据到CSV缓冲区"""
        with self._csv_lock:
            self._tick_csv_buffer.append(data)
            if len(self._tick_csv_buffer) >= self.csv_cache_size:
                self._flush_tick_csv_buffer()

    def _add_bar_to_csv_buffer(self, data: Dict[str, Any]):
        """添加bar数据到CSV缓冲区"""
        with self._csv_lock:
            self._bar_csv_buffer.append(data)
            if len(self._bar_csv_buffer) >= self.csv_cache_size:
                self._flush_bar_csv_buffer()

    def _flush_all_csv_buffers(self):
        """刷新所有CSV缓冲区"""
        with self._csv_lock:
            try:
                if self._tick_csv_buffer:
                    self._flush_tick_csv_buffer()
                if self._bar_csv_buffer:
                    self._flush_bar_csv_buffer()
            except Exception as e:
                logger.error(f"CSV批量刷新失败: {e}")

    def _flush_tick_csv_buffer(self):
        """刷新tick数据CSV缓冲区"""
        if not self._tick_csv_buffer:
            return

        try:
            # 按日期和合约分组
            date_symbol_groups = {}
            for data in self._tick_csv_buffer:
                dt = datetime.fromisoformat(data['UpdateTime'])
                date_str = dt.strftime('%Y%m%d')
                symbol = data['InstrumentID']

                if date_str not in date_symbol_groups:
                    date_symbol_groups[date_str] = {}
                if symbol not in date_symbol_groups[date_str]:
                    date_symbol_groups[date_str][symbol] = []

                date_symbol_groups[date_str][symbol].append(data)

            # 分别写入每个日期和合约的文件
            for date_str, symbol_groups in date_symbol_groups.items():
                # 创建日期目录
                date_dir = self.csv_base_path / "tick_csv" / date_str
                date_dir.mkdir(parents=True, exist_ok=True)

                for symbol, symbol_data in symbol_groups.items():
                    # 创建新的DataFrame，明确指定数据类型
                    df = pl.DataFrame(symbol_data, schema_overrides={
                        'InstrumentID': pl.Utf8,
                        'ExchangeID': pl.Utf8,
                        'TradingDay': pl.Utf8,
                        'UpdateTime': pl.Utf8,
                        'UpdateMillisec': pl.Int64,
                        'PreSettlementPrice': pl.Float64,
                        'PreClosePrice': pl.Float64,
                        'PreOpenInterest': pl.Float64,
                        'OpenPrice': pl.Float64,
                        'ClosePrice': pl.Float64,
                        'SettlementPrice': pl.Float64,
                        'UpperLimitPrice': pl.Float64,
                        'LowerLimitPrice': pl.Float64,
                        'HighestPrice': pl.Float64,
                        'LowestPrice': pl.Float64,
                        'LastPrice': pl.Float64,
                        'Volume': pl.Float64,
                        'LastVolume': pl.Float64,
                        'Turnover': pl.Float64,
                        'OpenInterest': pl.Float64,
                        'LastOpenInterest': pl.Float64,
                        'BidPrice1': pl.Float64,
                        'BidVolume1': pl.Float64,
                        'AskPrice1': pl.Float64,
                        'AskVolume1': pl.Float64,
                        'BidPrice2': pl.Float64,
                        'BidVolume2': pl.Float64,
                        'AskPrice2': pl.Float64,
                        'AskVolume2': pl.Float64,
                        'BidPrice3': pl.Float64,
                        'BidVolume3': pl.Float64,
                        'AskPrice3': pl.Float64,
                        'AskVolume3': pl.Float64,
                        'BidPrice4': pl.Float64,
                        'BidVolume4': pl.Float64,
                        'AskPrice4': pl.Float64,
                        'AskVolume4': pl.Float64,
                        'BidPrice5': pl.Float64,
                        'BidVolume5': pl.Float64,
                        'AskPrice5': pl.Float64,
                        'AskVolume5': pl.Float64,
                        'AveragePrice': pl.Float64,
                        'symbol': pl.Utf8,
                        'exchange': pl.Utf8,
                        'datetime': pl.Utf8
                    })
                    
                    file_path = date_dir / f"{symbol}.csv"

                    # 如果文件已存在，追加数据
                    if file_path.exists():
                        try:
                            # 读取现有文件时也指定数据类型
                            existing_df = pl.read_csv(file_path, schema_overrides={
                                'InstrumentID': pl.Utf8,
                                'ExchangeID': pl.Utf8,
                                'TradingDay': pl.Utf8,
                                'UpdateTime': pl.Utf8,
                                'UpdateMillisec': pl.Int64,
                                'PreSettlementPrice': pl.Float64,
                                'PreClosePrice': pl.Float64,
                                'PreOpenInterest': pl.Float64,
                                'OpenPrice': pl.Float64,
                                'ClosePrice': pl.Float64,
                                'SettlementPrice': pl.Float64,
                                'UpperLimitPrice': pl.Float64,
                                'LowerLimitPrice': pl.Float64,
                                'HighestPrice': pl.Float64,
                                'LowestPrice': pl.Float64,
                                'LastPrice': pl.Float64,
                                'Volume': pl.Float64,
                                'LastVolume': pl.Float64,
                                'Turnover': pl.Float64,
                                'OpenInterest': pl.Float64,
                                'LastOpenInterest': pl.Float64,
                                'BidPrice1': pl.Float64,
                                'BidVolume1': pl.Float64,
                                'AskPrice1': pl.Float64,
                                'AskVolume1': pl.Float64,
                                'BidPrice2': pl.Float64,
                                'BidVolume2': pl.Float64,
                                'AskPrice2': pl.Float64,
                                'AskVolume2': pl.Float64,
                                'BidPrice3': pl.Float64,
                                'BidVolume3': pl.Float64,
                                'AskPrice3': pl.Float64,
                                'AskVolume3': pl.Float64,
                                'BidPrice4': pl.Float64,
                                'BidVolume4': pl.Float64,
                                'AskPrice4': pl.Float64,
                                'AskVolume4': pl.Float64,
                                'BidPrice5': pl.Float64,
                                'BidVolume5': pl.Float64,
                                'AskPrice5': pl.Float64,
                                'AskVolume5': pl.Float64,
                                'AveragePrice': pl.Float64,
                                'symbol': pl.Utf8,
                                'exchange': pl.Utf8,
                                'datetime': pl.Utf8
                            })
                            df = pl.concat([existing_df, df])
                            # 去重并排序
                            df = df.unique(subset=['InstrumentID', 'ExchangeID', 'UpdateTime']).sort('UpdateTime')
                        except Exception as read_error:
                            logger.warning(f"读取现有CSV文件失败 {file_path}: {read_error}，将备份并重新创建")
                            # 备份损坏的文件
                            backup_path = file_path.with_suffix(f'.backup_{int(time.time())}.csv')
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
                        df.write_csv(temp_path)
                        # 原子性移动临时文件到目标位置，添加重试机制
                        max_retries = 3
                        for retry in range(max_retries):
                            try:
                                if file_path.exists():
                                    file_path.unlink()  # 先删除目标文件
                                temp_path.rename(file_path)  # 使用rename而不是replace
                                break
                            except (OSError, PermissionError) as move_error:
                                if retry < max_retries - 1:
                                    time.sleep(0.1)  # 等待100ms后重试
                                    continue
                                else:
                                    raise move_error
                    except Exception as write_error:
                        logger.error(f"写入CSV文件失败 {file_path}: {write_error}")
                        # 清理临时文件
                        if temp_path.exists():
                            try:
                                temp_path.unlink()
                            except Exception:
                                pass
                        raise

            buffer_count = len(self._tick_csv_buffer)
            self._tick_csv_buffer.clear()
            logger.debug(f"Tick CSV数据写入完成，共{buffer_count}条")

        except Exception as e:
            logger.error(f"Tick CSV写入失败: {e}")
            # 不清空缓冲区，让数据在下次尝试时重新写入
            # self._tick_csv_buffer.clear()

    def _flush_bar_csv_buffer(self):
        """刷新bar数据CSV缓冲区"""
        if not self._bar_csv_buffer:
            return

        try:
            # 按日期和合约分组
            date_symbol_groups = {}
            for data in self._bar_csv_buffer:
                dt = datetime.fromisoformat(data['UpdateTime'])
                date_str = dt.strftime('%Y%m%d')
                symbol = data['InstrumentID']

                if date_str not in date_symbol_groups:
                    date_symbol_groups[date_str] = {}
                if symbol not in date_symbol_groups[date_str]:
                    date_symbol_groups[date_str][symbol] = []

                date_symbol_groups[date_str][symbol].append(data)

            # 分别写入每个日期和合约的文件
            for date_str, symbol_groups in date_symbol_groups.items():
                # 创建日期目录
                date_dir = self.csv_base_path / "bar_csv" / date_str
                date_dir.mkdir(parents=True, exist_ok=True)

                for symbol, symbol_data in symbol_groups.items():
                    # 创建新的DataFrame，明确指定数据类型
                    df = pl.DataFrame(symbol_data, schema_overrides={
                        'BarType': pl.Utf8,
                        'UpdateTime': pl.Utf8,
                        'InstrumentID': pl.Utf8,
                        'Volume': pl.Float64,
                        'OpenInterest': pl.Float64,
                        'OpenPrice': pl.Float64,
                        'HighestPrice': pl.Float64,
                        'LowestPrice': pl.Float64,
                        'ClosePrice': pl.Float64,
                        'LastVolume': pl.Float64,
                        'symbol': pl.Utf8,
                        'exchange': pl.Utf8,
                        'datetime': pl.Utf8
                    })
                    
                    file_path = date_dir / f"{symbol}.csv"

                    # 如果文件已存在，追加数据
                    if file_path.exists():
                        try:
                            # 读取现有文件时也指定数据类型
                            existing_df = pl.read_csv(file_path, schema_overrides={
                                'BarType': pl.Utf8,
                                'UpdateTime': pl.Utf8,
                                'InstrumentID': pl.Utf8,
                                'Volume': pl.Float64,
                                'OpenInterest': pl.Float64,
                                'OpenPrice': pl.Float64,
                                'HighestPrice': pl.Float64,
                                'LowestPrice': pl.Float64,
                                'ClosePrice': pl.Float64,
                                'LastVolume': pl.Float64,
                                'symbol': pl.Utf8,
                                'exchange': pl.Utf8,
                                'datetime': pl.Utf8
                            })
                            df = pl.concat([existing_df, df])
                            # 去重并排序
                            df = df.unique(subset=['InstrumentID', 'BarType', 'UpdateTime']).sort('UpdateTime')
                        except Exception as read_error:
                            logger.warning(f"读取现有CSV文件失败 {file_path}: {read_error}，将备份并重新创建")
                            # 备份损坏的文件
                            backup_path = file_path.with_suffix(f'.backup_{int(time.time())}.csv')
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
                        df.write_csv(temp_path)
                        # 原子性移动临时文件到目标位置，添加重试机制
                        max_retries = 3
                        for retry in range(max_retries):
                            try:
                                if file_path.exists():
                                    file_path.unlink()  # 先删除目标文件
                                temp_path.rename(file_path)  # 使用rename而不是replace
                                break
                            except (OSError, PermissionError) as move_error:
                                if retry < max_retries - 1:
                                    time.sleep(0.1)  # 等待100ms后重试
                                    continue
                                else:
                                    raise move_error
                    except Exception as write_error:
                        logger.error(f"写入CSV文件失败 {file_path}: {write_error}")
                        # 清理临时文件
                        if temp_path.exists():
                            try:
                                temp_path.unlink()
                            except:
                                pass
                        raise

            buffer_count = len(self._bar_csv_buffer)
            self._bar_csv_buffer.clear()
            logger.debug(f"Bar CSV数据写入完成，共{buffer_count}条")

        except Exception as e:
            logger.error(f"Bar CSV写入失败: {e}")
            # 不清空缓冲区，让数据在下次尝试时重新写入
            # self._bar_csv_buffer.clear()

    @staticmethod
    def _get_date_range(start_date: date, end_date: date) -> List[date]:
        """获取日期范围内的所有日期"""
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        return date_list
