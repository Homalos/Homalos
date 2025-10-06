#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : data_center.py
@Date       : 2025/9/13 23:10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据中心 - 业务层

职责：
管理数据中心的业务逻辑
管理网关连接和数据处理
"""
import datetime
import os
import threading
import time
from threading import Event as ThreadEvent
from threading import Thread
from typing import Optional, Any, TextIO, Callable

from src.api.bar_generator import BarGenerator
from src.constants import Const
from src.core.event import EventType, Event
from src.core.event_bus import EventBus
from src.core.object import TradingSchedule, TickData, SubscribeRequest
from src.modules.data_center.data_center_strategy import DataCenterStrategy
from src.modules.gateway.market_gateway import MarketGateway
from src.modules.gateway.trader_gateway import TraderGateway
from src.strategy.base_strategy import BaseStrategy
from src.strategy.strategy_pool import StrategyPool
from src.utils.alarm import Alarm
from concurrent.futures import ThreadPoolExecutor
from src.utils.log import get_logger


class DataCenter(object):

    def __init__(self, dc_config: dict[str, Any]) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self._alarm = Alarm()                                       # 使用单例模式的闹钟实例
        self._alarm_thread: Optional[Thread] = None                 # 闹钟线程实例
        self._alarm_stop_event: ThreadEvent = ThreadEvent()         # 闹钟线程控制
        self._alarm_stop_timeout: float = 3.0                       # 闹钟停止超时时间
        self._alarm_running: bool = False                           # 闹钟运行状态
        self._alarm_start_time: datetime = datetime.datetime.now()  # 闹钟开始时间
        self._alarm_last_execution_time: Optional[str] = None       # 防重复执行机制
        self._alarm_execution_lock: threading.Lock = threading.Lock()     # 执行锁
        self._alarm_execution_count: int = 0                        # 闹钟执行次数
        self._alarm_schedule: Optional[TradingSchedule] = None      # 闹钟调度器时间配置

        self.dc_event_bus: Optional[EventBus] = None                # 数据中心事件总线
        self._dc_config: dict[str, Any] = dc_config                  # 数据中心所有相关配置字典
        self.dc_running: bool = False                               # 数据中心运行状态

        self.bar_generator: BarGenerator = BarGenerator()           # 初始化K线合成系统
        self.bar_generation_interval: list = []
        self.strategy_pool: StrategyPool = StrategyPool()           # 策略池
        self.strategy_map: dict[str, BaseStrategy] = {}             # 初始化策略映射

        # 使用标准ThreadPoolExecutor
        self.thread_pool: Optional[ThreadPoolExecutor] = None
        self.thread_pools_initialized: bool = False

        self.market_gateway: Optional[MarketGateway] = None     # 行情网关
        self.trader_gateway: Optional[TraderGateway] = None     # 交易网关
        self.broker_config: dict[str, dict] = {}                # 服务器节点配置信息
        self.md_login_status: bool = False                      # 行情网关登录状态
        self.td_login_status: bool = False                      # 交易网关登录状态
        self.is_login_status: bool = False                      # 登录状态
        self.td_is_confirmed: bool = False                      # 是否确认过了结算单

        self.sub_all_ins: list[str] = []                # 所有订阅列表

        self.csv_file: Optional[TextIO] = None
        self.csv_writer = None

    def init_thread_pools(self) -> None:
        """初始化线程池"""
        try:
            if self.thread_pools_initialized:
                return

            self.logger.info("初始化线程池...")

            # 主线程池 - 处理调度任务（tick现在通过event_bus处理，无需专用线程池）
            self.thread_pool = ThreadPoolExecutor(
                max_workers=20,
                thread_name_prefix='DCWorker'
            )

            self.thread_pools_initialized = True
            self.logger.info("线程池初始化完成")

        except Exception as e:
            self.logger.exception(f"初始化线程池失败: {e}")
            # 即使失败也设置标志，避免无限等待
            self.thread_pools_initialized = True
            raise

    def _safe_submit_to_pool(self, pool: ThreadPoolExecutor, fn: Callable, *args, **kwargs) -> bool:
        """
        安全提交任务到线程池
        """
        try:
            # 检查线程池是否已初始化
            if pool is None or not self.thread_pools_initialized:
                self.logger.warning("线程池未初始化，延迟提交任务")
                # 延迟重试机制
                threading.Timer(1.0, lambda: self._safe_submit_to_pool(pool, fn, *args, **kwargs)).start()
                return False

            # 直接提交任务
            pool.submit(fn, *args, **kwargs)
            return True
        except Exception as e:
            self.logger.error(f"提交任务到线程池失败: {e}")
            return False

    # ================== 线程池优化方法 ==================
    def _close_all_csv_files(self) -> None:
        """
        强制关闭所有策略的CSV文件
        :return:
        """
        try:
            if self.strategy_map:
                for strategy in self.strategy_map.values():
                    for specific_strategy in strategy.specific_strategy_map.values():
                        try:
                            if specific_strategy.csv_file:
                                specific_strategy.csv_file.flush()
                                os.fsync(specific_strategy.csv_file.fileno())  # 确保数据写入磁盘
                                specific_strategy.csv_file.close()
                                specific_strategy.csv_file = None
                                specific_strategy.csv_writer = None
                        except Exception as e:
                            self.logger.exception(f"强制关闭CSV文件失败: {e}")
                self.logger.info("已强制关闭所有CSV文件")
        except Exception as e:
            self.logger.exception(f"强制关闭CSV文件过程失败: {e}")

    # ================== 业务相关方法 ==================

    def init_dc_config(self) -> None:
        """
        初始化数据中心配置信息
        :return:
        """
        now_time = datetime.datetime.now()
        t_login_time = now_time + datetime.timedelta(seconds=60)
        t_login = t_login_time.time().strftime('%H:%M')

        t_before_open_time = now_time + datetime.timedelta(seconds=120)
        t_before_open = t_before_open_time.time().strftime('%H:%M')

        t_sub_id_time = now_time + datetime.timedelta(seconds=180)
        t_sub = t_sub_id_time.time().strftime('%H:%M')

        login_times: list[str] = self._dc_config.get("login_times", [])
        login_times.append(t_login)
        before_open_times: list[str] = self._dc_config.get("before_open_times", [])
        before_open_times.append(t_before_open)
        sub_id_times: list[str] = self._dc_config.get("sub_id_times", [])
        sub_id_times.append(t_sub)
        after_close_times: list[str] = self._dc_config.get("after_close_times", [])
        check_interval: int = self._dc_config.get("check_interval", 60)

        self._alarm_schedule = TradingSchedule(
            login_times=login_times,
            before_open_times=before_open_times,
            sub_id_times=sub_id_times,
            after_close_times=after_close_times,
            check_interval=check_interval
        )
        self.logger.info("调度时间配置：")
        self.logger.info(f"登录: {self._alarm_schedule.login_times}")
        self.logger.info(f"开盘前: {self._alarm_schedule.before_open_times}")
        self.logger.info(f"订阅: {self._alarm_schedule.sub_id_times}")
        self.logger.info(f"收盘后: {self._alarm_schedule.after_close_times}")

        self.bar_generation_interval: list = self._dc_config.get("bar_generation_interval", [])
        self.logger.info(f"K线间隔配置：{self.bar_generation_interval}")

    def init_broker_config(self) -> None:
        """
        初始化broker节点配置
        :return:
        """
        broker_name = self._dc_config.get("broker_name", "")
        broker_type = self._dc_config.get("broker_type", "")
        self.broker_config = self._dc_config.get("broker", "")
        self.logger.info(f"启用的broker名称: {broker_name}，broker类型: {broker_type}")

    def init_dc_event_bus(self) -> None:
        # 初始化事件总线，优化为tick处理专用配置
        self.dc_event_bus: EventBus = EventBus(
            context="DataCenter",
            market_max_workers=5000,        # 提升到5K，专门处理高频tick
            market_add_max_workers=300,     # 大幅提升扩容能力到300
            general_max_workers=1000,       # 普通事件处理保持不变
            general_add_max_workers=50,
            register_signals=False
        )
        self.logger.info("数据中心EventBus实例创建成功")

        # 订阅行情网关登录事件
        self.dc_event_bus.subscribe(EventType.MD_GATEWAY_LOGIN, self._md_login_handler)
        # 订阅交易网关登录事件
        self.dc_event_bus.subscribe(EventType.TD_GATEWAY_LOGIN, self._td_login_handler)

        # 首次底层会发布确认结算单事件，如果断开重连交易网关，底层不再确认结算单
        # 订阅结算单确认成功事件
        self.dc_event_bus.subscribe(EventType.TD_CONFIRM_SUCCESS, self._td_confirm_handler)

        # 订阅交易网关已经确认结算单事件
        self.dc_event_bus.subscribe(EventType.TD_ALREADY_CONFIRMED, self._td_already_confirmed_handler)

        # 订阅交易网关查询合约事件
        self.dc_event_bus.subscribe(EventType.TD_QRY_INS, self._td_qry_ins_handler)

        # 恢复事件总线的tick订阅作为主要机制
        self.dc_event_bus.subscribe(EventType.TICK, self._get_tick)

        # 订阅事件总线停止事件
        self.dc_event_bus.subscribe(EventType.EVENT_BUS_SHUTDOWN, self.shutdown_dc)

    def _md_login_handler(self, event: Event) -> None:
        """
        处理行情登录事件
        :param event: 行情网关登录事件
        :return:
        """
        rsp_md_login_data: dict = event.payload
        self.logger.info(f"收到行情网关登录事件返回信息：{rsp_md_login_data}")
        if rsp_md_login_data and rsp_md_login_data.get("code") == 0:
            # 行情登录成功
            self.md_login_status = True
            self.logger.info(rsp_md_login_data.get("message"))
            
            # 如果行情登录前已有订阅列表（重连情况），立即重新订阅所有合约
            if self.sub_all_ins and len(self.sub_all_ins) > 0:
                self.logger.info(f"检测到行情网关重连，自动重新订阅 {len(self.sub_all_ins)} 个合约")
                self._subscribe_all_instruments()
        else:
            # 行情登录失败
            self.md_login_status = False
            self.logger.info(rsp_md_login_data.get("message"))

    def _td_login_handler(self, event: Event) -> None:
        """
        处理交易登录事件
        :param event: 交易网关登录事件
        :return:
        """
        rsp_td_login_data = event.payload
        self.logger.info(f"收到交易网关登录事件返回信息：{rsp_td_login_data}")
        if rsp_td_login_data and rsp_td_login_data.get("code") == 0:
            # 登录成功的标志存放在确认结算单响应函数中，因为确认过结算单后，才可以进行其他操作。
            # 如果已经确认过结算单，则直接设置登录交易成功(有时断开重连后不再需要再次确认结算单后才算登录成功)
            self.logger.info(rsp_td_login_data.get("message"))
            # 获取登录后的交易日填充到全局变量trading_day中
            Const.trading_day = rsp_td_login_data.get("data", {}).get("trading_day")
        else:
            # 如果登录失败，则将结算单和登录标志都设置为False(登录失败了结算单也无法进行确认)
            self.td_is_confirmed = False
            self.td_login_status = False
            # 登录失败
            self.logger.warning(rsp_td_login_data.get("message"))

    def _td_confirm_handler(self, event: Event):
        """
        处理交易确认结算单事件
        :param event: 交易网关确认结算单事件
        :return:
        """
        rsp_td_confirm_data = event.payload
        self.logger.info(f"收到交易网关确认结算单事件返回信息：{rsp_td_confirm_data}")
        if rsp_td_confirm_data and rsp_td_confirm_data.get("code") == 0:
            self.td_is_confirmed = True
            self.td_login_status = True
            self.logger.info(rsp_td_confirm_data.get("message"))

            # 首次确认结算单后，发送查询合约事件
            self._publish_qry_ins()
            
            # 此处必须等待等待定时任务，因为订阅合约的前提的需要更新完所有合约代码
            # 合约代码存储在config/instrument_exchange.json文件中，订阅时从此文件加载合约代码

    def _td_already_confirmed_handler(self, event: Event):
        """
        处理交易网关已经确认结算单事件
        :param event: 已经确认结算单事件
        :return:
        """
        rsp_td_already_confirmed_data = event.payload
        self.logger.info(f"收到交易网关已经确认结算单事件返回信息：{rsp_td_already_confirmed_data}")
        if rsp_td_already_confirmed_data and rsp_td_already_confirmed_data.get("code") == 0:
            self.td_is_confirmed = True
            self.td_login_status = True
            self.logger.info(rsp_td_already_confirmed_data.get("message"))

    def _td_qry_ins_handler(self, event: Event):
        """
        处理交易网关查询合约事件
        :param event: 交易网关查询合约事件
        :return:
        """
        rsp_td_ready_data = event.payload
        self.logger.info(f"收到交易网关查询合约事件返回信息：{rsp_td_ready_data}")
        if rsp_td_ready_data and rsp_td_ready_data.get("code") == 0:
            self.logger.info(rsp_td_ready_data.get("message"))
            # 初始化策略
            self.init_strategies()

            self.strategy_pool.init_sub_id()
            self.strategy_pool.init_kline_type()

            # 初始化订阅合约
            self.init_sub_instruments()

            # 此处必须等待等待定时任务，因为订阅合约的前提的需要更新完所有合约代码
            # 合约代码存储在config/instrument_exchange.json文件中，订阅时从此文件加载合约代码

    def init_strategies(self) -> None:
        """初始化数据中心策略"""
        self.logger.info("初始化数据中心策略...")
        dc_strategy: DataCenterStrategy = DataCenterStrategy()
        self.strategy_pool.add_strategy(dc_strategy.strategy_id, dc_strategy)
        self.strategy_map = {dc_strategy.strategy_id: dc_strategy}
        
        # 【关键修复】将策略同步到全局 strategy_map
        from src import constants
        constants.strategy_map = self.strategy_map
        
        self.logger.info("成功初始化数据中心策略")

    def init_sub_instruments(self) -> None:
        """
        初始化策略需要订阅的合约，登录更新合约结束后进行此操作
        :return:
        """
        self.logger.info("初始化订阅合约...")
        if self.strategy_map:
            for strategy in self.strategy_map.values():
                # 获取策略所有需要订阅的合约
                self.sub_all_ins = list(set(strategy.sub_ins_id))

                # 添加订阅的K线类型
                if strategy.sub_kline_type:
                    # self.bar_generator.add_sub_kline_id(strategy.sub_ins_id)
                    # self.bar_generator.add_sub_kline_type(strategy.sub_kline_type)
                    self.bar_generator.set_kline_type(self.strategy_pool.sub_kline_type)

            self.bar_generator.init_min_kline_map()

        self.logger.info("成功初始化订阅合约")
        self.logger.info(f"需要订阅的合约数量：{len(self.sub_all_ins)}")

    def _get_tick(self, event: Event) -> None:
        """
        优化tick处理方法
        """
        if event.payload.get("code") == 0:
            # 从tick行情事件中获取tick对象
            try:
                tick: TickData = event.payload.get("data")
                if tick:
                    # 直接处理tick，避免额外的事件或队列操作
                    self._distribute_tick(tick)

            except Exception as e:
                self.logger.error(f"tick处理异常: {e}")

    def _distribute_tick(self, tick: TickData) -> None:
        """
        直接分发tick数据到策略
        """
        # 传递tick到策略
        for strategy_id, strategy in self.strategy_map.items():
            if tick.instrument_id in strategy.sub_ins_id:
                try:
                    strategy.specific_strategy_map[tick.instrument_id].on_tick(tick)
                except Exception as e:
                    self.logger.error(f"策略 {strategy_id} 处理合约 {tick.instrument_id} tick异常: {e}")

        # tick合成K线
        if tick.instrument_id in self.bar_generator.sub_kline_type_map.keys():
            self.bar_generator.tick_to_kline(tick)

    def init_gateway(self) -> None:
        """
        初始化行情网关和交易网关(在初始化事件总线后进行)
        :return:
        """
        self.market_gateway = MarketGateway(self.dc_event_bus, gateway_name="Data_Center_MD")
        self.trader_gateway = TraderGateway(self.dc_event_bus, gateway_name="Data_Center_TD")
        
        broker_info: dict = self._dc_config.get('broker', {})
        self.broker_config: dict = broker_info.get('broker_config', {})

    def _connect_gateway(self) -> bool:
        """
        登录行情和交易服务器，登录成功视为数据中心启动成功(何时进行登录由闹钟调度器根据配置时间来调度)
        :return:
        """
        # 连接行情服务器并登录
        if self.market_gateway:
            self.market_gateway.connect(self.broker_config)

        if self.trader_gateway:
            # 连接交易服务器并登录
            self.trader_gateway.connect(self.broker_config)

        start_time: float = time.time()
        timeout: float = 60.0  # 登录超时时间

        while not (self.md_login_status and self.td_login_status):
            # 检查是否超时
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                self.logger.warning(
                    f"等待登录超时 ({timeout}秒)，当前状态 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
                break
            time.sleep(1)

        if not self.md_login_status or not self.td_login_status:
            self.logger.error(f"网关登录失败 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
            self.is_login_status = False
            self.dc_running = False

            # self.dc_event_bus.publish(Event(EventType.DATA_CENTER_START, {
            #     "code": ErrorCode.DATA_CENTER_START_FAILED,
            #     "message": "数据中心启动失败",
            #     "data": None
            # }))
            return False

        self.is_login_status = True     # 设置登录状态为True
        self.dc_running = True          # 设置数据中心运行状态为True
        self.logger.info(f"所有网关登录成功 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
        self.logger.info("数据中心启动成功")

        # # 发布数据中心启动事件(成功)
        # self.dc_event_bus.publish(Event(EventType.DATA_CENTER_START, {
        #     "code": ErrorCode.SUCCESS,
        #     "message": "数据中心启动成功",
        #     "data": None
        # }))

        # # 登录成功后发送查询合约事件
        # self._publish_qry_ins()

        return True

    def _publish_qry_ins(self) -> None:
        """
        向底层交易网关发布更新合约事件，交易网关完成登录就会自动更新合约信息
        :return:
        """
        if self.dc_event_bus:
            self.dc_event_bus.publish(Event(EventType.DATA_CENTER_QRY_INS, {}))
            self.logger.info("发布更新合约事件成功")

    # ================== 关闭和清理优化 ==================

    def shutdown_dc(self, event: Optional[Event] = None) -> None:
        """
        关闭数据中心，确保线程池正确关闭
        :return: None
        """
        if not self.dc_running:
            self.logger.info("数据中心未在运行")
            return

        if event:
            self.logger.info("收到数据总心关闭事件")

        self.logger.info("停止数据中心...")

        # 1. 先停止闹钟
        self.stop_alarm()

        # 2. 关闭所有CSV文件
        self._close_all_csv_files()

        # # 3. 关闭K线生成器
        # try:
        #     if hasattr(self, 'bar_generator') and self.bar_generator:
        #         self.bar_generator.shutdown()
        # except Exception as e:
        #     self.logger.error(f"关闭K线生成器失败: {e}")

        try:
            # 4. 停止网关
            if self.market_gateway:
                self.market_gateway.close()
                self.market_gateway = None

            if self.trader_gateway:
                self.trader_gateway.close()
                self.trader_gateway = None

            # 5. 停止事件总线
            if self.dc_event_bus:
                self.dc_event_bus.stop()

            # 6. 最后关闭线程池
            self._shutdown_thread_pools()

            self.dc_running = False
            self.logger.info("数据中心已关闭")
        except Exception as e:
            self.logger.error(f"数据中心关闭失败: {e}")

    def _shutdown_thread_pools(self) -> None:
        """
        安全关闭所有线程池
        """
        self.logger.info("开始关闭线程池...")

        # 关闭主线程池（tick现在通过event_bus处理）
        if hasattr(self, 'thread_pool') and self.thread_pool:
            try:
                self.logger.info("关闭主线程池...")
                self.thread_pool.shutdown(wait=True)
                self.logger.info("主线程池已关闭")
            except Exception as e:
                self.logger.error(f"关闭主线程池失败: {e}")

        self.logger.info("所有线程池关闭完成")

    # ================== 闹钟调度器方法 ==================

    def start_alarm(self) -> bool:
        """
        启动闹钟调度器
        """
        if self._alarm_running:
            self.logger.warning("闹钟调度器已在运行中")
            return True

        try:
            self._alarm_stop_event.clear()
            self._alarm_running = True
            # 创建并启动守护线程
            self._alarm_thread = Thread(
                target=self._alarm_loop,
                name="AlarmScheduler",
                daemon=True
            )
            self._alarm_thread.start()
            self.logger.info("闹钟调度器启动成功")
            return True
        except Exception as e:
            self._alarm_running = False
            self.logger.exception(f"启动闹钟调度器失败: {e}")
            return False

    def _alarm_loop(self) -> None:
        """
        主闹钟循环 - 在独立线程中运行
        """
        self.logger.info("闹钟循环开始运行")
        loop_count = 0

        # 简化初始化检查 - 最多等待5秒
        max_wait_time: float = 5.0
        wait_interval: float = 0.5
        waited_time: float = 0.0

        while waited_time < max_wait_time:
            if self.thread_pools_initialized:
                self.logger.info("线程池已初始化，开始正常循环")
                break
            time.sleep(wait_interval)
            waited_time += wait_interval
            if waited_time % 1 == 0:  # 每秒输出一次
                self.logger.info(f"等待线程池初始化... {waited_time:.1f}s")
        else:
            self.logger.warning(f"线程池初始化等待超时({max_wait_time}s)，强制继续运行")

        # 无论线程池是否初始化完成，都开始正常循环
        while not self._alarm_stop_event.is_set():
            try:
                loop_count += 1
                current_time = datetime.datetime.now()

                # 只在整分钟输出调试信息
                if current_time.second == 0:
                    self.logger.debug(f"[LOOP] 第{loop_count}次 - {current_time.strftime('%H:%M:%S')}")

                # 提交检查任务
                self._submit_check_task_safely(current_time)

                # 计算到下一分钟的睡眠时间
                sleep_time = 60 - current_time.second
                if sleep_time <= 0:
                    sleep_time = 1

                # 等待
                self._alarm_stop_event.wait(timeout=min(sleep_time, 60))

            except Exception as e:
                self.logger.exception(f"闹钟循环异常: {e}")
                time.sleep(5)  # 异常时等待5秒

        self.logger.info("闹钟循环结束")

    def _submit_check_task_safely(self, current_time) -> None:
        """安全提交检查任务"""
        try:
            # 检查线程池状态
            if not self.thread_pools_initialized or not self.thread_pool or self.thread_pool is None:
                self.logger.warning("线程池未就绪，跳过本次检查")
                return

            # 检查线程池是否已关闭
            if hasattr(self.thread_pool, '_shutdown') and self.thread_pool._shutdown:
                self.logger.warning("线程池已关闭，跳过任务提交")
                return

            # 提交检查任务
            self.thread_pool.submit(self._check_alarms)

            if current_time.second == 0:
                self.logger.debug("整点检查任务提交成功")

        except RuntimeError as e:
            if "cannot schedule new futures after interpreter shutdown" in str(e):
                self.logger.warning("解释器正在关闭，跳过任务提交")
                self._alarm_stop_event.set()  # 停止闹钟循环
            else:
                self.logger.exception(f"提交检查任务失败: {e}")
        except Exception as e:
            self.logger.exception(f"提交检查任务异常: {e}")

    def _check_alarms(self) -> None:
        """
        检查并执行闹钟任务
        """
        try:
            current_time_str = datetime.datetime.now().strftime('%H:%M')
            self.logger.debug(f"[CHECK] 开始检查 - {current_time_str}")

            # 防止重复执行同一分钟的任务（使用更严格的时间判断）
            if current_time_str == self._alarm_last_execution_time:
                self.logger.debug(f"[CHECK] 跳过重复执行 - {current_time_str}")
                return

            # 确保同一时间只有一个检查在执行（使用锁机制）
            if not self._alarm_execution_lock.acquire(blocking=False):
                self.logger.debug(f"[CHECK] 跳过锁定状态 - {current_time_str}")
                return

            try:
                self.logger.debug(f"[CHECK] 执行检查 - {current_time_str}")
                self._alarm_execution_count += 1
                self._alarm_last_execution_time = current_time_str

                # 检查系统预定义时间点
                self._check_system_events(current_time_str)

                self.logger.debug(f"[CHECK] 检查完成 - {current_time_str}")
            finally:
                self._alarm_execution_lock.release()

        except Exception as e:
            self.logger.exception(f"检查闹钟异常: {e}")
            # 确保异常时释放锁
            try:
                self._alarm_execution_lock.release()
            except RuntimeError:
                pass

    def _check_custom_alarms(self, current_time: str) -> None:
        """
        检查用户自定义闹钟
        :param current_time: 当前时间字符串
        """
        if self._alarm.time_in_alarm(current_time):
            self.logger.info(f"触发自定义闹钟: {current_time}")
            try:
                strategy_ids = self._alarm.get_strategy_ids(current_time)

                for strategy_id in strategy_ids:
                    if not strategy_id:
                        continue

                    strategy_key = strategy_id
                    if strategy_key not in self.strategy_map:
                        self.logger.warning(f"策略 {strategy_id} 不存在")
                        continue

                    strategy = self.strategy_map[strategy_key]

                    # 线程不为None执行
                    if self.thread_pool:
                        # 执行策略闹钟回调
                        for instrument_id in strategy.sub_ins_id:
                            specific_strategy = strategy.specific_strategy_map[instrument_id]
                            self.thread_pool.submit(
                                specific_strategy.on_alarm
                            )
            except Exception as e:
                self.logger.exception(f"执行自定义闹钟失败: {e}")

    def _safe_execute_callback(self, callback: Callable, *args, **kwargs) -> None:
        """
        安全执行回调函数
        :param callback: 要执行的回调函数
        :param description: 回调描述
        :param args: 传递给回调函数的位置参数
        :param kwargs: 传递给回调函数的关键字参数
        """
        # 获取回调函数的名称作为描述
        description = getattr(callback, '__name__', str(callback))
        try:
            # 执行回调函数，传递所有参数
            callback(*args, **kwargs)
            self.logger.debug(f"{description} 执行成功")
        except Exception as e:
            self.logger.exception(f"{description} 执行失败: {e}")

    def _check_system_events(self, current_time: str) -> None:
        """
        系统事件检查
        :param current_time: 当前时间字符串
        """
        self.logger.debug("[SYSTEM_EVENTS] 开始检查系统事件")

        if self.thread_pool:
            self.logger.info("[KLINE_CHECK] 触发K线生成任务")
            # 执行K线任务（提交到线程池）
            self._safe_submit_to_pool(self.thread_pool, self.bar_generator.check_min1)
        
        # 执行每分钟任务（直接执行，不提交到线程池）
        self._one_min(current_time)

        # 执行登录服务器
        self.logger.debug(f"[LOGIN_CHECK] 登录时间配置: {self._alarm_schedule.login_times}")
        if self._alarm_schedule and current_time in self._alarm_schedule.login_times:
            self.logger.info("触发登录")
            self._connect_gateway()

        # 登录成功、线程不为None、alarm_schedule不为None执行的任务
        if self.is_login_status and self.thread_pool and self._alarm_schedule:
            # 执行开盘前
            self.logger.debug(f"[BEFORE_OPEN_CHECK] 开盘前时间配置: {self._alarm_schedule.before_open_times}")
            if current_time in self._alarm_schedule.before_open_times:
                self.logger.info("触发开盘前")
                # 使用安全提交方法
                self._safe_submit_to_pool(self.thread_pool, self._before_open)

            # 执行订阅行情
            self.logger.debug(f"[SUB_CHECK] 订阅时间配置: {self._alarm_schedule.sub_id_times}")
            if current_time in self._alarm_schedule.sub_id_times:
                self.logger.info("触发订阅所有行情")
                self._subscribe_all_instruments()

            # 收盘后事件
            self.logger.debug(f"[AFTER_CLOSE_CHECK] 收盘后时间配置: {self._alarm_schedule.after_close_times}")
            if current_time in self._alarm_schedule.after_close_times:
                self.logger.info("触发收盘后事件")
                # 使用安全提交方法
                self._safe_submit_to_pool(self.thread_pool, self._after_close)
            
        self.logger.debug(f"[SYSTEM_EVENTS] 系统事件检查完成")

    def _subscribe_all_instruments(self) -> None:
        """
        合约订阅方法，分批订阅避免阻塞
        """
        self.logger.info(f"开始订阅 {len(self.sub_all_ins)} 个合约...")

        if self.market_gateway:
            for index, ins in enumerate(self.sub_all_ins):
                self.market_gateway.subscribe(SubscribeRequest(ins))
                self.logger.info(f"已订阅 {index} 个合约...")

        self.logger.info("所有合约订阅完成")

    def _one_min(self, time_now: str):
        """
        优化一分钟任务执行，避免递归提交
        """
        try:
            if self.strategy_map:
                # 直接执行，避免在线程池任务中再次提交到线程池
                for strategy in self.strategy_map.values():
                    try:
                        # 对于一分钟任务，直接执行而不是提交到线程池
                        # 避免在线程池任务内部再提交任务导致的潜在死锁
                        # 直接调用，避免线程池死锁（在线程池任务内部再提交任务会导致死锁）
                        strategy.one_min(time_now)
                    except Exception as e:
                        self.logger.exception(f"执行策略 {strategy.strategy_id} 一分钟任务失败: {e}")
        except Exception as e:
            self.logger.exception(f"_one_min 方法执行异常: {e}")

    def _before_open(self) -> None:
        """处理开盘前事件"""
        self.logger.info("执行开盘前事件检测...")
        if self.thread_pool and self.strategy_map:
            for strategy in self.strategy_map.values():
                # 对于数据中心策略，只需要在策略级别执行一次开盘前事件
                self.logger.info(f"为策略 {strategy.strategy_id} 执行开盘前事件")
                self.thread_pool.submit(
                    self._execute_before_open,
                    strategy
                )

    def _execute_before_open(self, strategy) -> None:
        """
        执行数据中心策略的开盘前事件（策略级别，而非每个合约）
        :param strategy: 数据中心策略实例
        """
        try:
            self.logger.info(f"数据中心策略 {strategy.strategy_id} 开盘前事件开始")
            # 数据中心策略的开盘前逻辑可以在这里实现
            # 例如：准备数据存储目录、初始化文件等
            for instrument_id in strategy.sub_ins_id:
                if instrument_id in strategy.specific_strategy_map:
                    strategy.specific_strategy_map[instrument_id].on_before_open()
        except Exception as e:
            self.logger.exception(f"数据中心策略开盘前事件执行失败: {e}")

    def _after_close(self) -> None:
        """处理收盘后事件"""
        self.logger.info("执行收盘后退出事件")
        if self.thread_pool and self.strategy_map:
            for strategy in self.strategy_map.values():
                # 对于数据中心策略，只需要在策略级别执行一次收盘后事件
                self.logger.info(f"为策略{strategy.strategy_id}执行收盘后事件")
                self.thread_pool.submit(
                    self._execute_after_close,
                    strategy
                )

    def _execute_after_close(self, strategy) -> None:
        """
        执行数据中心策略的收盘后事件（策略级别，而非每个合约）
        :param strategy: 数据中心策略实例
        """
        try:
            # 数据中心策略的收盘后逻辑可以在这里实现
            # 例如：关闭文件、清理资源等
            for instrument_id in strategy.sub_ins_id:
                if instrument_id in strategy.specific_strategy_map:
                    strategy.specific_strategy_map[instrument_id].on_after_close()
        except Exception as e:
            self.logger.exception(f"数据中心策略收盘后事件执行失败: {e}")

    def is_alarm_running(self) -> bool:
        """检查调度器是否正在运行"""
        return self._alarm_running

    def stop_alarm(self, timeout: float = 10.0) -> None:
        """
        停止闹钟调度器
        :param timeout: 等待超时时间（秒）
        """
        if not self._alarm_running:
            return

        self.logger.info("正在停止闹钟调度器...")

        # 1. 设置停止标志
        self._alarm_stop_event.set()
        self._alarm_running = False

        # 2. 等待闹钟线程结束
        if self._alarm_thread and self._alarm_thread.is_alive():
            self._alarm_thread.join(timeout=timeout)
            if self._alarm_thread.is_alive():
                self.logger.warning("闹钟线程未能在指定时间内停止")
            else:
                self.logger.info("闹钟调度器已停止")

        self.logger.info("闹钟停止完成")

    # ================== 新增监控方法 ==================

    def get_thread_pool_status(self) -> dict:
        """
        获取线程池状态信息 - 优化统计逻辑
        """
        try:
            # 获取事件总线tick队列状态
            tick_queue_status = {}
            if self.dc_event_bus:
                try:
                    tick_queue_status = self.dc_event_bus.get_tick_queue_status()
                except Exception as e:
                    tick_queue_status = {'error': f'获取tick队列状态失败: {e}'}

            status: dict[str, Any] = {
                'thread_pools_initialized': self.thread_pools_initialized,
                'alarm_running': self._alarm_running,
                'dc_running': self.dc_running,
                'tick_statistics': {
                    'processing_mode': '实时处理',
                    'event_bus_queue': tick_queue_status
                },
                'alarm_status': {
                    'running': self._alarm_running,
                    'execution_count': self._alarm_execution_count
                }
            }

            # 线程池状态：显示当前积压情况而非累计完成率
            if self.thread_pool:
                # 简化主线程池状态监控
                status['main_pool'] = {
                    'max_workers': self.thread_pool._max_workers,
                    'executor_type': 'ThreadPoolExecutor',
                    'status': '运行中'
                }
            else:
                status['main_pool'] = {'error': '线程池未初始化'}

            # tick处理现在通过event_bus进行，无需专用线程池
            status['tick_processing'] = {
                'mode': '通过event_bus实时处理',
                'status': '正常运行'
            }

            return status
        except Exception as e:
            return {'error': f'获取状态失败: {str(e)}'}
