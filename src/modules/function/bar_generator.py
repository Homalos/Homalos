#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : bar_generator.py
@Date       : 2025/9/15 14:13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 合成K线
"""
import ast
import datetime
import threading
import traceback
from queue import Queue

from src.constants import strategy_map, thread_pool
from src.core.constants import Interval
from src.core.object import BarData, TickData
from src.strategy.base_strategy import BaseStrategy
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger
from src.utils.utility import del_num


class BarGenerator:

    def __init__(self):
        self.logger = get_logger(__class__.__name__)

        # 订阅K线的合约名称和合约类型
        self.sub_kline_id: list[str] = []
        self.sub_kline_type: list[Interval] = []

        # 1分钟K线的合约字典
        self.kline_min1_map: dict[str, BarData] = {}
        self.kline_min1_lock_map: dict[str, threading.Lock] = {}

        # 3分钟K线字典
        self.kline_min3_map: dict[str, BarData] = {}
        self.kline_min3_lock_map: dict[str, threading.Lock] = {}

        # 5分钟K线字典
        self.kline_min5_map: dict[str, BarData] = {}
        self.kline_min5_lock_map: dict[str, threading.Lock] = {}

        # 15分钟K线字典
        self.kline_min15_map: dict[str, BarData] = {}
        self.kline_min15_lock_map: dict[str, threading.Lock] = {}

        # 30分钟K线字典
        self.kline_min30_map: dict[str, BarData] = {}
        self.kline_min30_lock_map: dict[str, threading.Lock] = {}

        # 60分钟K线字典
        self.kline_min60_map: dict[str, BarData] = {}
        self.kline_min60_lock_map: dict[str, threading.Lock] = {}

        # K线的队列
        self.kline_queue = Queue()

        # 交易时间字典
        self.trading_time: dict = {}

        # 初始化交易时间字典
        self.init_trading_time()

        self.logger.info("已开启tick合成K线系统")
        self.bar_thread = threading.Thread(target=self.get_kline)
        self.bar_thread.name = "传递K线"
        self.bar_thread.start()

        # 初始化信号，用于判断分钟字典是否进行初始化，如有夜盘，第二天无需初始化，没有夜盘，第二天需要初始化
        self.init_flag: bool = False

    def init_trading_time(self) -> None:
        """
        初始化各周期K线的交易时间字典

        该函数读取trading目录下的多个时间配置文件，将每个文件中的时间数据按小时分组存储到
        self.trading_time字典中，用于后续的交易时间判断。

        文件格式要求：
        - 文件名格式：min{分钟数}.txt，如min3.txt, min5.txt等
        - 文件内容：应为Python列表格式的字符串表示，包含多个"HHMM"格式的时间点

        结构示例：
        self.trading_time = {
            'min3': {
                '09': ['0930', '0933', '0936', ...],
                '10': ['1000', '1003', '1006', ...],
                ...
            },
            'min5': {
                '09': ['0930', '0935', '0940', ...],
                ...
            },
            ...
        }
        """
        data_dir = str(get_path_ins.get_data_dir() / "trading")
        for file in ['min3.txt', 'min5.txt', 'min15.txt', 'min30.txt', 'min60.txt']:
            product = file.replace('.txt', '')
            self.trading_time[product] = {}
            with open(f"{data_dir}/{file}", "r") as f:
                data = f.read()  # 读取文件
                if data:
                    data = ast.literal_eval(data)
            if data:
                for time_point in data:
                    hour = time_point[:2]
                    if hour in self.trading_time[product]:
                        self.trading_time[product][hour].append(time_point)
                    else:
                        self.trading_time[product][hour] = []
                        self.trading_time[product][hour].append(time_point)

    def add_sub_kline_id(self, sub_kline_id_list) -> None:
        # 增加订阅K线的合约名称
        self.sub_kline_id: list = list(set(self.sub_kline_id + sub_kline_id_list))

    def add_sub_kline_type(self, sub_kline_type_list) -> None:
        # 增加订阅K线的类型
        self.sub_kline_type = list(set(self.sub_kline_type + sub_kline_type_list))

    def init_min_kline_map(self) -> None:
        """
        初始化分钟K线的字典以及线程锁,需要在 add_sub_kline_id 后使用
        如果有夜盘，晚上八点初始化早上八点不需要初始化
        :return:
        """
        if self.init_flag:
            return

        for instrument_id in self.sub_kline_id:
            self.kline_min1_map[instrument_id] = BarData()
            self.kline_min1_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了3分钟K线，则对字典进行
            if Interval.MINUTE3 in self.sub_kline_type:
                self.kline_min3_map[instrument_id] = BarData()
                self.kline_min3_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了5分钟K线，则对字典进行
            if Interval.MINUTE5 in self.sub_kline_type:
                self.kline_min5_map[instrument_id] = BarData()
                self.kline_min5_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了15分钟K线，则对字典进行
            if Interval.MINUTE15 in self.sub_kline_type:
                self.kline_min15_map[instrument_id] = BarData()
                self.kline_min15_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了30分钟K线，则对字典进行
            if Interval.MINUTE30 in self.sub_kline_type:
                self.kline_min30_map[instrument_id] = BarData()
                self.kline_min30_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了60分钟K线，则对字典进行
            if Interval.MINUTE60 in self.sub_kline_type:
                self.kline_min60_map[instrument_id] = BarData()
                self.kline_min60_lock_map[instrument_id] = threading.Lock()

        # 置为Ture表示初始化完了
        self.init_flag = True


    def check_min1(self, time_now):
        """
        防止没有tick传来，导致没有1分钟K线生成
        :param time_now:
        :return:
        """
        def is_new_kline_min(update_minute, true_minute):
            if update_minute in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
                                24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44,
                                45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58]:
                if abs(true_minute - update_minute) >= 2:
                    return True
                else:
                    return False
            elif update_minute == 59:
                if true_minute == 0:
                    return False
                else:
                    return True

        minute = time_now.minute
        for kline in self.kline_min1_map.values():
            if kline.instrument_id not in self.kline_min1_map.keys():
                return
            # 如果k线时间不在交易时间，则退出
            if not self.judge_in_trading_time(del_num(kline.instrument_id), kline.update_time.strftime('%H:%M:%S')):
                return
            self.kline_min1_lock_map[kline.instrument_id].acquire()

            if is_new_kline_min(kline.update_time.minute, minute):
                instrument_id = kline.instrument_id
                if del_num(instrument_id) in ['TF', 'IF', 'T', 'TS', 'IC', 'IH']:
                    if self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S') in ['09:29:00']:
                        # 如果是集合竞价，
                        # openPrice = self.kline_min1_map[instrument_id].close_price
                        volume = 0
                    else:
                        # 保存前一分钟末的收盘价作为现在的开盘价，以及前一分钟的累计成交量，用于计算当前K线的成交量
                        # openPrice = self.kline_min1_map[instrument_id].close_price
                        volume = self.kline_min1_map[instrument_id].volume
                else:
                    if self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S') in ['20:59:00', '08:59:00']:
                        # 如果是集合竞价，
                        # openPrice = self.kline_min1_map[instrument_id].close_price
                        volume = 0
                    else:
                        # 保存前一分钟末的收盘价作为现在的开盘价，以及前一分钟的累计成交量，用于计算当前K线的成交量
                        # openPrice = self.kline_min1_map[instrument_id].close_price
                        volume = self.kline_min1_map[instrument_id].volume

                open_price = self.kline_min1_map[instrument_id].close_price

                # 将前一根K线存放到队列里
                # 防止开启程序后第一次推送，以及集合竞价不推送
                if self.kline_min1_map[instrument_id].instrument_id != '':
                    # 注意Volume字段是累计成交量，所以这个时间段内成交量为该值与上一时间段末成交量的差值
                    # 成交量 = max（当前累计成交 - 上一刻成交， 0）
                    self.kline_min1_map[instrument_id].volume = max(
                        volume - self.kline_min1_map[instrument_id].last_volume, 0)

                    bar = self.get_new_bar(self.kline_min1_map[instrument_id])
                    self.kline_queue.put(bar)

                self.kline_min1_map[instrument_id] = BarData()
                self.kline_min1_map[instrument_id].bar_type = Interval.MINUTE
                self.kline_min1_map[instrument_id].instrument_id = instrument_id
                self.kline_min1_map[instrument_id].update_time = datetime.time(int(time_now.hour),
                                                                               int(time_now.minute),
                                                                               0, 0)
                self.kline_min1_map[instrument_id].volume = volume
                self.kline_min1_map[instrument_id].open_interest = kline.open_interest
                self.kline_min1_map[instrument_id].open_price = open_price
                self.kline_min1_map[instrument_id].high_price = max(open_price, kline.close_price)
                self.kline_min1_map[instrument_id].low_price = min(open_price, kline.close_price)
                self.kline_min1_map[instrument_id].close_price = kline.close_price
                self.kline_min1_map[instrument_id].last_volume = volume

            self.kline_min1_lock_map[kline.instrument_id].release()

    def judge_in_trading_time(self, product, time):
        """
        判断是否在交易时间
        :param product:
        :param time:
        :return:
        """
        try:
            if time[:2] not in self.trading_time[product]:
                return False
            if time in self.trading_time[product][time[:2]]:
                return True
            else:
                return False
        except Exception as e:
            self.logger.exception(f'judge_in_trading_time Error, Error: {e}')
            self.logger.exception(traceback.format_exc())
            return True

    def is_sub_kline(self, instrument_id):
        # 判断合约是否需要订阅K线
        return instrument_id in self.sub_kline_id

    def tick_to_kline(self, tick: TickData):
        # 不使用线程
        self.tick_to_kline_specific_process(tick)

    @staticmethod
    def get_new_bar(bar: BarData):
        """
        获取新的bar
        :param bar:
        :return:
        """
        new_bar = BarData()
        new_bar.instrument_id = bar.instrument_id
        new_bar.bar_type = bar.bar_type
        new_bar.volume = bar.volume
        new_bar.update_time = bar.update_time
        new_bar.exchange_id = bar.exchange_id
        new_bar.open_interest = bar.open_interest
        new_bar.open_price = bar.open_price
        new_bar.high_price = bar.high_price
        new_bar.low_price = bar.low_price
        new_bar.close_price = bar.close_price
        new_bar.last_volume = bar.last_volume

        return new_bar

    def tick_to_kline_specific_process(self, tick: TickData):
        # 单一合约合成1分钟K线
        # 对tick进行加锁，防止2个tick同时更改同一根K线造成一些错误
        self.kline_min1_lock_map[tick.instrument_id].acquire()
        instrument_id = tick.instrument_id

        st = tick.update_time.strftime("%H:%M:%S").split(':')

        # 剔除函数， 剔除一些有延迟的tick，比如K线时间是9：01，但是有一个9:00：59的延迟tick
        if tick.update_time.strftime("%H:%M:%S") < self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S') \
                and st[0] == self.kline_min1_map[instrument_id].update_time.strftime('%H'):
            self.kline_min1_lock_map[tick.instrument_id].release()
            return

        # 如果tick的分钟数 等于K线的分钟数，则不是新的分钟线
        if int(st[1]) == self.kline_min1_map[instrument_id].update_time.minute and \
                int(st[0]) == self.kline_min1_map[instrument_id].update_time.hour:
            new_minute = False
        else:
            new_minute = True

        # 如果是新1分钟，生成一个新k线变量
        if new_minute:
            if del_num(instrument_id) in ['TF', 'IF', 'T', 'TS', 'IC', 'IH']:
                if self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S') in ['09:29:00']:
                    # 如果是集合竞价，
                    # openPrice = self.kline_min1_map[instrumentID].close_price
                    volume = 0
                else:
                    # 保存前一分钟末的收盘价作为现在的开盘价，以及前一分钟的累计成交量，用于计算当前K线的成交量
                    # openPrice = self.kline_min1_map[instrumentID].close_price
                    volume = self.kline_min1_map[instrument_id].volume
            else:
                if self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S') in ['20:59:00', '08:59:00']:
                    # 如果是集合竞价，
                    # openPrice = self.kline_min1_map[instrumentID].close_price
                    volume = 0
                else:
                    # 保存前一分钟末的收盘价作为现在的开盘价，以及前一分钟的累计成交量，用于计算当前K线的成交量
                    # openPrice = self.kline_min1_map[instrumentID].close_price
                    volume = self.kline_min1_map[instrument_id].volume

            open_price = self.kline_min1_map[instrument_id].close_price
            # 防止开盘前初始化后没有集合竞价导致开盘价为0，使得K线数据无效
            if open_price == 0:
                open_price = tick.last_price

            # 将前一根K线存放到队列里
            # 防止开启程序后第一次推送，以及集合竞价不推送
            if self.kline_min1_map[instrument_id].instrument_id != '':
                # 注意Volume字段是累计成交量，所以这个时间段内成交量为该值与上一时间段末成交量的差值
                # 成交量 = max（当前累计成交 - 上一刻成交， 0）
                self.kline_min1_map[instrument_id].volume = max(volume - self.kline_min1_map[instrument_id].last_volume, 0)

                bar = self.get_new_bar(self.kline_min1_map[instrument_id])
                self.kline_queue.put(bar)

            self.kline_min1_map[instrument_id] = BarData()
            self.kline_min1_map[instrument_id].bar_type = Interval.MINUTE
            self.kline_min1_map[instrument_id].instrument_id = instrument_id
            self.kline_min1_map[instrument_id].update_time = datetime.time(int(st[0]), int(st[1]), 0, 0)
            self.kline_min1_map[instrument_id].volume = volume
            self.kline_min1_map[instrument_id].open_interest = tick.open_interest
            self.kline_min1_map[instrument_id].open_price = open_price
            self.kline_min1_map[instrument_id].high_price = max(open_price, tick.last_price)
            self.kline_min1_map[instrument_id].low_price = min(open_price, tick.last_price)
            self.kline_min1_map[instrument_id].close_price = tick.last_price
            self.kline_min1_map[instrument_id].last_volume = volume
        else:
            # 如果不是新1分钟，更新相关数据
            self.kline_min1_map[instrument_id].high_price = max(self.kline_min1_map[instrument_id].high_price, tick.last_price)
            self.kline_min1_map[instrument_id].low_price = min(self.kline_min1_map[instrument_id].low_price, tick.last_price)
            self.kline_min1_map[instrument_id].close_price = tick.last_price
            # 持仓量
            self.kline_min1_map[instrument_id].open_interest = tick.open_interest
            # 累计成交量
            self.kline_min1_map[instrument_id].volume = tick.volume

        self.kline_min1_lock_map[instrument_id].release()

    def get_kline(self):
        # 获取所有类型分钟线，并进行分发
        while True:
            kline: BarData = self.kline_queue.get()

            # 如果是无效数据，退出
            if self.clean_kline(kline):
                continue

            # 如果是1分钟K线，另需要分发到合成其他K线线程，合成其他K线
            if kline.bar_type == Interval.MINUTE:
                thread_pool.submit(self.min1_to_other_kline, kline)

            self.distribute_kline(kline)

    def min1_to_other_kline(self, kline: BarData):
        """
        一分钟生成其他周期K线
        :param kline:
        :return:
        """
        if kline.instrument_id in self.sub_kline_id and Interval.MINUTE3 in self.sub_kline_type:
            self.min1_to_min3(kline)
        if kline.instrument_id in self.sub_kline_id and Interval.MINUTE5 in self.sub_kline_type:
            self.min1_to_min5(kline)
        if kline.instrument_id in self.sub_kline_id and Interval.MINUTE15 in self.sub_kline_type:
            self.min1_to_min15(kline)
        if kline.instrument_id in self.sub_kline_id and Interval.MINUTE30 in self.sub_kline_type:
            self.min1_to_min30(kline)
        if kline.instrument_id in self.sub_kline_id and Interval.MINUTE60 in self.sub_kline_type:
            self.min1_to_min60(kline)

    def min1_to_min3(self, kline: BarData):
        self.kline_min3_lock_map[kline.instrument_id].acquire()
        instrument_id = kline.instrument_id

        # 如果是新的3分钟K线，生成一个新k线变量
        if self.is_new_kline_min(Interval.MINUTE3, kline.update_time):

            self.kline_min3_map[instrument_id] = BarData()
            self.kline_min3_map[instrument_id].bar_type = Interval.MINUTE3
            self.kline_min3_map[instrument_id].instrument_id = instrument_id
            self.kline_min3_map[instrument_id].update_time = kline.update_time
            self.kline_min3_map[instrument_id].volume = kline.volume
            self.kline_min3_map[instrument_id].open_interest = kline.open_interest
            self.kline_min3_map[instrument_id].open_price = kline.open_price
            self.kline_min3_map[instrument_id].high_price = max(0.0, kline.high_price)
            self.kline_min3_map[instrument_id].low_price = min(float('inf'), kline.low_price)
            self.kline_min3_map[instrument_id].close_price = kline.close_price
        else:
            # 如果不是的3分钟K线，更新相关数据
            self.kline_min3_map[instrument_id].high_price = max(self.kline_min3_map[instrument_id].high_price, kline.high_price)
            self.kline_min3_map[instrument_id].low_price = min(self.kline_min3_map[instrument_id].low_price, kline.low_price)
            self.kline_min3_map[instrument_id].close_price = kline.close_price
            # 持仓量
            self.kline_min3_map[instrument_id].open_interest = kline.open_interest
            # 累计成交量
            self.kline_min3_map[instrument_id].volume += kline.volume

        if self.is_min_kline_end(Interval.MINUTE3, kline.update_time):
            bar = self.get_new_bar(self.kline_min3_map[instrument_id])
            self.kline_queue.put(bar)

        self.kline_min3_lock_map[instrument_id].release()

    def min1_to_min5(self, kline: BarData):
        self.kline_min5_lock_map[kline.instrument_id].acquire()
        instrument_id = kline.instrument_id

        # 如果是新的5分钟K线，生成一个新k线变量
        if self.is_new_kline_min(Interval.MINUTE5, kline.update_time):

            self.kline_min5_map[instrument_id] = BarData()
            self.kline_min5_map[instrument_id].bar_type = Interval.MINUTE5
            self.kline_min5_map[instrument_id].instrument_id = instrument_id
            self.kline_min5_map[instrument_id].update_time = kline.update_time
            self.kline_min5_map[instrument_id].volume = kline.volume
            self.kline_min5_map[instrument_id].open_interest = kline.open_interest
            self.kline_min5_map[instrument_id].open_price = kline.open_price
            self.kline_min5_map[instrument_id].high_price = max(0.0, kline.high_price)
            self.kline_min5_map[instrument_id].low_price = min(float('inf'), kline.low_price)
            self.kline_min5_map[instrument_id].close_price = kline.close_price
        else:
            # 如果不是的5分钟K线，更新相关数据
            self.kline_min5_map[instrument_id].high_price = max(self.kline_min5_map[instrument_id].high_price, kline.high_price)
            self.kline_min5_map[instrument_id].low_price = min(self.kline_min5_map[instrument_id].low_price, kline.low_price)
            self.kline_min5_map[instrument_id].close_price = kline.close_price
            # 持仓量
            self.kline_min5_map[instrument_id].open_interest = kline.open_interest
            # 累计成交量
            self.kline_min5_map[instrument_id].volume += kline.volume

        if self.is_min_kline_end(Interval.MINUTE5, kline.update_time):
            bar = self.get_new_bar(self.kline_min5_map[instrument_id])
            self.kline_queue.put(bar)

        self.kline_min5_lock_map[instrument_id].release()

    def min1_to_min15(self, kline):
        self.kline_min15_lock_map[kline.instrument_id].acquire()
        instrument_id = kline.instrument_id

        # 如果是新的15分钟K线，生成一个新k线变量
        if self.is_new_kline_min(Interval.MINUTE15, kline.update_time):

            self.kline_min15_map[instrument_id] = BarData()
            self.kline_min15_map[instrument_id].bar_type = Interval.MINUTE15
            self.kline_min15_map[instrument_id].instrument_id = instrument_id
            self.kline_min15_map[instrument_id].update_time = kline.update_time
            self.kline_min15_map[instrument_id].volume = kline.volume
            self.kline_min15_map[instrument_id].open_interest = kline.open_interest
            self.kline_min15_map[instrument_id].open_price = kline.open_price
            self.kline_min15_map[instrument_id].high_price = max(0, kline.high_price)
            self.kline_min15_map[instrument_id].low_price = min(float('inf'), kline.low_price)
            self.kline_min15_map[instrument_id].close_price = kline.close_price
        else:
            # 如果不是的15分钟K线，更新相关数据
            self.kline_min15_map[instrument_id].high_price = max(self.kline_min15_map[instrument_id].high_price,
                                                              kline.high_price)
            self.kline_min15_map[instrument_id].low_price = min(self.kline_min15_map[instrument_id].low_price,
                                                             kline.low_price)
            self.kline_min15_map[instrument_id].close_price = kline.close_price
            # 持仓量
            self.kline_min15_map[instrument_id].open_interest = kline.open_interest
            # 累计成交量
            self.kline_min15_map[instrument_id].volume += kline.volume

        if self.is_min_kline_end(Interval.MINUTE15, kline.update_time):
            bar = self.get_new_bar(self.kline_min15_map[instrument_id])
            self.kline_queue.put(bar)

        self.kline_min15_lock_map[instrument_id].release()

    def min1_to_min30(self, kline):
        self.kline_min30_lock_map[kline.instrument_id].acquire()
        instrument_id = kline.instrument_id

        # 如果是新的30分钟K线，生成一个新k线变量
        if self.is_new_kline_min(Interval.MINUTE30, kline.update_time):

            self.kline_min30_map[instrument_id] = BarData()
            self.kline_min30_map[instrument_id].bar_type = Interval.MINUTE30
            self.kline_min30_map[instrument_id].instrument_id = instrument_id
            self.kline_min30_map[instrument_id].update_time = kline.update_time
            self.kline_min30_map[instrument_id].volume = kline.volume
            self.kline_min30_map[instrument_id].open_interest = kline.open_interest
            self.kline_min30_map[instrument_id].open_price = kline.open_price
            self.kline_min30_map[instrument_id].high_price = max(0, kline.high_price)
            self.kline_min30_map[instrument_id].low_price = min(float('inf'), kline.low_price)
            self.kline_min30_map[instrument_id].close_price = kline.close_price
        else:
            # 如果不是的30分钟K线，更新相关数据
            self.kline_min30_map[instrument_id].high_price = max(self.kline_min30_map[instrument_id].high_price,
                                                              kline.high_price)
            self.kline_min30_map[instrument_id].low_price = min(self.kline_min30_map[instrument_id].low_price,
                                                             kline.low_price)
            self.kline_min30_map[instrument_id].close_price = kline.close_price
            # 持仓量
            self.kline_min30_map[instrument_id].open_interest = kline.open_interest
            # 累计成交量
            self.kline_min30_map[instrument_id].volume += kline.volume

        if self.is_min_kline_end(Interval.MINUTE30, kline.update_time):
            bar = self.get_new_bar(self.kline_min30_map[instrument_id])
            self.kline_queue.put(bar)

        self.kline_min30_lock_map[instrument_id].release()

    def min1_to_min60(self, kline):
        self.kline_min60_lock_map[kline.instrument_id].acquire()
        instrument_id = kline.instrument_id

        # 如果是新的60分钟K线，生成一个新k线变量
        if self.is_new_kline_min(Interval.MINUTE60, kline.update_time):

            self.kline_min60_map[instrument_id] = BarData()
            self.kline_min60_map[instrument_id].bar_type = Interval.MINUTE60
            self.kline_min60_map[instrument_id].instrument_id = instrument_id
            self.kline_min60_map[instrument_id].update_time = kline.update_time
            self.kline_min60_map[instrument_id].volume = kline.volume
            self.kline_min60_map[instrument_id].open_interest = kline.open_interest
            self.kline_min60_map[instrument_id].open_price = kline.open_price
            self.kline_min60_map[instrument_id].high_price = max(0, kline.high_price)
            self.kline_min60_map[instrument_id].low_price = min(float('inf'), kline.low_price)
            self.kline_min60_map[instrument_id].close_price = kline.close_price

        else:
            # 如果不是的60分钟K线，更新相关数据
            self.kline_min60_map[instrument_id].high_price = max(self.kline_min60_map[instrument_id].high_price,
                                                              kline.high_price)
            self.kline_min60_map[instrument_id].low_price = min(self.kline_min60_map[instrument_id].low_price,
                                                             kline.low_price)
            self.kline_min60_map[instrument_id].close_price = kline.close_price
            # 持仓量
            self.kline_min60_map[instrument_id].open_interest = kline.open_interest
            # 累计成交量
            self.kline_min60_map[instrument_id].volume += kline.volume

        if self.is_min_kline_end(Interval.MINUTE60, kline.update_time):
            bar = self.get_new_bar(self.kline_min60_map[instrument_id])
            self.kline_queue.put(bar)

        self.kline_min60_lock_map[instrument_id].release()

    @staticmethod
    def is_new_kline_min(min_type, update_time):
        # 判断是否是一根新的K线
        if min_type == Interval.MINUTE3:
            if update_time.minute in [0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51, 54, 57]:
                return True
            else:
                return False
        elif min_type == Interval.MINUTE5:
            if update_time.minute in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
                return True
            else:
                return False
        elif min_type == Interval.MINUTE15:
            if update_time.minute in [0, 15, 30, 45]:
                return True
            else:
                return False
        elif min_type == Interval.MINUTE30:
            if update_time.minute in [0, 30]:
                return True
            else:
                return False
        elif min_type == Interval.MINUTE60:
            if update_time.minute in [0]:
                return True
            else:
                return False

    @staticmethod
    def is_min_kline_end(min_type, update_time):
        # 判断是否是一根新的K线
        if min_type == Interval.MINUTE3:
            if update_time.minute in [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56, 59]:
                return True
            else:
                return False
        elif min_type == Interval.MINUTE5:
            if update_time.minute in [4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59]:
                return True
            else:
                return False
        elif min_type == Interval.MINUTE15:
            if update_time.minute in [14, 29, 44, 59]:
                return True
            else:
                return False
        elif min_type == Interval.MINUTE30:
            if update_time.minute in [29, 59]:
                return True
            else:
                return False
        elif min_type == Interval.MINUTE60:
            if update_time.minute in [59]:
                return True
            else:
                return False

    def distribute_kline(self, kline: BarData):
        # 判断需要给哪些策略传Kline
        for strategy in strategy_map.values():
            if kline.instrument_id in strategy.sub_ins_id and kline.bar_type in strategy.sub_kline_type:
                self.save_kline(strategy, kline)

    @staticmethod
    def save_kline(strategy: BaseStrategy, kline: BarData):
        instrument_id = kline.instrument_id
        strategy.specific_strategy_map[instrument_id].kline_lock.acquire()
        strategy.specific_strategy_map[instrument_id].bar_data = kline
        thread_pool.submit(strategy.specific_strategy_map[instrument_id].on_bar)

    # 如果是无效数据，则返回True
    def clean_kline(self, kline: BarData):
        if kline.instrument_id == '':
            return True
        if kline.volume == 0 or kline.open_interest == 0.0 or kline.open_price == 0.0 or kline.high_price == 0.0 or \
                kline.low_price == float('inf') or kline.close_price == 0.0:
            self.logger.warning('{} K线数据无效, updateTime:{}'.format(kline.instrument_id, kline.update_time))
            return True
        
        return False

    def clean_map(self):
        # 订阅K线的合约名称和合约类型
        self.sub_kline_id: list[str] = []
        self.sub_kline_type: list[Interval] = []

        # 1分钟K线的合约字典
        self.kline_min1_map: dict[str, BarData] = {}
        self.kline_min1_lock_map: dict[str, threading.Lock] = {}

        # 3分钟K线字典
        self.kline_min3_map: dict[str, BarData] = {}
        self.kline_min3_lock_map: dict[str, threading.Lock] = {}

        # 5分钟K线字典
        self.kline_min5_map: dict[str, BarData] = {}
        self.kline_min5_lock_map: dict[str, threading.Lock] = {}

        # 15分钟K线字典
        self.kline_min15_map: dict[str, BarData] = {}
        self.kline_min15_lock_map: dict[str, threading.Lock] = {}

        # 30分钟K线字典
        self.kline_min30_map: dict[str, BarData] = {}
        self.kline_min30_lock_map: dict[str, threading.Lock] = {}

        # 60分钟K线字典
        self.kline_min60_map: dict[str, BarData] = {}
        self.kline_min60_lock_map: dict[str, threading.Lock] = {}

        # 初始化信号，用于判断分钟字典是否进行初始化，如有夜盘，第二天无需初始化，没有夜盘，第二天需要初始化
        self.init_flag: bool = False
