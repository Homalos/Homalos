#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : data_center_strategy.py
@Date       : 2025/9/18 17:58
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据中心的策略，只负责数据存储，继承于策略基类
"""
import csv
import datetime
import os
from pathlib import Path
from typing import TextIO, Optional, Any

from src.constants import INSTRUMENT_EXCHANGE_FILENAME, TICK_DIR_NAME, Const, KLINE_DIR_NAME
from src.core.constants import Interval
from src.core.object import TickData, BarData, TradeData, OrderData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategy
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger
from src.utils.utility import load_json, create_folder, is_file_in_folder, write_csv


class DataCenterStrategy(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.strategy_name: str = "数据中心策略"
        self.strategy_content: str = "数据中心策略，存储行情使用"
        self.instruments: list[str] = self.load_all_instruments()
        self.bar_intervals: dict[str, list[Interval]] = {}

        for instrument_id in self.instruments:
            self.bar_intervals[instrument_id] = [
            Interval.MINUTE, Interval.MINUTE3, Interval.MINUTE5,
            Interval.MINUTE15, Interval.MINUTE30, Interval.MINUTE60
        ]

        self.prefix_tick_path: str = str(get_path_ins.get_data_dir() / TICK_DIR_NAME / Const.trading_day)
        self.prefix_kline_path: str = str(get_path_ins.get_data_dir() / KLINE_DIR_NAME / Const.trading_day)

        # 初始化详细策略文件 - 将在外部初始化时填充
        self.specific_strategy_map: dict[str, SpecificStrategy] = {}
        for instrument_id in self.instruments:
            self.specific_strategy_map[instrument_id] = DataCenterStrategy.Specific(
                self,
                self.strategy_id,
                instrument_id,
                self.bar_intervals.get(instrument_id, [])
            )
        self.csv_file: Optional[TextIO] = None
        self.csv_writer: Optional[Any] = None

        self.csv_kline_file: Optional[TextIO] = None
        self.csv_kline_writer: Optional[Any] = None

    def one_min(self, now: datetime.datetime) -> None:
        self.logger.info(f"one_min now_time：{now}")
        if self.instruments:
            # 按交易日创建tick存放的文件夹（已在初始化时创建，这里只是确保）
            rsp_create_tick_int = create_folder(self.prefix_tick_path)
            if rsp_create_tick_int == -1:
                self.logger.exception(f"数据中心策略一分钟回调: 无法创建tick交易日文件夹 {self.prefix_tick_path}")
                raise Exception("无法创建tick交易日文件夹")

            if rsp_create_tick_int == 1:
                return

            if rsp_create_tick_int == 0:
                # 新创建交易日文件夹，再创建CSV文件
                self.create_tick_csv_file()

        # if not self.is_open_flag:
        #     return

        if self.bar_intervals:
            rsp_create_kline_int = create_folder(self.prefix_kline_path)
            if rsp_create_kline_int == -1:
                self.logger.exception(f"数据中心策略一分钟回调: 无法创建kline交易日文件夹 {self.prefix_kline_path}")
                raise Exception("无法创建kline交易日文件夹")

            if rsp_create_kline_int == 1:
                return

            if rsp_create_kline_int == 0:
                # 新创建交易日文件夹，再创建CSV文件
                self.create_kline_csv_file()

    def create_tick_csv_file(self):
        for instrument_id in self.instruments:
            csv_file_path = Path(f"{self.prefix_tick_path}/{instrument_id}.csv")
            if not csv_file_path.exists():
                # 打开CSV文件（追加模式）
                self.csv_file = open(f"{self.prefix_tick_path}/{instrument_id}.csv", 'a', newline='', encoding='utf-8')
                self.csv_writer = csv.writer(self.csv_file)
                self.csv_writer.writerow([
                    'TradingDay', 'ExchangeID', 'LastPrice', 'PreSettlementPrice',
                    'PreClosePrice', 'PreOpenInterest', 'OpenPrice', 'HighestPrice', 'LowestPrice',
                    'Volume', 'Turnover', 'OpenInterest', 'ClosePrice', 'SettlementPrice',
                    'UpperLimitPrice', 'LowerLimitPrice', 'PreDelta', 'CurrDelta', 'UpdateTime',
                    'UpdateMillisec', 'BidPrice1', 'BidVolume1', 'AskPrice1', 'AskVolume1',
                    'BidPrice2', 'BidVolume2', 'AskPrice2', 'AskVolume2', 'BidPrice3', 'BidVolume3',
                    'AskPrice3', 'AskVolume3', 'BidPrice4', 'BidVolume4', 'AskPrice4', 'AskVolume4',
                    'BidPrice5', 'BidVolume5', 'AskPrice5', 'AskVolume5', 'AveragePrice', 'ActionDay',
                    'InstrumentID', 'ExchangeInstID', 'BandingUpperPrice', 'BandingLowerPrice', 'Timestamp'
                ])
                self.csv_file.flush()

    def create_kline_csv_file(self):
        # 新创建交易日文件夹，再创建CSV文件
        checker_kline_file = is_file_in_folder(self.prefix_kline_path)
        for instrument_id in self.instruments:
            for bar_interval in self.bar_intervals[instrument_id]:
                if checker_kline_file(f"{instrument_id}_{bar_interval.value}.csv"):
                    continue

                self.csv_kline_file = open(f"{self.prefix_kline_path}/{instrument_id}_{bar_interval.value}.csv",
                                           'a', newline='', encoding='utf-8')
                self.csv_kline_writer = csv.writer(self.csv_kline_file)
                self.csv_kline_writer.writerow([
                    'bar_type', 'update_time', 'instrument_id',
                    'exchange_id', 'volume', 'open_interest', 'open_price',
                    'high_price', 'low_price', 'close_price', 'last_volume'
                ])
                self.csv_kline_file.flush()


    @staticmethod
    def load_all_instruments() -> list[str]:
        """
        加载所有期货合约代码
        :return:
        """
        ins_exchange_dict = load_json(str(get_path_ins.get_config_dir() / INSTRUMENT_EXCHANGE_FILENAME))
        # 加载所有合约代码
        sub_ins_id = [ins for ins in list(ins_exchange_dict.keys())]
        return sub_ins_id

    class Specific(SpecificStrategy):
        """
        策略的详细策略文件
        """
        def __init__(
                self,
                base_strategy: BaseStrategy,
                strategy_id: str,
                instrument_id: str,
                bar_intervals: list[Interval]
        ):
            super().__init__(base_strategy, instrument_id, bar_intervals)
            self.logger = get_logger(self.__class__.__name__)
            self.base_strategy: BaseStrategy = base_strategy
            self.strategy_id: str = strategy_id
            self.instrument_id: str = instrument_id
            self.bar_intervals: list[Interval] = bar_intervals

            self.csv_file: Optional[TextIO] = None
            self.csv_writer: Optional[Any] = None  # csv.writer对象
            self.csv_kline_file: Optional[TextIO] = None
            self.csv_writer_kline: Optional[Any] = None
            self._tick_count: int = 0  # 初始化tick计数器

            # 初始化策略的时候，已经登录成功，所以可以正常获取到交易日
            self.prefix_tick_path: str = str(get_path_ins.get_data_dir() / TICK_DIR_NAME / Const.trading_day)
            self.prefix_kline_path: str = str(get_path_ins.get_data_dir() / KLINE_DIR_NAME / Const.trading_day)

        def on_init(self) -> None:
            """
            开盘前事件处理 - 检查CSV文件状态，但不强制初始化
            优化：避免大量合约同时初始化，让CSV文件在首次接收tick时再初始化
            """
            # 确保tick目录存在
            os.makedirs(self.prefix_tick_path, exist_ok=True)
            
            # 1. 创建文件对象
            self.csv_file = open(f"{self.prefix_tick_path}/{self.instrument_id}.csv", 'a', newline='')
            # 2. 基于文件对象构建 csv写入对象
            self.csv_writer = csv.writer(self.csv_file)

            # 确保kline目录存在
            os.makedirs(self.prefix_kline_path, exist_ok=True)
            
            for bar_interval in self.bar_intervals:
                csv_kline_path = f"{self.prefix_kline_path}/{self.instrument_id}_{bar_interval.value}.csv"
                
                # 检查文件是否存在且为空，如果是新文件则需要写入表头
                is_new_file = not os.path.exists(csv_kline_path) or os.path.getsize(csv_kline_path) == 0
                
                self.csv_kline_file = open(csv_kline_path, 'a', newline='')
                self.csv_writer_kline = csv.writer(self.csv_kline_file)
                
                # 如果是新文件，写入表头
                if is_new_file:
                    self.csv_writer_kline.writerow([
                        'bar_type', 'update_time', 'instrument_id',
                        'exchange_id', 'volume', 'open_interest', 'open_price',
                        'high_price', 'low_price', 'close_price', 'last_volume'
                    ])
                    self.csv_kline_file.flush()

        def on_close(self) -> None:
            """收盘后关闭CSV文件"""
            try:
                if self.csv_file:
                    # 强制刷新所有缓冲数据到磁盘
                    self.csv_file.flush()
                    os.fsync(self.csv_file.fileno())  # 强制同步到磁盘
                    self.csv_file.close()
                    
                    # 输出写入统计信息
                    self.logger.info(f"合约 {self.instrument_id} 收盘统计: 共写入 {self._tick_count} 条tick数据")
                    self.logger.info("CSV文件已关闭并同步到磁盘")
                
                # 重置变量
                self.csv_writer = None
                self.csv_file = None
                self._tick_count = 0  # 重置计数器
            except Exception as e:
                self.logger.exception(f"关闭合约 {self.instrument_id} CSV文件时发生错误: {e}")

        def on_alarm(self) -> None:
            self.logger.info("on_alarm")

        def on_tick(self, tick: TickData) -> None:
            # 检查CSV文件状态，如果文件被关闭则重新初始化
            if not self.csv_writer or not self.csv_file or self.csv_file.closed:
                return

            # 记录tick数据接收（调试用）
            self._tick_count += 1

            # 每处理 x 个tick输出一次日志，避免日志过多
            if self._tick_count % 300 == 1:
                self.logger.info(f"写入进度: 合约{self.instrument_id} 已处理{self._tick_count}条tick数据")

            try:
                tick_data_list = [
                    tick.trading_day,
                    tick.exchange_id.value,
                    tick.last_price,
                    tick.pre_settlement_price,
                    tick.pre_close_price,
                    tick.pre_open_interest,
                    tick.open_price,
                    tick.highest_price,
                    tick.lowest_price,
                    tick.volume,
                    tick.turnover,
                    tick.open_interest,
                    tick.close_price,
                    tick.settlement_price,
                    tick.upper_limit_price,
                    tick.lower_limit_price,
                    tick.pre_delta,
                    tick.curr_delta,
                    tick.update_time,
                    tick.update_millisec,
                    tick.bid_price_1,
                    tick.bid_volume_1,
                    tick.ask_price_1,
                    tick.ask_volume_1,
                    tick.bid_price_2,
                    tick.bid_volume_2,
                    tick.ask_price_2,
                    tick.ask_volume_2,
                    tick.bid_price_3,
                    tick.bid_volume_3,
                    tick.ask_price_3,
                    tick.ask_volume_3,
                    tick.bid_price_4,
                    tick.bid_volume_4,
                    tick.ask_price_4,
                    tick.ask_volume_4,
                    tick.bid_price_5,
                    tick.bid_volume_5,
                    tick.ask_price_5,
                    tick.ask_volume_5,
                    tick.average_price,
                    tick.action_day,
                    tick.instrument_id,
                    tick.exchange_inst_id,
                    tick.banding_upper_price,
                    tick.banding_lower_price,
                    tick.timestamp
                ]
                # 写入tick数据
                self.csv_writer.writerow(tick_data_list)
                self.csv_file.flush()

            except Exception as e:
                self.logger.exception(f"写入合约 {self.instrument_id} tick数据失败: {e}")
                # 如果写入失败，尝试重新初始化文件

        def on_bar(self, bar: BarData) -> None:
            content = [bar.bar_type.value, bar.update_time.strftime("%H:%M:%S"), bar.instrument_id,
                       bar.exchange_id.value, bar.volume, bar.open_interest, bar.open_price, bar.high_price,
                       bar.low_price, bar.close_price, bar.last_volume]
            csv_path = f"{self.prefix_kline_path}/{self.instrument_id}_{bar.bar_type.value}.csv"
            write_csv(csv_path, 'a', content)

        def on_trade(self, trade: TradeData) -> None:
            self.logger.info("on_trade")

        def on_order(self, order: OrderData) -> None:
            self.logger.info("on_order")

def get_strategy():
    return DataCenterStrategy()
