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

from src.constants import Const
from src.core.constants import ErrorCode
from src.core.event import EventType, Event
from src.core.event_bus import EventBus
from src.core.object import TradingSchedule, TickData, SubscribeRequest
from src.modules.data_center.data_center_strategy import DataCenterStrategy
from src.modules.function.bar_generator import BarGenerator
from src.modules.gateway.market_gateway import MarketGateway
from src.modules.gateway.trader_gateway import TraderGateway
from src.strategy.base_strategy import BaseStrategy
from src.utils.alarm import Alarm
from src.utils.homalos_thread_pool import HomalosThreadPool
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
        self._total_tick_count: int = 0                             # tick数据总数

        self.bar_generator: BarGenerator = BarGenerator()           # 初始化K线合成系统
        self.bar_generation_interval: list = []
        self.strategy_map: dict[str, BaseStrategy] = {}             # 初始化策略映射

        # 修改线程池初始化，但不立即启动
        self.thread_pool: Optional[HomalosThreadPool] = None
        self.tick_thread_pool: Optional[HomalosThreadPool] = None
        self.thread_pools_initialized: bool = False

        self.market_gateway: Optional[MarketGateway] = None     # 行情网关
        self.trader_gateway: Optional[TraderGateway] = None     # 交易网关
        self.broker_config: dict[str, dict] = {}                # 服务器节点配置信息
        self.md_login_status: bool = False                      # 行情网关登录状态
        self.td_login_status: bool = False                      # 交易网关登录状态

        # 是否更新合约，更新所有上市合约到instrument_exchange.json文件中，每次只在开盘盘时更新一次
        self.is_update_ins: bool = True
        self.is_update_ins_completed: bool = False      # 是否更新合约完成

        self.sub_all_ins: list[str] = []                # 所有订阅列表

        self.csv_file: Optional[TextIO] = None
        self.csv_writer = None

        # 新增：tick处理统计和流量控制
        self._tick_counter = 0
        self._tick_rate_limit = 10000  # 每秒最大tick处理数 (从1000提升到10000)
        self._last_tick_time = time.time()
        self._tick_queue_size = 0
        self._max_queue_size = 20000  # 最大队列积压 (从5000提升到20000)
        self._last_health_check_time = 0  # 上次健康检查时间
        self._health_check_interval = 1.0  # 健康检查间隔（秒）
        
        # 批量处理相关配置 - 适应低频行情
        self._tick_batch_size = 1   # 立即处理每个tick，不等待批量
        self._tick_batch_timeout = 0.1  # 100毫秒超时，确保及时处理
        self._tick_batch_queue: list[TickData] = []  # 批处理队列
        self._last_batch_time = time.time()  # 上次批处理时间
        self._batch_lock = threading.Lock()  # 批处理锁

    def init_thread_pools(self) -> None:
        """初始化线程池"""
        try:
            if self.thread_pools_initialized:
                return

            self.logger.info("初始化线程池...")

            # 主线程池 - 处理调度任务
            self.thread_pool = HomalosThreadPool(
                max_workers=20,
                thread_name_prefix='DCWorker'
            )
            self.thread_pool.start()

            # Tick处理线程池 - 专门处理高频tick数据
            self.tick_thread_pool = HomalosThreadPool(
                max_workers=1500,  # 从800增加到1500，配合更大的队列
                thread_name_prefix='DCTickWorker'
            )
            self.tick_thread_pool.start()

            self.thread_pools_initialized = True
            self.logger.info("线程池初始化完成")

        except Exception as e:
            self.logger.exception(f"初始化线程池失败: {e}")
            # 即使失败也设置标志，避免无限等待
            self.thread_pools_initialized = True
            raise

    def _check_thread_pool_health(self) -> bool:
        """
        检查线程池健康状态
        """
        try:
            # 检查线程池是否已初始化
            if not self.thread_pools_initialized:
                return False

            # 检查队列积压情况 (从80%放宽到95%)
            if self._tick_queue_size > self._max_queue_size * 0.95:
                self.logger.warning(f"Tick队列积压严重: {self._tick_queue_size}/{self._max_queue_size}")
                return False

            # 检查线程池状态
            if self.thread_pool and self.tick_thread_pool:
                tick_pool_progress = self.tick_thread_pool.get_progress()
                main_pool_progress = self.thread_pool.get_progress()
                self.logger.debug(f"线程池状态 - Tick池: {tick_pool_progress}, 主池: {main_pool_progress}")
                return True

            return False
        except Exception as e:
            self.logger.error(f"检查线程池健康状态失败: {e}")
            return False

    def _safe_submit_to_pool(self, pool: HomalosThreadPool, fn: Callable, *args, **kwargs) -> bool:
        """
        安全提交任务到线程池，带有优化的流量控制
        """
        try:
            # 检查线程池是否已初始化
            if pool is None or not self.thread_pools_initialized:
                self.logger.warning("线程池未初始化，延迟提交任务")
                # 延迟重试机制
                threading.Timer(1.0, lambda: self._safe_submit_to_pool(pool, fn, *args, **kwargs)).start()
                return False

            current_time = time.time()
            
            # 定期检查线程池健康状态（减少检查频率）
            if current_time - self._last_health_check_time >= self._health_check_interval:
                if not self._check_thread_pool_health():
                    self.logger.warning("线程池不健康，拒绝新任务")
                    return False
                self._last_health_check_time = current_time

            # 流量控制：检查tick处理速率
            if current_time - self._last_tick_time < 1.0 and self._tick_counter > self._tick_rate_limit:
                # 降低日志频率，避免日志刷屏
                if self._tick_counter % 1000 == 0:
                    self.logger.warning("达到tick处理速率限制，丢弃tick")
                return False

            # 提交任务
            pool.submit(fn, *args, **kwargs)
            self._tick_counter += 1
            self._tick_queue_size += 1

            # 重置计数器
            if current_time - self._last_tick_time >= 1.0:
                self._tick_counter = 0
                self._last_tick_time = current_time

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

        t_close_time = now_time + datetime.timedelta(seconds=480)
        t_close = t_close_time.time().strftime('%H:%M')

        login_times: list[str] = self._dc_config.get("login_times", [])
        login_times.append(t_login)
        before_open_times: list[str] = self._dc_config.get("before_open_times", [])
        before_open_times.append(t_before_open)
        sub_id_times: list[str] = self._dc_config.get("sub_id_times", [])
        sub_id_times.append(t_sub)
        after_close_times: list[str] = self._dc_config.get("after_close_times", [])
        after_close_times.append(t_close)
        check_interval: int = self._dc_config.get("check_interval", 60)

        self._alarm_schedule = TradingSchedule(
            login_times=login_times,
            before_open_times=before_open_times,
            sub_id_times=sub_id_times,
            after_close_times=after_close_times,
            check_interval=check_interval
        )
        self.logger.info(f"调度时间配置：")
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
        # 初始化事件总线，增加队列容量以处理高频tick数据
        self.dc_event_bus: EventBus = EventBus(
            context="DataCenter",
            market_max_workers=3000,        # 增加market线程池到3K
            market_add_max_workers=100,
            general_max_workers=1000,       # 普通事件处理
            general_add_max_workers=50,
            register_signals=False
        )
        self.logger.info("数据中心EventBus实例创建成功")

        # 订阅行情网关登录事件
        self.dc_event_bus.subscribe(EventType.MD_GATEWAY_LOGIN, self._md_login_handler)
        # 订阅交易网关登录事件
        self.dc_event_bus.subscribe(EventType.TD_GATEWAY_LOGIN, self._td_login_handler)

        # 首次底层会发布确认结算单事件，如果断开重连交易网关，底层不再确认结算单
        if self.is_update_ins:
            # 订阅结算单确认成功事件
            self.dc_event_bus.subscribe(EventType.TD_CONFIRM_SUCCESS, self._td_confirm_handler)
        else:
            # 订阅交易网关就绪事件
            self.dc_event_bus.subscribe(EventType.TD_GATEWAY_READY, self._td_ready_handler)

        # 订阅行情数据
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

    def _td_login_handler(self, event: Event) -> None:
        """
        处理交易登录事件
        :param event: 交易网关登录事件
        :return:
        """
        rsp_td_login_data = event.payload
        self.logger.info(f"收到交易网关登录事件返回信息：{rsp_td_login_data}")
        if rsp_td_login_data and rsp_td_login_data.get("code") == 0:
            # 交易登录成功
            self.td_login_status = True
            self.logger.info(rsp_td_login_data.get("message"))
            # 获取登录后的交易日填充到全局变量trading_day中
            Const.trading_day = rsp_td_login_data.get("data", {}).get("trading_day")

    def _td_confirm_handler(self, event: Event):
        """
        处理交易确认结算单事件
        :param event: 交易网关确认结算单事件
        :return:
        """
        rsp_td_confirm_data = event.payload
        self.logger.info(f"收到交易网关确认结算单事件返回信息：{rsp_td_confirm_data}")
        if rsp_td_confirm_data and rsp_td_confirm_data.get("code") == 0:
            self.logger.info(rsp_td_confirm_data.get("message"))

            # 初始化策略
            self.init_strategies()

            # 初始化订阅合约
            self.init_sub_instruments()

    def init_strategies(self) -> None:
        """初始化数据中心策略"""
        self.logger.info("初始化数据中心策略...")
        dc_strategy: DataCenterStrategy = DataCenterStrategy()
        self.strategy_map = {dc_strategy.strategy_id: dc_strategy}
        self.logger.info(f"成功初始化数据中心策略")

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
                    self.bar_generator.add_sub_kline_id(strategy.sub_ins_id)
                    self.bar_generator.add_sub_kline_type(strategy.sub_kline_type)

            self.bar_generator.init_min_kline_map()

        self.logger.info(f"成功初始化订阅合约")
        self.logger.info(f"需要订阅的合约数量：{len(self.sub_all_ins)}")

    def _td_ready_handler(self, event: Event):
        """
        处理交易网关就绪事件
        :param event: 交易网关就绪事件
        :return:
        """
        rsp_td_ready_data = event.payload
        self.logger.info(f"收到交易网关就绪事件返回信息：{rsp_td_ready_data}")
        if rsp_td_ready_data and rsp_td_ready_data.get("code") == 0:
            self.logger.info(rsp_td_ready_data.get("message"))
            # 初始化策略
            self.init_strategies()

            # 初始化订阅合约
            self.init_sub_instruments()

    def _get_tick(self, event: Event) -> None:
        """
        优化tick处理方法，使用批量处理提高吞吐量
        """
        self.logger.debug(f"收到tick事件，payload code: {event.payload.get('code')}")
        if event.payload.get("code") == 0:
            # 从tick行情事件中获取tick对象
            try:
                tick: TickData = event.payload.get("data")
                if tick:
                    self.logger.debug(f"收到tick数据: {tick.instrument_id} @ {tick.last_price}")
                    # 添加到批处理队列
                    self._add_tick_to_batch(tick)
                else:
                    self.logger.warning("tick数据为空")

            except Exception as e:
                self.logger.exception(f"获取或分发tick行情数据异常：{e}")
                return
        else:
            self.logger.warning(f"收到非成功的tick事件，code: {event.payload.get('code')}, message: {event.payload.get('message')}")

    def _add_tick_to_batch(self, tick: TickData) -> None:
        """
        将tick添加到批处理队列
        """
        with self._batch_lock:
            self._tick_batch_queue.append(tick)
            current_time = time.time()
            
            # 检查是否需要触发批处理
            should_process = (
                len(self._tick_batch_queue) >= self._tick_batch_size or  # 达到批量大小
                current_time - self._last_batch_time >= self._tick_batch_timeout  # 超时
            )
            
            if should_process:
                # 复制当前批次并清空队列
                batch_ticks = self._tick_batch_queue.copy()
                self._tick_batch_queue.clear()
                self._last_batch_time = current_time
                
                # 异步处理批量tick
                self._safe_submit_to_pool(
                    self.tick_thread_pool,
                    self._process_tick_batch,
                    batch_ticks
                )

    def _process_tick_batch(self, tick_batch: list[TickData]) -> None:
        """
        批量处理tick数据
        """
        try:
            for tick in tick_batch:
                # 直接处理每个tick，减少线程切换
                self._distribute_tick(tick)
                
            # 更新统计信息
            batch_size = len(tick_batch)
            self._total_tick_count += batch_size
            self._tick_queue_size = max(0, self._tick_queue_size - batch_size)
            
            # 优化日志输出，显示实际处理模式
            if self._total_tick_count % 1000 == 0:
                if batch_size == 1:
                    self.logger.info(f"已实时处理tick数量: {self._total_tick_count} (单tick模式)")
                else:
                    self.logger.info(f"已批量处理tick数量: {self._total_tick_count}，批次大小: {batch_size}")
                
        except Exception as e:
            self.logger.exception(f"批量处理tick数据异常: {e}")

    def _distribute_tick(self, tick: TickData) -> None:
        """
        直接分发tick数据，不使用额外线程池
        """
        try:
            # 传递tick到策略
            for strategy in self.strategy_map.values():
                if tick.instrument_id in strategy.sub_ins_id:
                    # 直接调用策略方法，避免线程池开销
                    strategy.specific_strategy_map[tick.instrument_id].on_tick(tick)
                    
        except Exception as e:
            self.logger.exception(f"直接分发tick数据异常: {e}")

    def _flush_tick_batch(self) -> None:
        """
        强制刷新批处理队列，处理剩余的tick
        """
        with self._batch_lock:
            if self._tick_batch_queue:
                batch_ticks = self._tick_batch_queue.copy()
                self._tick_batch_queue.clear()
                
                self.logger.info(f"刷新批处理队列，处理剩余 {len(batch_ticks)} 个tick")
                
                # 直接处理，不使用线程池（因为可能正在关闭）
                for tick in batch_ticks:
                    try:
                        self._distribute_tick(tick)
                    except Exception as e:
                        self.logger.error(f"刷新批处理时处理tick失败: {e}")


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
        self.market_gateway.connect(self.broker_config)

        # 连接交易服务器并登录
        self.trader_gateway.connect(self.broker_config)

        start_time: float = time.time()
        timeout: float = 10.0

        while not (self.md_login_status and self.td_login_status):
            # 检查是否超时
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                self.logger.warning(
                    f"等待登录超时 ({timeout}秒)，当前状态 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
                break
            time.sleep(0.1)

        if not self.md_login_status or not self.td_login_status:
            self.logger.error(f"网关登录失败 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
            self.dc_running = False

            self.dc_event_bus.publish(Event(EventType.DATA_CENTER_START, {
                "code": ErrorCode.DATA_CENTER_START_FAILED,
                "message": "数据中心启动失败",
                "data": None
            }))
            return False

        self.dc_running = True
        self.logger.info(f"所有网关登录成功 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
        self.logger.info("数据中心启动成功")

        # 发布数据中心启动事件(成功)
        self.dc_event_bus.publish(Event(EventType.DATA_CENTER_START, {
            "code": ErrorCode.SUCCESS,
            "message": "数据中心启动成功",
            "data": None
        }))

        # 登录成功后发送查询合约事件
        self._publish_qry_ins()

        return True

    def _publish_qry_ins(self) -> None:
        """
        向底层交易网关发布更新合约事件，交易网关完成登录就会自动更新合约信息
        :return:
        """
        self.dc_event_bus.publish(Event(EventType.DATA_CENTER_QRY_INS, {}))
        self.logger.info("发布更新合约事件成功")

    # ================== 关闭和清理优化 ==================

    def shutdown_dc(self, event: Event = None) -> None:
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

        # 2. 刷新批处理队列，确保所有tick都被处理
        self._flush_tick_batch()

        # 3. 关闭所有CSV文件
        self._close_all_csv_files()

        try:
            # 3. 停止网关
            if self.market_gateway:
                self.market_gateway.close()
                self.market_gateway = None

            if self.trader_gateway:
                self.trader_gateway.close()
                self.trader_gateway = None

            # 4. 停止事件总线
            if self.dc_event_bus:
                self.dc_event_bus.stop()

            # 5. 最后关闭线程池
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

        # 先关闭tick线程池（停止接收新任务）
        if hasattr(self, 'tick_thread_pool') and self.tick_thread_pool:
            try:
                self.logger.info("关闭tick处理线程池...")
                self.tick_thread_pool.shutdown(wait=True)
                self.logger.info("tick处理线程池已关闭")
            except Exception as e:
                self.logger.error(f"关闭tick线程池失败: {e}")

        # 再关闭主线程池
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
            if self.thread_pool.executor and hasattr(self.thread_pool.executor, '_shutdown') and self.thread_pool.executor._shutdown:
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

                    # 执行策略闹钟回调
                    for instrument_id in strategy.sub_ins_id:
                        specific_strategy = strategy.specific_strategy_map[instrument_id]
                        self.thread_pool.submit(
                            self._safe_execute_callback,
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
        self.logger.debug(f"[SYSTEM_EVENTS] 开始检查系统事件 - {current_time}")
        
        # 执行每分钟任务（直接执行，不提交到线程池）
        self._one_min(current_time)

        # 执行登录服务器
        self.logger.debug(f"[LOGIN_CHECK] 当前时间: {current_time}, 登录时间配置: {self._alarm_schedule.login_times}")
        if current_time in self._alarm_schedule.login_times:
            self.logger.info(f"触发登录: {current_time}")
            self._connect_gateway()
        else:
            self.logger.debug(f"[LOGIN_CHECK] 不在登录时间内")

        # 执行开盘前
        self.logger.debug(f"[BEFORE_OPEN_CHECK] 当前时间: {current_time}, 开盘前时间配置: {self._alarm_schedule.before_open_times}")
        if current_time in self._alarm_schedule.before_open_times:
            self.logger.info(f"触发开盘前: {current_time}")
            # 使用安全提交方法
            self._safe_submit_to_pool(self.thread_pool, self._before_open)

        # 执行订阅行情
        self.logger.debug(f"[SUB_CHECK] 当前时间: {current_time}, 订阅时间配置: {self._alarm_schedule.sub_id_times}")
        if current_time in self._alarm_schedule.sub_id_times:
            self.logger.info(f"触发订阅所有行情: {current_time}")
            self._subscribe_all_instruments()

        # 收盘后事件
        self.logger.debug(f"[AFTER_CLOSE_CHECK] 当前时间: {current_time}, 收盘后时间配置: {self._alarm_schedule.after_close_times}")
        if current_time in self._alarm_schedule.after_close_times:
            self.logger.info(f"触发收盘后事件: {current_time}")
            # 使用安全提交方法
            self._safe_submit_to_pool(self.thread_pool, self._after_close)
            
        self.logger.debug(f"[SYSTEM_EVENTS] 系统事件检查完成 - {current_time}")

    def _subscribe_all_instruments(self) -> None:
        """
        合约订阅方法，分批订阅避免阻塞
        """
        self.logger.info(f"开始订阅 {len(self.sub_all_ins)} 个合约...")

        # 分批订阅，每批10个合约
        batch_size = 10
        for i in range(0, len(self.sub_all_ins), batch_size):
            batch = self.sub_all_ins[i:i + batch_size]
            for ins in batch:
                try:
                    self.market_gateway.subscribe(SubscribeRequest(ins))
                except Exception as e:
                    self.logger.error(f"订阅合约 {ins} 失败: {e}")

            self.logger.info(f"已订阅 {min(i + batch_size, len(self.sub_all_ins))}/{len(self.sub_all_ins)} 个合约")

            # 批次间短暂延迟
            if i + batch_size < len(self.sub_all_ins):
                time.sleep(0.1)

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
        if self.strategy_map:
            for strategy in self.strategy_map.values():
                # 对于数据中心策略，只需要在策略级别执行一次开盘前事件
                self.logger.info(f"为策略{strategy.strategy_id}执行开盘前事件（策略级别）")
                self.thread_pool.submit(
                    self._safe_execute_callback,
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

        if self.strategy_map:
            for strategy in self.strategy_map.values():
                # 对于数据中心策略，只需要在策略级别执行一次收盘后事件
                self.logger.info(f"为策略{strategy.strategy_id}执行收盘后事件（策略级别）")
                self.thread_pool.submit(
                    self._safe_execute_callback,
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
            status = {
                'thread_pools_initialized': self.thread_pools_initialized,
                'alarm_running': self._alarm_running,
                'dc_running': self.dc_running,
                'tick_statistics': {
                    'total_processed': self._total_tick_count,
                    'current_queue_size': self._tick_queue_size,
                    'rate_limit': self._tick_rate_limit,
                    'processing_mode': '实时单tick处理'
                },
                'alarm_status': {
                    'running': self._alarm_running,
                    'execution_count': self._alarm_execution_count
                }
            }

            # 线程池状态：显示当前积压情况而非累计完成率
            if self.thread_pool:
                main_progress = self.thread_pool.get_progress()
                # 计算当前积压任务数
                main_pending = max(0, main_progress['total'] - main_progress['completed'])
                status['main_pool'] = {
                    'pending_tasks': main_pending,
                    'completed_today': main_progress['completed'],
                    'status': '空闲' if main_pending == 0 else f'{main_pending}个待处理'
                }
            else:
                status['main_pool'] = {'error': '线程池未初始化'}

            if self.tick_thread_pool:
                tick_progress = self.tick_thread_pool.get_progress()
                # 计算当前积压任务数
                tick_pending = max(0, tick_progress['total'] - tick_progress['completed'])
                status['tick_pool'] = {
                    'pending_tasks': tick_pending,
                    'completed_today': tick_progress['completed'],
                    'status': '空闲' if tick_pending == 0 else f'{tick_pending}个待处理',
                    'note': '实时处理模式：新tick持续到来'
                }
            else:
                status['tick_pool'] = {'error': '线程池未初始化'}

            return status
        except Exception as e:
            return {'error': f'获取状态失败: {str(e)}'}

    # ================== 监控方法 ==================

    def adjust_thread_pool_size(self, tick_workers: int = None, main_workers: int = None) -> bool:
        """
        动态调整线程池大小
        """
        try:
            if tick_workers and hasattr(self, 'tick_thread_pool'):
                # 需要重新创建线程池来调整大小
                old_pool = self.tick_thread_pool
                self.tick_thread_pool = HomalosThreadPool(
                    max_workers=tick_workers,
                    thread_name_prefix='DCTickWorker'
                )
                old_pool.shutdown(wait=False)
                self.logger.info(f"Tick线程池大小调整为: {tick_workers}")

            if main_workers and hasattr(self, 'thread_pool'):
                old_pool = self.thread_pool
                self.thread_pool = HomalosThreadPool(
                    max_workers=main_workers,
                    thread_name_prefix='DCWorker'
                )
                old_pool.shutdown(wait=False)
                self.logger.info(f"主线程池大小调整为: {main_workers}")

            return True
        except Exception as e:
            self.logger.error(f"调整线程池大小失败: {e}")
            return False

    def auto_adjust_thread_pools(self):
        """
        根据系统负载自动调整线程池大小
        """
        status = self.get_thread_pool_status()

        # 根据tick处理负载调整线程池
        queue_size = status['tick_statistics']['current_queue_size']
        tick_pool_progress = status['tick_pool']

        # 如果队列积压严重，增加tick处理线程
        if queue_size > self._max_queue_size * 0.7:
            current_workers = tick_pool_progress.get('max_workers', 1500)
            new_workers = min(current_workers * 2, 3000)  # 最大不超过3000
            self.adjust_thread_pool_size(tick_workers=new_workers)
            self.logger.warning(f"检测到队列积压，tick线程池调整为: {new_workers}")

        # 如果队列空闲，减少线程数节省资源
        elif queue_size < self._max_queue_size * 0.1:
            current_workers = tick_pool_progress.get('max_workers', 1500)
            if current_workers > 500:  # 保持最小线程数500
                new_workers = max(current_workers // 2, 500)
                self.adjust_thread_pool_size(tick_workers=new_workers)
                self.logger.info(f"队列空闲，tick线程池调整为: {new_workers}")

    def monitor_and_adjust(self):
        """
        监控和调整线程池的定时任务
        """
        if not self.dc_running:
            return

        try:
            self.auto_adjust_thread_pools()

            # 每5分钟检查一次
            threading.Timer(300, self.monitor_and_adjust).start()
        except Exception as e:
            self.logger.error(f"线程池监控调整失败: {e}")

    # 在数据中心启动时开始监控
    def start_monitoring(self):
        """启动线程池监控"""
        self.logger.info("启动线程池监控")
        if self.dc_running:
            threading.Timer(60, self.monitor_and_adjust).start()  # 1分钟后开始监控
