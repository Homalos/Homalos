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
import os
from pathlib import Path
from typing import TextIO, Optional, Any

from src.constants import INSTRUMENT_EXCHANGE_FILENAME, TICK_DIR_NAME, Const
from src.core.constants import Interval
from src.core.object import TickData, BarData, TradeData, OrderData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategyApi
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger
from src.utils.utility import load_json, create_folder


class DataCenterStrategy(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__class__.__name__)
        self.strategy_id: str = "0001"
        self.strategy_name: str = "数据中心策略"
        self.sub_ins_id: list[str] = self.load_all_instruments()
        self.sub_kline_type: list[Interval] = [
            Interval.MINUTE, Interval.MINUTE3, Interval.MINUTE5,
            Interval.MINUTE15, Interval.MINUTE30, Interval.MINUTE60
        ]
        self.strategy_content: str = "数据中心策略，存储行情使用"

        self.prefix_tick_path: str = str(get_path_ins.get_data_dir() / TICK_DIR_NAME / Const.trading_day)

        # 初始化详细策略文件 - 将在外部初始化时填充
        self.specific_strategy_map: dict[str, SpecificStrategyApi] = {}
        for ins in self.sub_ins_id:
            self.specific_strategy_map[ins] = DataCenterStrategy.Specific(
                ins,
                self.strategy_id,
                self.sub_kline_type,
                self.prefix_tick_path
            )
        self.csv_file: Optional[TextIO] = None
        self.csv_writer: Optional[Any] = None

    def one_min(self, now_time: str) -> None:
        self.logger.info(f"one_min：{now_time}")
        if self.sub_ins_id:
            # 按交易日创建tick存放的文件夹（已在初始化时创建，这里只是确保）
            rsp_int = create_folder(self.prefix_tick_path)
            if rsp_int == -1:
                self.logger.exception(f"数据中心策略一分钟回调: 无法创建交易日文件夹 {self.prefix_tick_path}")
                raise Exception("无法创建交易日文件夹")

            if rsp_int == 1:
                return

            if rsp_int == 0:
                # 新创建交易日文件夹，再创建CSV文件
                self.create_csv_file()

    def create_csv_file(self):
        for ins in self.sub_ins_id:
            csv_file_path = Path(f"{self.prefix_tick_path}/{ins}.csv")
            if not csv_file_path.exists():
                # 打开CSV文件（追加模式）
                self.csv_file = open(f"{self.prefix_tick_path}/{ins}.csv", 'a', newline='', encoding='utf-8')
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


    class Specific(SpecificStrategyApi):

        def __init__(self, instrument_id: str, strategy_id: str, sub_kline_type: list, prefix_tick_path: str):
            super().__init__(instrument_id, strategy_id, sub_kline_type, prefix_tick_path)

            self.logger = get_logger(self.__class__.__name__)
            self.csv_file: Optional[TextIO] = None
            self.csv_writer: Optional[Any] = None  # csv.writer对象
            self._tick_count: int = 0  # 初始化tick计数器
            self.instrument_id: str = instrument_id
            self.strategy_id: str = strategy_id
            self.sub_kline_type: list[Interval] = sub_kline_type
            self.prefix_tick_path: str = prefix_tick_path

        def on_before_open(self) -> None:
            """
            开盘前事件处理 - 检查CSV文件状态，但不强制初始化
            优化：避免大量合约同时初始化，让CSV文件在首次接收tick时再初始化
            """
            # 1. 创建文件对象
            self.csv_file = open(f"{self.prefix_tick_path}/{self.instrument_id}.csv", 'a', newline='')
            # 2. 基于文件对象构建 csv写入对象
            self.csv_writer = csv.writer(self.csv_file)

        def on_after_close(self) -> None:
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
            self.logger.info("on_bar")

        def on_rtn_trade(self, trade: TradeData) -> None:
            self.logger.info("on_rtn_trade")

        def on_rtn_order(self, order: OrderData) -> None:
            self.logger.info("on_rtn_order")