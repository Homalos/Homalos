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
from src.constants import TRADING_FLOW_DIR_NAME
from src.core.constants import Interval
from src.strategy.base_strategy import BaseStrategy
from src.utils.get_path import get_path_ins
from src.utils.utility import write_csv, get_file_name


class StrategyPool:

    def __init__(self):
        # 策略字典：{1: <__main__.Strategy1 object at 0x0000004439176F70>,
        # 2: <__main__.Strategy2 object at 0x00000044390486A0>}
        self.strategy_map: dict[str, BaseStrategy] = {}
        # 订阅了哪些合约，如：['au2208', 'FG209', 'SA209']
        self.sub_ins_id = []
        # 订阅了哪些合约以及具体K线类型，如：{'FG209': ['min'], 'SA209': ['min', 'min5'], 'au2208': ['min', 'min5']}
        self.sub_kline_type: dict[str, list[Interval]] = {}

    def init_sub(self):
        del self.sub_ins_id
        del self.sub_kline_type

        self.sub_ins_id = []
        self.sub_kline_type = {}

    def add_strategy(self, strategy_id: str, strategy):
        self.strategy_map[strategy_id] = strategy
        self.create_trade_file()

    def get_strategies(self) -> [BaseStrategy]:
        return self.strategy_map.values()

    def init_sub_id(self):
        # 遍历所有策略，将所有策略的合约进行合并
        for strategy in self.strategy_map.values():
            self.sub_ins_id: list[str] = list(set(self.sub_ins_id + strategy.sub_ins_id))

    def init_kline_type(self):
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

    def create_trade_file(self):
        """
        创建交易流水
        :return:
        """
        # 遍历所有策略，将所有策略的合约进行合并
        content = ['自然日', '交易日', '时间', '标的', '方向', '委托价', '成交价', '成交量', '平仓盈亏', '手续费']
        trading_flow_path = str(get_path_ins.get_data_dir() / TRADING_FLOW_DIR_NAME)
        for strategy in self.strategy_map.values():
            for sub_id in strategy.sub_ins_id:
                file_name = 'strategy{}_{}.csv'.format(strategy.strategy_id, sub_id)
                # 判断文件是否存在
                if file_name not in get_file_name(trading_flow_path, '.csv'):
                    write_csv(f"{trading_flow_path}/{file_name}", 'w', content)


if __name__ == '__main__':

    class Strategy:
        def execute(self):
            pass


    class Strategy1(Strategy):
        # 只在启动程序的时候执行一次
        def __init__(self):
            super().__init__()
            # 策略编号
            self.strategy_id = "1"
            # 订阅的合约
            self.sub_ins_id = ["FG209", "SA209", 'au2208', 'sc2207', 'm2209', 'IF2206', 'rb2210', 'fu2209', 'hc2210',
                          'bu2206']
            self.sub_ins_id = ["FG209", "SA209"]
            # 订阅的K线
            self.sub_kline_type = [Interval.MINUTE]

            self.strategy_content = "记录全市场行情"

        def execute(self):
            print("Executing strategy 1")


    class Strategy2(Strategy):
        # 只在启动程序的时候执行一次
        def __init__(self):
            super().__init__()
            # 策略编号
            self.strategy_id = "2"
            # 订阅的合约
            self.sub_ins_id = ["FG209", "SA209", 'au2208', 'sc2207', 'm2209', 'IF2206', 'rb2210', 'fu2209', 'hc2210',
                          'bu2206']
            self.sub_ins_id = ["au2208", "SA209"]
            # 订阅的K线
            self.sub_kline_type = [Interval.MINUTE, Interval.MINUTE5]

            self.strategy_content = ""

        def execute(self):
            print("Executing strategy 2")


    strategyPool = StrategyPool()
    strategyPool.add_strategy("1", Strategy1())
    strategyPool.add_strategy("2", Strategy2())

    strategy_list = strategyPool.get_strategies()
    print(strategyPool.strategy_map)
    print(len(strategy_list))

    strategyPool.init_sub_id()
    print(strategyPool.sub_ins_id)

    strategyPool.init_kline_type()
    print(strategyPool.sub_kline_type)