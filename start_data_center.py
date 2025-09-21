#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : start_data_center.py
@Date       : 2025/9/18 20:32
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 启动数据中心
"""
import atexit
import datetime
import signal
import time
from threading import Event, Thread
from typing import Optional, Any, Callable

from src.constants import BROKERS_FILENAME, DATA_CENTER_CONFIG_FILENAME
from src.core.constants import ErrorCode
from src.core.event import Event as DataCenterEvent
from src.core.event import EventType
from src.core.event_bus import EventBus
from src.core.object import TradingSchedule, SubscribeRequest, TickData
from src.modules.data_center.data_center_strategy import DataCenterStrategy
from src.modules.function.bar_generator import BarGenerator
from src.modules.gateway.market_gateway import MarketGateway
from src.modules.gateway.trader_gateway import TraderGateway
from src.strategy.base_strategy import BaseStrategy
from src.utils.alarm import Alarm
from src.utils.config_manager import ConfigManager
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger, logger
from src.utils.thread_pool import ThreadPool
from src.utils.utility import get_enable_broker, sleep


class StartDataCenter:

    def __init__(self, alarm_schedule: Optional[TradingSchedule] = None):
        self.alarm = Alarm()                                    # 使用单例模式的闹钟实例
        self._alarm_thread = None                               # 闹钟线程实例
        self._alarm_stop_event = Event()                        # 闹钟线程控制
        self._alarm_running: bool = False                       # 闹钟运行状态
        self._alarm_start_time = datetime.datetime.now()        # 闹钟开始时间
        self._alarm_last_execution_time: Optional[str] = None   # 防重复执行机制
        self._alarm_execution_lock = Event()                    # 执行锁
        self._alarm_execution_count: int = 0                    # 闹钟执行次数
        self._alarm_schedule: Optional[TradingSchedule] = alarm_schedule  # 闹钟调度器时间配置

        self.tick_to_kline_sys = BarGenerator()

        self.dt_event_bus: Optional[EventBus] = None            # 数据中心事件总线
        self.dt_config: dict[str, Any] = {}                     # 数据中心所有相关配置字典
        self.dt_running: bool = False                           # 数据中心运行状态

        self.bar_generator = BarGenerator()                     # 初始化K线合成系统
        self.strategy_map: dict = {}         # 初始化策略映射
        self.thread_pool = ThreadPool(35)                       # 初始化线程池实例

        self.market_gateway: MarketGateway | None = None        # 行情网关
        self.trader_gateway: TraderGateway | None = None        # 交易网关
        self.broker_config: dict[str, dict] =  {}               # 网关配置
        self.md_login_status: bool = False                      # 行情网关登录状态
        self.td_login_status: bool = False                      # 交易网关登录状态
        self.trading_day: str = ""                              # 交易日

        self.is_update_ins = True      # 是否更新合约，更新所有上市合约到instrument_exchange.json文件中，每次只在开盘盘时更新一次

        self.sub_list: list[str] = []       # 订阅列表

        self.csv_file = None
        self.csv_writer = None

        # 注册关闭处理器
        atexit.register(self.stop_alarm)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger = get_logger(self.__class__.__name__)

    def init_data_center_config(self) -> bool:
        # 加载 data_center.yaml
        config_file_path: str = str(get_path_ins.get_config_dir() / DATA_CENTER_CONFIG_FILENAME)
        dt_cfg = ConfigManager(config_file_path)
        self.dt_config: dict = dt_cfg.get("base", {})

        if not self.dt_config or not self.dt_config.get("enable", False):
            self.logger.warning("没有配置data_center或没有启用data_center")
            return False

        alarm_schedule_cfg = self.dt_config.get("alarm_schedule", {})
        login_times = alarm_schedule_cfg.get("login_times", [])
        pre_open_times = alarm_schedule_cfg.get("pre_open_times", [])
        after_close_times = alarm_schedule_cfg.get("after_close_times", [])
        check_interval = alarm_schedule_cfg.get("check_interval", 60)

        now_time = datetime.datetime.now()
        t_login_time = now_time + datetime.timedelta(seconds=60)
        t_login = t_login_time.time().strftime('%H:%M')

        t_pre_open_time = now_time + datetime.timedelta(seconds=120)
        t_pre_open = t_pre_open_time.time().strftime('%H:%M')

        t_sub_id_time = now_time + datetime.timedelta(seconds=180)
        t_sub = t_sub_id_time.time().strftime('%H:%M')

        t_close_time = now_time + datetime.timedelta(seconds=240)
        t_close = t_close_time.time().strftime('%H:%M')

        self._alarm_schedule = TradingSchedule(
            login_times=[t_login],
            pre_open_times=[t_pre_open],
            sub_id_times=[t_sub],
            after_close_times=[t_close],
            check_interval=check_interval
        )

        self.logger.debug("开始验证K线配置...")
        bar_generation: dict = self.dt_config.get("bar_generation", {})
        bar_generation_list: list = bar_generation.get("intervals", [])
        # 验证K线配置
        if not bar_generation or not bar_generation_list:
            self.logger.warning("K线间隔未配置，请配置默认间隔: [1m, 5m, 15m, 30m, 60m, 1d]")
        self.logger.debug("配置验证完成")
        return True

    def init_broker_config(self) -> bool:
        """初始化broker节点配置"""
        brokers_file_path: str = str(get_path_ins.get_config_dir() / BROKERS_FILENAME)
        # 加载 brokers.yaml
        brokers_cfg = ConfigManager(brokers_file_path)
        rsp_enable_broker = get_enable_broker(brokers_cfg)
        if not rsp_enable_broker:
            self.logger.warning("没有启用的broker")
            return False
        # 获取启用的broker名称和类型
        enabled_broker_name = rsp_enable_broker.get("broker_name", "")
        enabled_broker_type = rsp_enable_broker.get("broker_type", "")
        self.logger.info(f"启用的broker名称: {enabled_broker_name}，broker类型: {enabled_broker_type}")
        # 将broker节点配置写入dt_config
        self.dt_config['broker'] = rsp_enable_broker
        return True

    def init_strategies(self) -> None:
        """初始化测试策略"""
        # 创建数据中心策略实例
        self.logger.info("初始化策略")
        self.strategy_map: dict = {"0001": DataCenterStrategy()}

        if self.strategy_map:
            for strategy in self.strategy_map.values():
                self.logger.info("策略{}：{}".format(strategy.strategy_id, strategy.strategy_content))

    def init_sub_instruments(self) -> None:
        """初始化所有策略(目前只有一个)需要订阅的合约，登录后进行"""
        if self.strategy_map:
            for strategy in self.strategy_map.values():
                self.sub_list = list(set(self.sub_list + strategy.sub_ins_id))

                if strategy.sub_kline_type:
                    self.tick_to_kline_sys.add_sub_kline_id(strategy.sub_ins_id)
                    self.tick_to_kline_sys.add_sub_kline_type(strategy.sub_kline_type)

            self.tick_to_kline_sys.init_min_kline_map()

        self.logger.info(f"成功初始化数据中心策略")

    def _md_gateway_login_handler(self, event: DataCenterEvent) -> None:
        """
        处理行情网关登录事件
        :param event: 行情网关登录事件
        :return:
        """
        self.logger.info("收到行情网关登录事件，判断行情服务器是否登录成功")
        rsp_login_data: dict = event.payload
        self.logger.info(f"收到行情网关登录事件数据：{rsp_login_data}")
        if rsp_login_data and rsp_login_data.get("code") == 0:
            self.md_login_status = True
            self.logger.info(rsp_login_data.get("message"))

    def _td_gateway_login_handler(self, event: DataCenterEvent) -> None:
        """
        交易网关登录事件处理
        :param event: 交易网关登录事件
        :return:
        """
        self.logger.info("收到交易网关登录事件，判断交易服务器是否登录成功")
        rsp_login_data = event.payload
        self.logger.info(f"收到交易网关登录事件数据：{rsp_login_data}")
        if rsp_login_data and rsp_login_data.get("code") == 0:
            self.logger.info(rsp_login_data.get("message"))
            self.td_login_status = True
            self.trading_day = rsp_login_data.get("data", {}).get("trading_day")  # 获取登录后的交易日

    def _td_gateway_ready_handler(self, event: DataCenterEvent):
        self.logger.info(f"收到交易网关就绪事件，事件类型：{event.event_type}")
        rsp_login_data = event.payload
        if rsp_login_data and rsp_login_data.get("code") == 0:
            self.logger.info(rsp_login_data.get("message"))
            self.logger.info(f"现在时间：{datetime.datetime.now()}")

            self.publish_qry_instruments()

    def _td_confirm_success_handler(self, event: DataCenterEvent):
        self.logger.info(f"收到结算单确认成功事件，事件类型：{event.event_type}")
        rsp_login_data = event.payload
        if rsp_login_data and rsp_login_data.get("code") == 0:
            self.logger.info(rsp_login_data.get("message"))
            self.logger.info(f"现在时间：{datetime.datetime.now()}")

            self.publish_qry_instruments()

    def distribute_tick(self, event: DataCenterEvent):
        """
        判断需要给哪些策略传tick，以及哪些合约需要合成 min1 K线
        :param event:
        :return:
        """
        if event and event.payload:
            tick: TickData = event.payload
            # 传递tick到策略
            for strategy in self.strategy_map.values():
                if tick.instrument_id in strategy.sub_ins_id:
                    # 直接调用行情事件
                    self.thread_pool.submit(strategy.specific_strategy_map[tick.instrument_id].on_tick, tick)

            # tick合成K线
            if tick.instrument_id in self.tick_to_kline_sys.sub_kline_id:
                self.tick_to_kline_sys.tick_to_kline(tick)

    def init_dt_event_bus(self) -> None:
        self.dt_event_bus: EventBus = EventBus(context="DataCenter", register_signals=False)
        self.logger.info("数据中心EventBus实例创建成功")

        # 订阅行情网关登录事件
        self.dt_event_bus.subscribe(EventType.MD_GATEWAY_LOGIN, self._md_gateway_login_handler)
        # 订阅交易网关登录事件
        self.dt_event_bus.subscribe(EventType.TD_GATEWAY_LOGIN, self._td_gateway_login_handler)
        # 订阅事件总线停止事件
        self.dt_event_bus.subscribe(EventType.EVENT_BUS_SHUTDOWN, self.shutdown_dt)
        # 首次底层会发布确认结算单事件，如果断开重连交易网关，底层不再确认结算单
        if self.is_update_ins:
            # 订阅结算单确认成功事件
            self.dt_event_bus.subscribe(EventType.TD_CONFIRM_SUCCESS, self._td_confirm_success_handler)
        else:
            # 订阅交易网关就绪事件
            self.dt_event_bus.subscribe(EventType.TD_GATEWAY_READY, self._td_gateway_ready_handler)
            self.is_update_ins = False

        # 订阅行情数据
        self.dt_event_bus.subscribe(EventType.TICK, self.distribute_tick)

    def init_gateway(self) -> None:
        self.market_gateway = MarketGateway(self.dt_event_bus, gateway_name="DataCenter_MD")
        self.trader_gateway = TraderGateway(self.dt_event_bus, gateway_name="DataCenter_TD")
        broker_info: dict = self.dt_config.get('broker', {})
        self.broker_config: dict = broker_info.get('broker_config', {})

    def connect_gateway(self) -> bool:
        # 连接行情服务器并登录
        self.market_gateway.connect(self.broker_config)
        # 连接交易服务器并登录
        self.trader_gateway.connect(self.broker_config)

        start_time: float = time.time()
        timeout: float = 5.0
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
            self.dt_running = False

            self.dt_event_bus.publish(DataCenterEvent(EventType.DATA_CENTER_START, {
                "code": ErrorCode.DATA_CENTER_START_FAILED,
                "message": "数据中心启动失败",
                "data": None
            }))
            return False

        self.logger.info(f"所有网关登录成功 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
        self.dt_running = True
        # 发布数据中心启动事件(成功)
        self.logger.info("数据中心启动成功")

        # 发布数据中心启动事件(成功)
        self.dt_event_bus.publish(DataCenterEvent(EventType.DATA_CENTER_START, {
            "code": ErrorCode.SUCCESS,
            "message": "数据中心启动成功",
            "data": None
        }))

        return True

    def publish_qry_instruments(self) -> None:
        """查询合约"""
        # 向底层交易网关发布更新合约事件
        self.dt_event_bus.publish(DataCenterEvent(EventType.DATA_CENTER_QRY_INS, {}))
        self.logger.info("发布更新合约事件成功")

    def shutdown_dt(self, event: DataCenterEvent = None) -> None:
        """
        关闭数据中心
        :return: None
        """
        if not self.dt_running:
            self.logger.info("数据中心未在运行")
            return

        if event:
            self.logger.info(f"收到关闭信号，事件类型：{event.event_type}")

        self.logger.info("停止数据中心...")
        self.dt_running = False
        try:
            # 停止网关
            if self.market_gateway:
                self.market_gateway.close()
                self.market_gateway = None

            if self.trader_gateway:
                self.trader_gateway.close()
                self.trader_gateway = None

            if self.dt_event_bus:
                self.dt_event_bus.stop()

            self.logger.info("数据中心已关闭")
        except Exception as e:
            self.logger.error(f"数据中心关闭失败: {e}")

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
        while not self._alarm_stop_event.is_set():
            try:
                current_time = datetime.datetime.now()
                # 计算到下一分钟的睡眠时间
                if current_time.second == 0:
                    sleep_time = self._alarm_schedule.check_interval
                else:
                    sleep_time = self._alarm_schedule.check_interval - current_time.second
                # 提交检查任务到线程池
                self.thread_pool.submit(self._check_alarms)
                # 等待下一次检查，同时响应停止信号
                if self._alarm_stop_event.wait(timeout=sleep_time):
                    break
            except Exception as e:
                self.logger.exception(f"闹钟循环异常: {e}")
                # 异常时短暂等待，避免快速循环
                self._alarm_stop_event.wait(timeout=5)
        self.logger.info("闹钟循环结束")

    def _check_alarms(self) -> None:
        """
        检查并执行闹钟任务
        """
        self.logger.info("检查时间任务开始")
        try:
            current_time_str = datetime.datetime.now().strftime('%H:%M')
            # 防止重复执行同一分钟的任务
            if current_time_str == self._alarm_last_execution_time:
                return

            # 确保同一时间只有一个检查在执行
            if self._alarm_execution_lock.is_set():
                self.logger.debug(f"跳过重复检查: {current_time_str}")
                return

            self._alarm_execution_lock.set()
            try:
                self.logger.debug(f"检查时间: {current_time_str}")
                self._alarm_execution_count += 1
                self._alarm_last_execution_time = current_time_str
                # # 检查用户自定义闹钟
                # self._check_custom_alarms(current_time_str)
                # 检查系统预定义时间点
                self._check_system_events(current_time_str)
            finally:
                self._alarm_execution_lock.clear()
        except Exception as e:
            self.logger.exception(f"检查闹钟时发生异常: {e}")

    # def _check_custom_alarms(self, current_time: str) -> None:
    #     """
    #     检查用户自定义闹钟
    #     :param current_time: 当前时间字符串
    #     """
    #     if self.alarm.time_in_alarm(current_time):
    #         self.logger.info(f"触发自定义闹钟: {current_time}")
    #         try:
    #             strategy_ids = self.alarm.get_strategy_ids(current_time)
    #
    #             for strategy_id in strategy_ids:
    #                 if not strategy_id:
    #                     continue
    #
    #                 strategy_key = strategy_id
    #                 if strategy_key not in self.strategy_map:
    #                     self.logger.warning(f"策略 {strategy_id} 不存在")
    #                     continue
    #
    #                 strategy = self.strategy_map[strategy_key]
    #
    #                 # 执行策略闹钟回调
    #                 for instrument_id in strategy.sub_ins_id:
    #                     if instrument_id in strategy.specific_strategy_map:
    #                         specific_strategy = strategy.specific_strategy_map[instrument_id]
    #                         self.thread_pool.submit(
    #                             self._safe_execute_callback,
    #                             specific_strategy.on_alarm,
    #                             f"策略{strategy_id}-{instrument_id}闹钟回调"
    #                         )
    #         except Exception as e:
    #             self.logger.exception(f"执行自定义闹钟失败: {e}")

    def _handle_pre_open_event(self) -> None:
        """处理开盘前事件"""
        self.logger.info("执行开盘前事件检测...")
        self.logger.info(f"strategy_map: {self.strategy_map}")
        if self.strategy_map:
            for strategy in self.strategy_map.values():
                for instrument_id in strategy.sub_ins_id:
                    specific_strategy = strategy.specific_strategy_map[instrument_id]
                    self.logger.info(f"执行开盘前回调-{instrument_id}")
                    self.thread_pool.submit(
                        self._safe_execute_callback,
                        specific_strategy.on_before_open,
                        f"开盘前回调-{instrument_id}"
                    )

    def _handle_close_event(self) -> None:
        """处理收盘后事件"""
        self.logger.info("执行收盘后退出事件")

        if self.strategy_map:
            for strategy in self.strategy_map.values():
                for instrument_id in strategy.sub_ins_id:
                    specific_strategy = strategy.specific_strategy_map[instrument_id]
                    self.thread_pool.submit(
                        self._safe_execute_callback,
                        specific_strategy.on_after_close(),
                        f"收盘后回调-{instrument_id}"
                    )

    def _check_system_events(self, current_time: str) -> None:
        """
        检查系统预定义事件
        :param current_time: 当前时间字符串
        """
        # 登录网关事件
        self.logger.info(f"_check_system_events: {current_time}")
        if current_time in self._alarm_schedule.login_times:
            self.logger.info(f"触发登录闹钟: {current_time}")
            self.connect_gateway()
            # 初始化订阅
            self.init_sub_instruments()

        # 开盘前事件
        if current_time in self._alarm_schedule.pre_open_times:
            self.logger.info(f"触发开盘前事件: {current_time}")
            self.thread_pool.submit(
                self._safe_execute_callback,
                self._handle_pre_open_event,
                "开盘前事件"
            )

        # 订阅行情事件
        if current_time in self._alarm_schedule.sub_id_times:
            self.logger.info(f"触发订阅所有行情事件: {current_time}")
            self.logger.info(f"订阅所有行情: {self.sub_list}")
            for ins in self.sub_list:
                self.market_gateway.subscribe(SubscribeRequest(ins))

        # 收盘后事件
        if current_time in self._alarm_schedule.after_close_times:
            self.logger.info(f"触发收盘后事件: {current_time}")
            self.thread_pool.submit(
                self._safe_execute_callback,
                self._handle_close_event,
                "收盘后事件"
            )

    def _safe_execute_callback(self, callback: Callable, description: str) -> None:
        """
        安全执行回调函数
        :param callback: 要执行的回调函数
        :param description: 回调描述
        """
        try:
            callback()
            self.logger.debug(f"{description} 执行成功")
        except Exception as e:
            self.logger.exception(f"{description} 执行失败: {e}")

    def _signal_handler(self, signum, _frame) -> None:
        """信号处理器"""
        self.logger.debug(f"收到信号 {signum}，正在关闭...")
        self.shutdown_dt()
        self.stop_alarm()

    def stop_alarm(self, timeout: float = 10.0) -> None:
        """
        停止闹钟调度器
        :param timeout: 等待超时时间（秒）
        """
        if not self._alarm_running:
            return

        self.logger.info("正在停止闹钟调度器...")
        # 设置停止标志
        self._alarm_stop_event.set()
        self._alarm_running = False
        # 等待线程结束
        if self._alarm_thread and self._alarm_thread.is_alive():
            self._alarm_thread.join(timeout=timeout)
            if self._alarm_thread.is_alive():
                self.logger.warning("闹钟线程未能在指定时间内停止")
            else:
                self.logger.info("闹钟调度器已停止")
        # 关闭线程池
        self.thread_pool.clean_pool()
        # 清理资源
        self.alarm.clean()

    def is_alarm_running(self) -> bool:
        """检查调度器是否正在运行"""
        return self._alarm_running

    def get_status(self) -> dict[str, Any]:
        """
        获取调度器状态信息
        :return: 状态信息字典
        """
        uptime = datetime.datetime.now() - self._alarm_start_time
        return {
            "alarm_running": self._alarm_running,
            "uptime": str(uptime),
            "execution_count": self._alarm_execution_count,
            "strategy_count": len(self.strategy_map),
            "alarm_count": self.alarm.get_alarm_count(),
            "last_execution": self._alarm_last_execution_time,
            "thread_alive": self._alarm_thread.is_alive() if self._alarm_thread else False
        }


def main() -> None:
    """
    主函数，启动数据中心应用
    :return: None
    """
    start_data_center = StartDataCenter()
    try:
        # 初始化数据中心配置
        init_dt_cfg = start_data_center.init_data_center_config()
        if not init_dt_cfg:
            logger.warning("初始化数据中心配置失败")
            return

        # 初始化broker配置
        init_broker_cfg = start_data_center.init_broker_config()
        if not init_broker_cfg:
            logger.warning("初始化broker配置失败")
            return

        # 初始化数据中心策略
        start_data_center.init_strategies()

        # 初始化事件总线
        start_data_center.init_dt_event_bus()

        # 初始化网关
        start_data_center.init_gateway()

        # 启动调度器
        if start_data_center.start_alarm():
            logger.info("调度器启动成功，按 Ctrl+C 停止")
            # 主线程保持运行
            while start_data_center.is_alarm_running():
                sleep(1)
                # 每30秒打印一次状态
                if int(time.time()) % 30 == 0:
                    status = start_data_center.get_status()
                    logger.info(f"调度器状态: {status}")
        else:
            logger.exception("调度器启动失败")
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，开始关闭调度器和数据中心...")
    except Exception as e:
        logger.error(f"数据中心运行异常: {e}")
    finally:
        logger.info("收到关闭信号，快速关闭数据中心...")
        start_data_center.shutdown_dt()
        start_data_center.stop_alarm()
        logger.info("程序结束")


if __name__ == '__main__':
    main()
