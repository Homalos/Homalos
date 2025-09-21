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

from src.constants import INSTRUMENT_EXCHANGE_FILENAME, TICK_DIR_NAME
from src.core.constants import Interval
from src.core.object import TickData, BarData, TradeData, OrderData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategyApi
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger, console
from src.utils.utility import load_json, create_folder


class DataCenterStrategy(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_id: str = "0001"
        self.strategy_name: str = "数据中心策略"
        self.sub_kline_type: list[Interval] = [
            # Interval.MINUTE, Interval.MINUTE3, Interval.MINUTE5,
            # Interval.MINUTE15, Interval.MINUTE30, Interval.MINUTE60
        ]
        self.strategy_content: str = "数据中心策略，存储行情使用"

        # 初始化详细策略文件 - 将在外部初始化时填充
        self.specific_strategy_map = {}
        for ins in self.sub_ins_id:
            self.specific_strategy_map[ins] = DataCenterStrategy.Specific(ins, self.strategy_id, self.sub_kline_type)


    class Specific(SpecificStrategyApi):

        def __init__(self, instrument_id: str, strategy_id: str, sub_kline_type: list):
            super().__init__(instrument_id, strategy_id, sub_kline_type)

            self.logger = get_logger(__class__.__name__)
            """从文件加载所有期货合约"""
            ins_exchange_dict: dict[str, str] = load_json(str(get_path_ins.get_config_dir() / INSTRUMENT_EXCHANGE_FILENAME))
            self.sub_ins_list = [ins for ins in list(ins_exchange_dict.keys())]

            self.csv_file = None
            self.csv_writer = None

        def on_before_open(self) -> None:
            self.logger.info("on_before_open")
            if self.sub_ins_list:
                prefix_tick_path = str(get_path_ins.get_data_dir() / TICK_DIR_NAME / self.trading_day)
                # 按交易日创建tick存放的文件夹
                create_folder(prefix_tick_path)

                # 初始化生成csv文件
                for instrument_id in self.sub_ins_list:
                    with open(f"{prefix_tick_path}/{instrument_id}.csv", 'a', newline='') as self.csv_file:
                        self.csv_writer = csv.writer(self.csv_file)
                        # 写入列名，如果没有列名可以不执行这一行
                        self.csv_writer.writerow(['TradingDay', 'ExchangeID', 'LastPrice', 'PreSettlementPrice',
                                                  'PreClosePrice', 'PreOpenInterest', 'OpenPrice', 'HighestPrice',
                                                  'LowestPrice',
                                                  'Volume', 'Turnover', 'OpenInterest', 'ClosePrice', 'SettlementPrice',
                                                  'UpperLimitPrice', 'LowerLimitPrice', 'PreDelta', 'CurrDelta',
                                                  'UpdateTime',
                                                  'UpdateMillisec', 'BidPrice1', 'BidVolume1', 'AskPrice1',
                                                  'AskVolume1',
                                                  'BidPrice2', 'BidVolume2', 'AskPrice2', 'AskVolume2', 'BidPrice3',
                                                  'BidVolume3',
                                                  'AskPrice3', 'AskVolume3', 'BidPrice4', 'BidVolume4', 'AskPrice4',
                                                  'AskVolume4',
                                                  'BidPrice5', 'BidVolume5', 'AskPrice5', 'AskVolume5', 'AveragePrice',
                                                  'ActionDay',
                                                  'InstrumentID', 'ExchangeInstID', 'BandingUpperPrice',
                                                  'BandingLowerPrice', 'Timestamp'])

                self.csv_file = open(f"{prefix_tick_path}/{self.instrument_id}.csv", 'a', newline='')
                # 2. 基于文件对象构建 csv写入对象
                self.csv_writer = csv.writer(self.csv_file)

        def on_after_close(self) -> None:
            self.logger.info("on_after_close")
            self.csv_writer.close()

        def on_alarm(self) -> None:
            self.logger.info("on_alarm")

        def on_tick(self, tick: TickData) -> None:
            console.info(f"收到tick数据：{tick.trading_day}, {tick.instrument_id}, {tick.last_price}")
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
            self.csv_writer.writerow(tick_data_list)
            self.csv_file.flush()

        def on_bar(self, bar: BarData) -> None:
            self.logger.info("on_bar")

        def on_rtn_trade(self, trade: TradeData) -> None:
            self.logger.info("on_rtn_trade")

        def on_rtn_order(self, order: OrderData) -> None:
            self.logger.info("on_rtn_order")