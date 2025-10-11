#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_pool.py
@Date       : 2025/9/26 23:44
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略池
"""
from src.constants import TRADING_FLOW_DIR_NAME, trade_file_head
from src.core.constants import Interval
from src.strategy.base_strategy import BaseStrategy
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger
from src.utils.utility import write_csv, get_file_name


class StrategyPool(object):

    def __init__(self) -> None:
        """
        初始化策略池
        """
        # 策略字典
        self.strategy_map: dict[str, BaseStrategy] = {}
        # 订阅了哪些合约，如：['au2208', 'FG209', 'SA209']
        self.sub_ins_id: list[str] = []
        # 订阅了哪些合约以及具体K线类型
        # 如：{'FG209': ['min'], 'SA209': ['min', 'min5'], 'au2208': ['min', 'min5']}
        self.sub_kline_type: dict[str, list[Interval]] = {}
        self.logger = get_logger(__class__.__name__)

    def init_sub(self) -> None:
        """
        初始化订阅

        Returns:
            None
        """
        del self.sub_ins_id
        del self.sub_kline_type

        self.sub_ins_id: list[str] = []
        self.sub_kline_type: dict[str, list[Interval]] = {}

    def add_strategy(self, strategy_id: str, strategy) -> None:
        """
        添加策略到策略字典

        Args:
            strategy_id: 策略ID
            strategy: 策略实例

        Returns:
            None
        """
        self.strategy_map[strategy_id] = strategy
        self.create_trade_file()

    def get_strategies(self) -> [BaseStrategy]:
        """
        获取策略列表

        Returns:
            策略列表
        """
        return self.strategy_map.values()

    def get_strategy_pool_info(self):
        self.logger.info(f"共运行 {len(self.strategy_map)} 个策略：")
        for strategy in self.strategy_map.values():
            self.logger.info(strategy.strategy_id, strategy.strategy_name, strategy.strategy_content)

    def init_sub_id(self):
        # 遍历所有策略，将所有策略的合约进行合并
        for strategy in self.strategy_map.values():
            self.sub_ins_id: list[str] = list(set(self.sub_ins_id + strategy.sub_ins_id))

    def init_kline_type(self) -> dict[str, list[Interval]]:
        """
        初始化订阅的K线类型

        Returns:
            订阅的K线类型
        """
        # 初始化一个空字典来存储订阅了哪些合约及其订阅的K线类型
        self.sub_kline_type = {}
        # 遍历策略映射中的值，即遍历所有子策略
        for strategy in self.strategy_map.values():
            # 获取子策略的sub_id和sub_kline_type列表
            sub_id = strategy.sub_ins_id
            kline_types = strategy.sub_kline_type
            # 如果策略没有订阅K线，则过滤掉
            if len(kline_types) == 0:
                continue
            # 遍历sub_id列表
            for i in range(len(sub_id)):
                # 获取合约代码
                instrument_id = sub_id[i]
                # 如果该合约还没有被记录在sub_kline_type字典中，创建一个空列表来记录其订阅的K线类型
                if instrument_id not in self.sub_kline_type:
                    self.sub_kline_type[instrument_id] = []
                # 遍历该策略订阅的K线类型，将其记录在sub_kline_type字典中
                for kline_type in kline_types:
                    # 如果该合约还没有订阅这种K线类型，就添加到列表中
                    if kline_type not in self.sub_kline_type[instrument_id]:
                        self.sub_kline_type[instrument_id].append(kline_type)

        # 返回包含订阅了哪些合约及其订阅的K线类型的字典
        return self.sub_kline_type

    def create_trade_file(self) -> None:
        """
        创建交易流水文件

        Returns:
            None
        """
        # 遍历所有策略，将所有策略的合约进行合并
        trading_flow_path = str(get_path_ins.get_data_dir() / TRADING_FLOW_DIR_NAME)
        for strategy in self.strategy_map.values():
            for sub_id in strategy.sub_ins_id:
                file_name = 'strategy{}_{}.csv'.format(strategy.strategy_id, sub_id)
                # 判断文件是否存在
                if file_name not in get_file_name(trading_flow_path, '.csv'):
                    write_csv(f"{trading_flow_path}/{file_name}", 'w', trade_file_head)
