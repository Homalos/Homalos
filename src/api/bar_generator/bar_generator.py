#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : bar_generator.py
@Date       : 2025/9/15 14:13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: K线合成器
"""
import ast
import datetime
import os
import threading
import traceback
from queue import Queue
from typing import Optional

from src import constants
from src.constants import TRADING_DIR_NAME, is_queue
from src.core.constants import Interval
from src.core.event_bus import EventBus
from src.core.object import BarData, TickData
from src.strategy.base_strategy import BaseStrategy
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger
from src.utils.log.logger import log_object, time_log_detail
from src.utils.utility import del_num


class BarGenerator:

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.logger = get_logger(self.__class__.__name__)
        self.event_bus = event_bus

        # # 内存管理配置
        # self.max_kline_cache = max_kline_cache  # 每个合约最大缓存K线数量
        # self.last_cleanup_time = datetime.datetime.now()  # 上次清理时间
        # self.cleanup_interval = 3600  # 清理间隔（秒）
        
        # # K线处理专用线程池
        # self.kline_executor = ThreadPoolExecutor(
        #     max_workers=50,
        #     thread_name_prefix='BarWorker'
        # )

        # # 订阅K线的合约名称和合约类型
        # self.sub_kline_id: list[str] = []
        # self.sub_kline_type: list[Interval] = []

        self.trading_dir_path = str(get_path_ins.get_data_dir() / TRADING_DIR_NAME)
        self.logger.info(f"交易时间文件位置：{self.trading_dir_path}")

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
        self.kline_queue: Queue = Queue()

        # 交易时间字典
        self.trading_time: dict = {}
        # 是否使用队列分发K线
        self.is_queue: bool = is_queue

        # 初始化交易时间字典
        try:
            self.init_trading_time()
            self.logger.info(f"交易时间字典初始化完成，加载了 {len(self.trading_time)} 个配置")
            self._debug_trading_time_config()
        except Exception as e:
            self.logger.exception(f"初始化交易时间字典失败: {e}")
            # 如果初始化失败，创建一个空字典避免后续错误
            self.trading_time = {}

        if self.is_queue:
            self.logger.info("已开启tick合成K线系统")
            self.bar_thread = threading.Thread(target=self.get_kline)
            self.bar_thread.daemon = True
            self.bar_thread.name = "传递K线-守护线程"
            self.bar_thread.start()


        # 初始化信号，用于判断分钟字典是否进行初始化，如有夜盘，第二天无需初始化，没有夜盘，第二天需要初始化
        self.init_flag: bool = False

        # 订阅了哪些合约以及具体K线类型，如：{'FG209': ['min'], 'SA209': ['min', 'min5'], 'au2208': ['min', 'min5']}
        self.sub_kline_type_map: dict[str, list[Interval]] = {}
        
        # 设置事件订阅
        if self.event_bus:
            self._setup_event_handlers()
    
    def _setup_event_handlers(self) -> None:
        """设置事件处理器"""
        if not self.event_bus:
            self.logger.warning("EventBus未初始化，跳过事件处理器注册")
            return
            
        from src.core.event import EventType
        # 订阅K线配置更新事件
        self.event_bus.subscribe(EventType.KLINE_CONFIG_UPDATE, self._handle_kline_config_update)
        # 订阅tick数据事件
        self.event_bus.subscribe(EventType.TICK, self._handle_tick_data)
        self.logger.info("BarGenerator事件处理器已注册")
    
    def _handle_kline_config_update(self, event) -> None:
        """
        处理K线配置更新事件
        
        Args:
            event: K线配置更新事件，payload格式:
                   {"subscription_map": {instrument_id: [Interval, ...]}}
        """
        try:
            self.logger.info("🔍 [DEBUG] BarGenerator收到K线配置更新事件")
            payload = event.payload
            self.logger.info(f"🔍 [DEBUG] Event payload: {payload}")
            subscription_map = payload.get('subscription_map', {})
            
            if not subscription_map:
                self.logger.warning("收到空的K线配置更新")
                return
            
            self.logger.info(f"收到K线配置更新，共 {len(subscription_map)} 个合约: {subscription_map}")
            
            # 更新订阅的K线类型映射
            self.set_kline_type(subscription_map)
            
            # 初始化K线字典
            self.init_min_kline_map()
            
            self.logger.info(f"✅ K线配置更新完成，订阅合约数: {len(self.sub_kline_type_map)}, sub_kline_type_map={self.sub_kline_type_map}")
            
        except Exception as e:
            self.logger.error(f"处理K线配置更新失败: {e}", exc_info=True)
    
    def _handle_tick_data(self, event) -> None:
        """
        处理tick数据事件
        
        Args:
            event: tick数据事件，payload格式:
                   - 如果是dict: {"code": 0, "data": TickData对象}
                   - 如果直接是TickData对象
        """
        try:
            # 解析tick数据（兼容多种格式）
            if isinstance(event.payload, dict):
                tick_data = event.payload.get("data")
            else:
                tick_data = event.payload
            
            if not tick_data:
                return
            
            # 获取合约ID（兼容对象和字典）
            instrument_id = None
            if hasattr(tick_data, 'instrument_id'):
                instrument_id = tick_data.instrument_id
            elif isinstance(tick_data, dict):
                instrument_id = tick_data.get('instrument_id')
            
            if not instrument_id:
                self.logger.warning("tick数据缺少instrument_id")
                return
            
            # 只处理订阅的合约
            if instrument_id in self.sub_kline_type_map:
                self.tick_to_kline(tick_data)
            
        except Exception as e:
            self.logger.error(f"处理tick数据失败: {e}", exc_info=True)

    def init_trading_time(self) -> None:
        """
        初始化各周期K线的交易时间字典和产品特定的交易时间字典

        该函数读取trading目录下的多个时间配置文件，将每个文件中的时间数据按小时分组存储到
        self.trading_time字典中，用于后续的交易时间判断。

        文件格式要求：
        - K线周期文件：min{分钟数}.txt，如min3.txt, min5.txt等
        - 产品特定文件：{产品代码}.txt，如lu.txt, CY.txt等
        - 文件内容：应为Python列表格式的字符串表示，包含多个"HH:MM:SS"格式的时间点

        结构示例：
        self.trading_time = {
            'min3': {
                '09': ['09:30:00', '09:33:00', '09:36:00', ...],
                '10': ['10:00:00', '10:03:00', '10:06:00', ...],
                ...
            },
            'lu': {
                '09': ['09:00:00', '09:01:00', '09:02:00', ...],
                '22': ['22:40:00', '22:41:00', '22:42:00', ...],
                ...
            },
            ...
        }
        """
        # 确保 os 模块可用（已在顶部导入）
        
        # 1. 加载K线周期配置文件
        for file in ['min3.txt', 'min5.txt', 'min15.txt', 'min30.txt', 'min60.txt']:
            product = file.replace('.txt', '')
            self._load_trading_time_file(f"{self.trading_dir_path}/{file}", product)
        
        # 2. 加载产品特定的交易时间配置文件
        try:
            # 扫描trading目录下所有txt文件
            trading_files = [f for f in os.listdir(self.trading_dir_path) 
                           if f.endswith('.txt') and not f.startswith('min')]
            
            for file in trading_files:
                # 产品代码就是文件名（去掉.txt后缀）
                product_code = file.replace('.txt', '')
                self._load_trading_time_file(f"{self.trading_dir_path}/{file}", product_code)
                
            self.logger.info(f"成功加载 {len(trading_files)} 个产品的交易时间配置")
            
        except Exception as e:
            self.logger.exception(f"加载产品交易时间配置失败: {e}")
    
    def _load_trading_time_file(self, file_path: str, product_key: str) -> None:
        """
        加载单个交易时间配置文件
        :param file_path: 文件路径
        :param product_key: 产品标识（K线周期或产品代码）
        """
        try:
            self.logger.debug(f"尝试加载交易时间配置文件: {file_path} -> {product_key}")
            
            if not os.path.exists(file_path):
                self.logger.warning(f"交易时间配置文件不存在: {file_path}")
                return
                
            with open(file_path, "r", encoding='utf-8') as f:
                data = f.read().strip()
                self.logger.debug(f"读取到文件内容长度: {len(data)} 字符")
                
                if data:
                    data = ast.literal_eval(data)
                    self.logger.debug(f"解析后的数据长度: {len(data)} 个时间点")
                    
            if data:
                self.trading_time[product_key] = {}
                for time_point in data:
                    hour = time_point[:2]  # 提取小时部分
                    if hour in self.trading_time[product_key]:
                        self.trading_time[product_key][hour].append(time_point)
                    else:
                        self.trading_time[product_key][hour] = [time_point]
                        
                self.logger.debug(f"成功加载 {product_key} 的交易时间配置，共 {len(data)} 个时间点，{len(self.trading_time[product_key])} 个小时段")
            else:
                self.logger.warning(f"交易时间配置文件 {file_path} 内容为空")
                
        except Exception as e:
            self.logger.exception(f"加载交易时间文件 {file_path} 失败: {e}")
            self.logger.error(f"文件路径: {file_path}, 产品: {product_key}")

    def _debug_trading_time_config(self) -> None:
        """调试方法：显示加载的交易时间配置"""
        if not self.trading_time:
            self.logger.warning("交易时间配置为空！")
            return
            
        self.logger.info("已加载的交易时间配置")
        for product, time_config in self.trading_time.items():
            if time_config:
                hour_count = len(time_config)
                total_times = sum(len(times) for times in time_config.values())
                self.logger.debug(f"  - {product}: {hour_count} 个小时段, {total_times} 个时间点")
            else:
                self.logger.warning(f"  - {product}: 配置为空")

    # def add_sub_kline_id(self, sub_kline_id_list: list[str]) -> None:
    #     # 增加订阅K线的合约名称
    #     self.sub_kline_id: list[str] = list(set(self.sub_kline_id + sub_kline_id_list))
    #
    # def add_sub_kline_type(self, sub_kline_type_list: list[Interval]) -> None:
    #     # 增加订阅K线的类型
    #     self.sub_kline_type: list[Interval] = list(set(self.sub_kline_type + sub_kline_type_list))

    def set_kline_type(self, kline_type_map):
        """
        设置订阅的K线类型
        :param kline_type_map:
        :return:
        """
        self.sub_kline_type_map = kline_type_map

    def init_min_kline_map(self) -> None:
        """
        初始化分钟K线的字典以及线程锁,需要在 add_sub_kline_id 后使用
        如果有夜盘，晚上八点初始化早上八点不需要初始化
        :return:
        """
        if self.init_flag:
            return

        for instrument_id in self.sub_kline_type_map.keys():
            self.kline_min1_map[instrument_id] = BarData()
            self.kline_min1_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了3分钟K线，则对字典进行
            if Interval.MINUTE3 in self.sub_kline_type_map[instrument_id]:
                self.kline_min3_map[instrument_id] = BarData()
                self.kline_min3_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了5分钟K线，则对字典进行
            if Interval.MINUTE5 in self.sub_kline_type_map[instrument_id]:
                self.kline_min5_map[instrument_id] = BarData()
                self.kline_min5_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了15分钟K线，则对字典进行
            if Interval.MINUTE15 in self.sub_kline_type_map[instrument_id]:
                self.kline_min15_map[instrument_id] = BarData()
                self.kline_min15_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了30分钟K线，则对字典进行
            if Interval.MINUTE30 in self.sub_kline_type_map[instrument_id]:
                self.kline_min30_map[instrument_id] = BarData()
                self.kline_min30_lock_map[instrument_id] = threading.Lock()

            # 如果订阅了60分钟K线，则对字典进行
            if Interval.MINUTE60 in self.sub_kline_type_map[instrument_id]:
                self.kline_min60_map[instrument_id] = BarData()
                self.kline_min60_lock_map[instrument_id] = threading.Lock()

        # 置为Ture表示初始化完了
        self.init_flag = True


    def check_min1(self):
        """
        防止没有tick传来，导致没有1分钟K线生成
        :return:
        """
        # time.sleep(3)
        time_now = datetime.datetime.now()
        def is_new_kline_min(update_minute, true_minute):
            if update_minute in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                                 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
                                 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59]:
                if abs(true_minute - update_minute) >= 1:
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
                        # 【修复】使用current_cumulative_volume字段获取最新的累计成交量
                        volume = self.kline_min1_map[instrument_id].current_cumulative_volume
                        # 🔍 调试：check_min1读取volume
                        if instrument_id in ['SA601', 'cs2605', 'lu2604']:
                            self.logger.info(f"[CHECK_MIN1_VOLUME] {instrument_id} - 读取current_cumulative_volume={volume}, last_volume={self.kline_min1_map[instrument_id].last_volume}, 时间={self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S')}")
                else:
                    if self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S') in ['20:59:00', '08:59:00']:
                        # 如果是集合竞价，
                        # openPrice = self.kline_min1_map[instrument_id].close_price
                        volume = 0
                    else:
                        # 保存前一分钟末的收盘价作为现在的开盘价，以及前一分钟的累计成交量，用于计算当前K线的成交量
                        # openPrice = self.kline_min1_map[instrument_id].close_price
                        # 【修复】使用current_cumulative_volume字段获取最新的累计成交量
                        volume = self.kline_min1_map[instrument_id].current_cumulative_volume
                        # 🔍 调试：check_min1读取volume
                        if instrument_id in ['SA601', 'cs2605', 'lu2604']:
                            self.logger.info(f"[CHECK_MIN1_VOLUME] {instrument_id} - 读取current_cumulative_volume={volume}, last_volume={self.kline_min1_map[instrument_id].last_volume}, 时间={self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S')}")

                open_price = self.kline_min1_map[instrument_id].close_price

                # 将前一根K线存放到队列里
                # 防止开启程序后第一次推送，以及集合竞价不推送
                if self.kline_min1_map[instrument_id].instrument_id != '':
                    # 注意Volume字段是累计成交量，所以这个时间段内成交量为该值与上一时间段末成交量的差值
                    # 成交量 = max（当前累计成交 - 上一刻成交， 0）
                    calculated_volume = max(volume - self.kline_min1_map[instrument_id].last_volume, 0)
                    self.kline_min1_map[instrument_id].volume = calculated_volume

                    # 🔍 调试：check_min1的成交量计算 - 扩展到更多合约
                    if instrument_id in ['lu2604', 'sp2606', 'sc2608', 'SA601', 'cs2605']:
                        self.logger.info(f"[CHECK_MIN1_CALC] {instrument_id} - 推送前一分钟K线")
                        self.logger.info(f"[CHECK_MIN1_CALC] {instrument_id} - 成交量计算: current_cumulative_volume({volume}) - last_volume({self.kline_min1_map[instrument_id].last_volume}) = 分钟成交量({calculated_volume})")
                        self.logger.info(f"[CHECK_MIN1_CALC] {instrument_id} - K线时间: {self.kline_min1_map[instrument_id].update_time}")

                    bar = self.get_new_bar(self.kline_min1_map[instrument_id])
                    if self.is_queue:
                        self.kline_queue.put(bar)
                    else:
                        self.distribute_kline_without_queue(bar)

                self.kline_min1_map[instrument_id] = BarData()
                self.kline_min1_map[instrument_id].bar_type = Interval.MINUTE
                self.kline_min1_map[instrument_id].instrument_id = instrument_id
                self.kline_min1_map[instrument_id].exchange_id = kline.exchange_id  # 修复：设置交易所ID
                self.kline_min1_map[instrument_id].update_time = datetime.time(int(time_now.hour),
                                                                               int(time_now.minute), 0, 0)
                self.kline_min1_map[instrument_id].volume = volume
                self.kline_min1_map[instrument_id].open_interest = kline.open_interest
                self.kline_min1_map[instrument_id].open_price = open_price
                self.kline_min1_map[instrument_id].high_price = max(open_price, kline.close_price)
                self.kline_min1_map[instrument_id].low_price = min(open_price, kline.close_price)
                self.kline_min1_map[instrument_id].close_price = kline.close_price
                self.kline_min1_map[instrument_id].last_volume = volume
                # 【修复】初始化当前累计成交量字段
                self.kline_min1_map[instrument_id].current_cumulative_volume = volume

            self.kline_min1_lock_map[kline.instrument_id].release()

    def judge_in_trading_time(self, product, now_time):
        """
        判断是否在交易时间
        :param product: 产品代码
        :param now_time: 时间字符串 HH:MM:SS
        :return: bool
        """
        try:
            # 检查产品是否在交易时间配置中
            if product not in self.trading_time:
                self.logger.warning(f"产品 '{product}' 的交易时间配置不存在，默认允许交易")
                return True
                
            # 检查时间配置
            product_trading_time = self.trading_time[product]
            hour_key = now_time[:2]  # 提取小时部分
            
            if hour_key not in product_trading_time:
                return False
                
            if now_time in product_trading_time[hour_key]:
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.exception(f'judge_in_trading_time Error, Product: {product}, Time: {now_time}, Error: {e}')
            self.logger.exception(traceback.format_exc())
            # 发生异常时默认允许交易，避免系统停止
            return True

    def is_sub_kline(self, instrument_id) -> bool:
        # 判断合约是否需要订阅K线
        return instrument_id in self.sub_kline_type_map.keys()

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
        instrument_id: str = tick.instrument_id
        lock = self.kline_min1_lock_map[instrument_id]
        
        # 使用try-finally确保锁一定会被释放，防止死锁
        lock.acquire()
        try:
            self._tick_to_kline_locked(tick, instrument_id)
        finally:
            lock.release()
    
    def _tick_to_kline_locked(self, tick: TickData, instrument_id: str):
        """
        在锁保护下执行tick转K线的核心逻辑
        此方法由tick_to_kline_specific_process调用，确保异常安全
        """
        
        # 🔍 调试：输出接收到的tick数据
        if instrument_id in ['SA601', 'FG601', 'sc2601']:  # 选择几个代表性合约进行调试
            self.logger.debug(f"[TICK_DEBUG] {instrument_id} - 接收tick: volume={tick.volume}, time={tick.update_time}")

        st: list[str] = tick.update_time.split(':')
        # 剔除一些有延迟的tick，比如K线时间是9：01，但是有一个9:00：59的延迟tick
        kline_min1_update_time = self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S')
        # 剔除函数， 剔除一些有延迟的tick，比如K线时间是9：01，但是有一个9:00：59的延迟tick
        if tick.update_time < kline_min1_update_time and st[0] == self.kline_min1_map[instrument_id].update_time.strftime('%H'):
            # 锁会在外层finally中自动释放
            self.logger.info("合成K线剔除过期Tick：\n"
                             f'tick.update_time: {tick.update_time}'
                             f'kline_min1_update_time: {kline_min1_update_time}')
            return

        # 如果tick的分钟数 等于K线的分钟数，则不是新的分钟线
        if int(st[1]) == self.kline_min1_map[instrument_id].update_time.minute and \
                int(st[0]) == self.kline_min1_map[instrument_id].update_time.hour:
            new_minute = False
        else:
            new_minute = True

        # 如果是新1分钟，生成一个新k线变量
        if new_minute:
            # 🔍 调试：新分钟开始
            if instrument_id in ['lu2604', 'sp2606', 'sc2608']:
                self.logger.debug(f"[KLINE_DEBUG] {instrument_id} - 新分钟开始，当前K线: volume={self.kline_min1_map[instrument_id].volume}, last_volume={self.kline_min1_map[instrument_id].last_volume}")
            
            if del_num(instrument_id) in ['TF', 'IF', 'T', 'TS', 'IC', 'IH']:
                if self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S') in ['09:29:00']:
                    # 如果是集合竞价，
                    # openPrice = self.kline_min1_map[instrumentID].close_price
                    volume = 0
                    if instrument_id in ['lu2604', 'sp2606', 'sc2608', 'SA601']:
                        self.logger.info(f"[TICK_VOLUME] {instrument_id} - 集合竞价时段，设置volume=0")
                else:
                    # 保存前一分钟末的收盘价作为现在的开盘价，以及前一分钟的累计成交量，用于计算当前K线的成交量
                    # openPrice = self.kline_min1_map[instrumentID].close_price
                    # 【修复】使用current_cumulative_volume字段获取最新的累计成交量
                    volume = self.kline_min1_map[instrument_id].current_cumulative_volume
                    if instrument_id in ['lu2604', 'sp2606', 'sc2608', 'SA601']:
                        self.logger.info(f"[TICK_VOLUME] {instrument_id} - 正常时段，从当前K线获取current_cumulative_volume={volume}")
            else:
                if self.kline_min1_map[instrument_id].update_time.strftime('%H:%M:%S') in ['20:59:00', '08:59:00']:
                    # 如果是集合竞价，
                    # openPrice = self.kline_min1_map[instrumentID].close_price
                    volume = 0
                    if instrument_id in ['lu2604', 'sp2606', 'sc2608', 'SA601', 'cs2605']:
                        self.logger.info(f"[TICK_VOLUME] {instrument_id} - 夜盘集合竞价时段，设置volume=0")
                else:
                    # 保存前一分钟末的收盘价作为现在的开盘价，以及前一分钟的累计成交量，用于计算当前K线的成交量
                    # openPrice = self.kline_min1_map[instrumentID].close_price
                    # 【修复】使用current_cumulative_volume字段获取最新的累计成交量
                    volume = self.kline_min1_map[instrument_id].current_cumulative_volume
                    if instrument_id in ['lu2604', 'sp2606', 'sc2608', 'SA601', 'cs2605']:
                        self.logger.info(f"[TICK_VOLUME] {instrument_id} - 正常时段，从当前K线获取current_cumulative_volume={volume}, last_volume={self.kline_min1_map[instrument_id].last_volume}")

            open_price = self.kline_min1_map[instrument_id].close_price
            # 防止开盘前初始化后没有集合竞价导致开盘价为0，使得K线数据无效
            if open_price == 0:
                open_price = tick.last_price

            # 将前一根K线存放到队列里
            # 防止开启程序后第一次推送，以及集合竞价不推送
            if self.kline_min1_map[instrument_id].instrument_id != '':
                # 注意Volume字段是累计成交量，所以这个时间段内成交量为该值与上一时间段末成交量的差值
                # 成交量 = max（当前累计成交 - 上一刻成交， 0）
                calculated_volume = max(volume - self.kline_min1_map[instrument_id].last_volume, 0)
                self.kline_min1_map[instrument_id].volume = calculated_volume
                
                # 🔍 调试：tick触发的K线成交量计算
                if instrument_id in ['lu2604', 'sp2606', 'sc2608', 'SA601', 'cs2605']:
                    self.logger.info(f"[TICK_CALC] {instrument_id} - 新分钟触发K线生成")
                    self.logger.info(f"[TICK_CALC] {instrument_id} - 成交量计算: current_cumulative_volume({volume}) - last_volume({self.kline_min1_map[instrument_id].last_volume}) = 分钟成交量({calculated_volume})")
                    self.logger.info(f"[TICK_CALC] {instrument_id} - K线时间: {self.kline_min1_map[instrument_id].update_time}, tick时间: {tick.update_time}")

                bar = self.get_new_bar(self.kline_min1_map[instrument_id])
                if self.is_queue:
                    self.kline_queue.put(bar)
                else:
                    self.distribute_kline_without_queue(bar)

            self.kline_min1_map[instrument_id] = BarData()
            self.kline_min1_map[instrument_id].bar_type = Interval.MINUTE
            self.kline_min1_map[instrument_id].instrument_id = instrument_id
            self.kline_min1_map[instrument_id].exchange_id = tick.exchange_id  # 修复：设置交易所ID
            self.kline_min1_map[instrument_id].update_time = datetime.time(int(st[0]),
                                                                           int(st[1]), 0, 0)
            self.kline_min1_map[instrument_id].volume = volume
            self.kline_min1_map[instrument_id].open_interest = tick.open_interest
            self.kline_min1_map[instrument_id].open_price = open_price
            self.kline_min1_map[instrument_id].high_price = max(open_price, tick.last_price)
            self.kline_min1_map[instrument_id].low_price = min(open_price, tick.last_price)
            self.kline_min1_map[instrument_id].close_price = tick.last_price
            self.kline_min1_map[instrument_id].last_volume = volume
            # 【修复】初始化当前累计成交量字段
            self.kline_min1_map[instrument_id].current_cumulative_volume = volume
            
            # 🔍 调试：新K线初始化
            if instrument_id in ['lu2604', 'sp2606', 'sc2608']:
                self.logger.debug(f"[NEW_KLINE_DEBUG] {instrument_id} - 新K线初始化: volume={volume}, last_volume={volume}, open_price={open_price}, tick.volume={tick.volume}")
        else:
            # 如果不是新1分钟，更新相关数据
            old_volume = self.kline_min1_map[instrument_id].volume
            self.kline_min1_map[instrument_id].high_price = max(self.kline_min1_map[instrument_id].high_price, tick.last_price)
            self.kline_min1_map[instrument_id].low_price = min(self.kline_min1_map[instrument_id].low_price, tick.last_price)
            self.kline_min1_map[instrument_id].close_price = tick.last_price
            # 持仓量
            self.kline_min1_map[instrument_id].open_interest = tick.open_interest
            # 累计成交量
            self.kline_min1_map[instrument_id].volume = int(tick.volume)
            # 【修复】同时更新当前累计成交量字段
            self.kline_min1_map[instrument_id].current_cumulative_volume = int(tick.volume)
            
            # 调试：累计成交量更新（DEBUG级别，避免日志过多）
            self.logger.debug(f"[VOLUME_UPDATE] {instrument_id} - 累计成交量更新: {old_volume} -> "
                              f"{self.kline_min1_map[instrument_id].volume}, "
                              f"current_cumulative_volume={self.kline_min1_map[instrument_id].current_cumulative_volume} "
                              f"(tick.volume={tick.volume})")
        
        # 锁会在外层finally中自动释放

    def get_kline(self):
        # 获取所有类型分钟线，并进行分发
        self.logger.info("[GET_KLINE_THREAD] K线队列处理线程已启动")
        while True:
            try:
                kline: BarData = self.kline_queue.get()

                # 如果是无效数据，退出
                if self.clean_kline(kline):
                    self.logger.warning(
                        f"[CLEAN_KLINE_QUEUE] {kline.instrument_id} - K线数据无效被过滤: "
                        f"open={kline.open_price}, high={kline.high_price}, "
                        f"low={kline.low_price}, close={kline.close_price}, "
                        f"volume={kline.volume}, oi={kline.open_interest}, "
                        f"time={kline.update_time}"
                    )
                    continue

                self.logger.info(
                    f"[DISTRIBUTE_BAR_QUEUE] {kline.instrument_id} - 准备发布bar事件: "
                    f"bar_type={kline.bar_type}, time={kline.update_time}, "
                    f"open={kline.open_price}, close={kline.close_price}, volume={kline.volume}"
                )

                # 如果是1分钟K线，另需要分发到合成其他K线线程，合成其他K线
                if kline.bar_type == Interval.MINUTE:
                    self.min1_to_other_kline(kline)

                self.distribute_kline(kline)
            except Exception as e:
                self.logger.exception(f"[GET_KLINE_ERROR] K线队列处理异常: {e}")

    def _generate_kline_for_interval(self, kline: BarData, interval: Interval, 
                                   kline_map: dict, lock_map: dict) -> None:
        """
        通用的K线合成方法，减少代码重复
        :param kline: 输入的1分钟K线
        :param interval: 目标周期
        :param kline_map: 目标周期的K线字典
        :param lock_map: 目标周期的锁字典
        :return: None
        """
        lock_map[kline.instrument_id].acquire()
        instrument_id = ""
        try:
            instrument_id = kline.instrument_id
            
            # 检查是否是未初始化的空K线对象（非整点启动时会出现）
            is_empty_kline = (kline_map[instrument_id].open_price == 0.0 and 
                            kline_map[instrument_id].close_price == 0.0 and
                            kline_map[instrument_id].instrument_id == instrument_id)
            
            # 如果是新的K线周期 或 是第一次接收数据（空对象），生成一个新k线变量
            if self.is_new_kline_min(interval, kline.update_time) or is_empty_kline:
                kline_map[instrument_id] = BarData()
                kline_map[instrument_id].bar_type = interval
                kline_map[instrument_id].instrument_id = instrument_id
                kline_map[instrument_id].exchange_id = kline.exchange_id  # 修复：设置交易所ID
                kline_map[instrument_id].update_time = kline.update_time
                kline_map[instrument_id].volume = kline.volume
                kline_map[instrument_id].open_interest = kline.open_interest
                kline_map[instrument_id].open_price = kline.open_price
                kline_map[instrument_id].high_price = max(0.0, kline.high_price)
                kline_map[instrument_id].low_price = min(float('inf'), kline.low_price)
                kline_map[instrument_id].close_price = kline.close_price
            else:
                # 如果不是新K线，更新相关数据
                kline_map[instrument_id].high_price = max(kline_map[instrument_id].high_price, kline.high_price)
                kline_map[instrument_id].low_price = min(kline_map[instrument_id].low_price, kline.low_price)
                kline_map[instrument_id].close_price = kline.close_price
                # 持仓量
                kline_map[instrument_id].open_interest = kline.open_interest
                # 累计成交量
                kline_map[instrument_id].volume += kline.volume
            
            # 检查是否到了K线结束时间，如果是则推送
            if self.is_min_kline_end(interval, kline.update_time):
                bar = self.get_new_bar(kline_map[instrument_id])
                if self.is_queue:
                    self.kline_queue.put(bar)
                else:
                    self.distribute_kline_without_queue(bar)
                
        finally:
            lock_map[instrument_id].release()

    def distribute_kline_without_queue(self, kline):
        # 如果是无效数据，退出
        if BarGenerator.clean_kline(kline):
            self.logger.warning(
                f"[CLEAN_KLINE] {kline.instrument_id} - K线数据无效被过滤: "
                f"open={kline.open_price}, high={kline.high_price}, "
                f"low={kline.low_price}, close={kline.close_price}, "
                f"volume={kline.volume}, oi={kline.open_interest}, "
                f"time={kline.update_time}"
            )
            return

        # 如果是1分钟K线，另需要分发到合成其他K线线程，合成其他K线
        if kline.bar_type == Interval.MINUTE:
            self.min1_to_other_kline(kline)

        self.logger.info(
            f"[DISTRIBUTE_BAR] {kline.instrument_id} - 准备发布bar事件: "
            f"bar_type={kline.bar_type}, time={kline.update_time}, "
            f"open={kline.open_price}, close={kline.close_price}, volume={kline.volume}"
        )
        self.distribute_kline(kline)

    def min1_to_other_kline(self, kline: BarData):
        """
        一分钟生成其他周期K线
        :param kline:
        :return:
        """
        if kline.instrument_id in self.sub_kline_type_map.keys() and Interval.MINUTE3 in self.sub_kline_type_map[kline.instrument_id]:
            self.min1_to_min3(kline)
        if kline.instrument_id in self.sub_kline_type_map.keys() and Interval.MINUTE5 in self.sub_kline_type_map[kline.instrument_id]:
            self.min1_to_min5(kline)
        if kline.instrument_id in self.sub_kline_type_map.keys() and Interval.MINUTE15 in self.sub_kline_type_map[kline.instrument_id]:
            self.min1_to_min15(kline)
        if kline.instrument_id in self.sub_kline_type_map.keys() and Interval.MINUTE30 in self.sub_kline_type_map[kline.instrument_id]:
            self.min1_to_min30(kline)
        if kline.instrument_id in self.sub_kline_type_map.keys() and Interval.MINUTE60 in self.sub_kline_type_map[kline.instrument_id]:
            self.min1_to_min60(kline)

    def min1_to_min3(self, kline: BarData):
        """3分钟K线合成"""
        self._generate_kline_for_interval(kline, Interval.MINUTE3, 
                                        self.kline_min3_map, self.kline_min3_lock_map)

    def min1_to_min5(self, kline: BarData):
        """5分钟K线合成"""
        self._generate_kline_for_interval(kline, Interval.MINUTE5, 
                                        self.kline_min5_map, self.kline_min5_lock_map)

    def min1_to_min15(self, kline: BarData):
        """15分钟K线合成"""
        self._generate_kline_for_interval(kline, Interval.MINUTE15, 
                                        self.kline_min15_map, self.kline_min15_lock_map)

    def min1_to_min30(self, kline: BarData):
        """30分钟K线合成"""
        self._generate_kline_for_interval(kline, Interval.MINUTE30, 
                                        self.kline_min30_map, self.kline_min30_lock_map)

    def min1_to_min60(self, kline: BarData):
        """60分钟K线合成"""
        self._generate_kline_for_interval(kline, Interval.MINUTE60, 
                                        self.kline_min60_map, self.kline_min60_lock_map)

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
        """
        分发K线数据
        新架构：发布BAR事件到事件总线，由订阅的策略接收
        旧架构：直接调用strategy_map中的策略
        """
        # 新架构：使用事件总线发布BAR事件
        if self.event_bus:
            from src.core.event import Event
            self.event_bus.publish(
                Event.bar(
                    payload={"bar": kline}
                )
            )
            self.logger.debug(f"发布K线事件: {kline.instrument_id} {kline.bar_type.value} {kline.update_time}")
        else:
            # 旧架构：向后兼容，直接调用策略
            for strategy in constants.strategy_map.values():
                if kline.instrument_id in strategy.sub_ins_id and kline.bar_type in strategy.sub_kline_type:
                    self.save_kline(strategy, kline)

    @staticmethod
    def save_kline(strategy: BaseStrategy, kline: BarData):
        instrument_id = kline.instrument_id
        # 【修复】支持无锁模式,数据中心策略不需要锁
        if strategy.specific_strategy_map[instrument_id].kline_lock:
            # 有锁的情况:使用锁保护
            strategy.specific_strategy_map[instrument_id].kline_lock.acquire()
            try:
                strategy.specific_strategy_map[instrument_id].bar_data = kline
                strategy.specific_strategy_map[instrument_id].on_bar(kline)
            finally:
                strategy.specific_strategy_map[instrument_id].kline_lock.release()
        else:
            # 无锁的情况:直接调用(适用于数据中心策略)
            strategy.specific_strategy_map[instrument_id].bar_data = kline
            strategy.specific_strategy_map[instrument_id].on_bar(kline)

    @staticmethod
    # 如果是无效数据，则返回True
    def clean_kline(kline: BarData):
        if kline.instrument_id is None or kline.instrument_id == '':
            return True

        # 检查价格数据是否有效
        price_invalid = (kline.open_price == 0.0 or kline.high_price == 0.0 or 
                        kline.low_price == float('inf') or kline.low_price == 0.0 or 
                        kline.close_price == 0.0)
        
        # 检查基础数据是否有效
        basic_invalid = kline.open_interest == 0.0
        
        # 修复：在非交易时间，volume为0可能是正常的，不应仅因volume为0就判定为无效
        # 只有当价格数据或基础数据无效时才判定为无效K线
        if price_invalid or basic_invalid:
            time_log_detail('{} K线数据无效, update_time:{} (价格无效:{}, 基础数据无效:{})'.format(
                kline.instrument_id, kline.update_time, price_invalid, basic_invalid))
            time_log_detail("K线详细数据:")
            log_object(kline)
            return True
        
        # 如果只是volume为0但其他数据正常，则在调试模式下记录但不过滤
        if kline.volume == 0:
            time_log_detail('{} K线成交量为0, update_time:{} (非交易时间可能正常)'.format(
                kline.instrument_id, kline.update_time))
            time_log_detail("K线详细数据:")
            log_object(kline)
            # 【修复】注释说"不过滤"但代码返回True(过滤),改为False(不过滤)
            # 成交量为0在非交易时段是正常的,不应该过滤
            return False
        
        return False

    # def shutdown(self):
    #     """关闭BarGenerator，清理资源"""
    #     try:
    #         if hasattr(self, 'kline_executor') and self.kline_executor:
    #             self.logger.info("关闭K线处理线程池...")
    #             self.kline_executor.shutdown(wait=True)
    #             self.logger.info("K线处理线程池已关闭")
    #     except Exception as e:
    #         self.logger.error(f"关闭K线处理线程池失败: {e}")


    def clean_map(self):
        """完全清理所有K线数据"""
        # 订阅K线的合约名称和合约类型
        # self.sub_kline_id: list[str] = []
        # self.sub_kline_type: list[Interval] = []

        self.sub_kline_type_map: dict[str, Interval] = {}

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


if __name__ == '__main__':
    bar_generator = BarGenerator()
