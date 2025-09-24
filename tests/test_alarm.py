# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# """
# @ProjectName: Homalos
# @FileName   : test_alarm.py
# @Date       : 2025/9/17 21:11
# @Author     : Lumosylva
# @Email      : donnymoving@gmail.com
# @Software   : PyCharm
# @Description: 闹钟系统测试和管理类(调度器 + 执行器架构)
#
# 守护线程的主要职责：时间调度和循环控制
# 具体功能：
# 1. 时间循环管理 _alarm_loop
# 2. 定时触发器：每分钟（或配置的间隔）触发一次闹钟检查
# 3. 生命周期管理：控制整个调度器的启动和停止
# 4. 单一职责：只负责时间调度，不执行具体业务逻辑
# 5. 长期运行的后台服务
#
# 线程池的主要职责：并发任务执行
# 具体功能：
# 1. 并发执行闹钟检查，例如：self.thread_pool.submit(self._check_alarms)
# 2. 并发执行策略回调，例如 on_alarm 回调
# 3. 并发执行系统事件，例如：登录事件
# 线程池场景
# 策略回调执行（可能耗时）
# 登录/连接操作（可能阻塞）
# 多合约并发处理
# 系统事件处理
#
# 设计优势 - 职责分离
# 守护线程：专注时间管理，保证调度精度，确保不错过任何时间点
# 线程池：专注任务执行，提供并发能力，高效的任务执行器
#
# 时间线程 (守护线程)           线程池 (工作线程)
#      │                           │
#      ├─ 每分钟检查时间             │
#      ├─ 计算睡眠时间               │
#      ├─ 提交检查任务 ────────────→ ├─ 接收任务
#      ├─ 等待下次检查               ├─ 检查自定义闹钟
#      ├─ 循环继续...               ├─ 检查系统事件
#      │                           ├─ 执行策略回调
#      │                           ├─ 处理登录事件
#      │                           └─ 任务完成，线程回收
# """
# import atexit
# import datetime
# import signal
# import time
# from threading import Thread, Event
# from typing import Dict, Optional, Callable, Any
#
# from src.core.object import TradingSchedule
# from src.strategy.base_strategy import BaseStrategy
# from src.strategy.strategy_demo import StrategyDemo
# from src.utils.alarm import Alarm
# from src.utils.log.logger import get_logger
# from src.utils.thread_pool import ThreadPool
# from src.utils.utility import sleep
#
#
# class AlarmScheduler:
#     """
#     闹钟调度器
#
#     主要改进：
#     1. 修复线程管理问题
#     2. 添加优雅关闭机制
#     3. 防止重复执行
#     4. 完善异常处理
#     5. 支持配置化时间设置
#
#     使用方式
#     from tests.test_alarm import AlarmScheduler
#
#     scheduler = AlarmScheduler()
#     scheduler.start()
#     """
#
#     def __init__(self, trading_schedule: Optional[TradingSchedule] = None):
#         """
#         初始化闹钟调度器
#
#         :param trading_schedule: 交易时间配置，如果为None则使用默认配置
#         """
#         self.logger = get_logger(self.__class__.__name__)
#         self._start_time = datetime.datetime.now()
#         self._execution_count = 0
#
#         self.strategy_map: dict[str, BaseStrategy] = {}
#         self.alarm = Alarm()    # 使用单例模式的闹钟实例
#         self.thread_pool = ThreadPool(35)
#         self.trading_schedule = trading_schedule or TradingSchedule()
#
#         # 线程控制
#         self._stop_event = Event()
#         self._alarm_thread: Optional[Thread] = None
#         self._is_running = False
#
#         # 防重复执行机制
#         self._last_execution_time: Optional[str] = None
#         self._execution_lock = Event()
#
#         # 初始化测试策略
#         self._initialize_strategies()
#
#         # 注册关闭处理器
#         atexit.register(self.stop)
#         signal.signal(signal.SIGINT, self._signal_handler)
#         signal.signal(signal.SIGTERM, self._signal_handler)
#
#         self.logger.info("闹钟调度器初始化完成")
#
#     def _initialize_strategies(self) -> None:
#         """初始化测试策略"""
#         try:
#             # 创建策略实例
#             strategy_demo = StrategyDemo()
#
#             # 为每个订阅的合约创建具体策略实例
#             for instrument_id in strategy_demo.sub_ins_id:
#                 specific_strategy = strategy_demo.Specific(
#                     instrument_id=instrument_id,
#                     strategy_id=strategy_demo.strategy_id,
#                     sub_kline_type=strategy_demo.sub_kline_type
#                 )
#                 strategy_demo.specific_strategy_map[instrument_id] = specific_strategy
#
#             # 添加到策略映射中
#             self.strategy_map[strategy_demo.strategy_id] = strategy_demo
#             self.logger.info(f"成功初始化测试策略: {strategy_demo.strategy_id}, 合约: {strategy_demo.sub_ins_id}")
#         except Exception as e:
#             self.logger.exception(f"初始化测试策略失败: {e}")
#
#     def add_strategy(self, strategy_id: str, strategy: BaseStrategy) -> None:
#         """
#         添加策略到调度器
#
#         :param strategy_id: 策略ID
#         :param strategy: 策略实例
#         """
#         self.strategy_map[strategy_id] = strategy
#         self.logger.info(f"添加策略: {strategy_id}")
#
#     def remove_strategy(self, strategy_id: str) -> bool:
#         """
#         移除策略
#
#         :param strategy_id: 策略ID
#         :return: 移除成功返回True
#         """
#         if strategy_id in self.strategy_map:
#             del self.strategy_map[strategy_id]
#             self.logger.info(f"移除策略: {strategy_id}")
#             return True
#         return False
#
#     def start(self) -> bool:
#         """
#         启动闹钟调度器
#
#         :return: 启动成功返回True
#         """
#         if self._is_running:
#             self.logger.warning("闹钟调度器已在运行中")
#             return False
#
#         try:
#             self._stop_event.clear()
#             self._is_running = True
#
#             # 创建并启动守护线程
#             self._alarm_thread = Thread(
#                 target=self._alarm_loop,
#                 name="AlarmScheduler",
#                 daemon=True
#             )
#             self._alarm_thread.start()
#
#             self.logger.info("闹钟调度器启动成功")
#             return True
#
#         except Exception as e:
#             self._is_running = False
#             self.logger.exception(f"启动闹钟调度器失败: {e}")
#             return False
#
#     def stop(self, timeout: float = 10.0) -> None:
#         """
#         停止闹钟调度器
#
#         :param timeout: 等待超时时间（秒）
#         """
#         if not self._is_running:
#             return
#
#         self.logger.info("正在停止闹钟调度器...")
#
#         # 设置停止标志
#         self._stop_event.set()
#         self._is_running = False
#
#         # 等待线程结束
#         if self._alarm_thread and self._alarm_thread.is_alive():
#             self._alarm_thread.join(timeout=timeout)
#
#             if self._alarm_thread.is_alive():
#                 self.logger.warning("闹钟线程未能在指定时间内停止")
#             else:
#                 self.logger.info("闹钟调度器已停止")
#
#         # 关闭线程池
#         self.thread_pool.clean_pool()
#
#         # 清理资源
#         self.alarm.clean()
#
#     def is_running(self) -> bool:
#         """检查调度器是否正在运行"""
#         return self._is_running
#
#     def get_status(self) -> Dict[str, Any]:
#         """
#         获取调度器状态信息
#
#         :return: 状态信息字典
#         """
#         uptime = datetime.datetime.now() - self._start_time
#         return {
#             "is_running": self._is_running,
#             "uptime": str(uptime),
#             "execution_count": self._execution_count,
#             "strategy_count": len(self.strategy_map),
#             "alarm_count": self.alarm.get_alarm_count(),
#             "last_execution": self._last_execution_time,
#             "thread_alive": self._alarm_thread.is_alive() if self._alarm_thread else False
#         }
#
#     def _alarm_loop(self) -> None:
#         """
#         主闹钟循环 - 在独立线程中运行
#         """
#         self.logger.info("闹钟循环开始运行")
#
#         while not self._stop_event.is_set():
#             try:
#                 current_time = datetime.datetime.now()
#
#                 # 计算到下一分钟的睡眠时间
#                 if current_time.second == 0:
#                     sleep_time = self.trading_schedule.check_interval
#                 else:
#                     sleep_time = self.trading_schedule.check_interval - current_time.second
#
#                 # 提交检查任务到线程池
#                 self.thread_pool.submit(self._check_alarms)
#
#                 # 等待下一次检查，同时响应停止信号
#                 if self._stop_event.wait(timeout=sleep_time):
#                     break
#
#             except Exception as e:
#                 self.logger.exception(f"闹钟循环异常: {e}")
#                 # 异常时短暂等待，避免快速循环
#                 self._stop_event.wait(timeout=5)
#
#         self.logger.info("闹钟循环结束")
#
#     def _check_alarms(self) -> None:
#         """
#         检查并执行闹钟任务
#         """
#         try:
#             current_time_str = datetime.datetime.now().strftime('%H:%M')
#
#             # 防止重复执行同一分钟的任务
#             if current_time_str == self._last_execution_time:
#                 return
#
#             # 确保同一时间只有一个检查在执行
#             if self._execution_lock.is_set():
#                 self.logger.debug(f"跳过重复检查: {current_time_str}")
#                 return
#
#             self._execution_lock.set()
#
#             try:
#                 self.logger.debug(f"检查时间: {current_time_str}")
#                 self._execution_count += 1
#                 self._last_execution_time = current_time_str
#
#                 # 检查用户自定义闹钟
#                 self._check_custom_alarms(current_time_str)
#
#                 # 检查系统预定义时间点
#                 self._check_system_events(current_time_str)
#
#             finally:
#                 self._execution_lock.clear()
#
#         except Exception as e:
#             self.logger.exception(f"检查闹钟时发生异常: {e}")
#
#     def _check_custom_alarms(self, current_time: str) -> None:
#         """
#         检查用户自定义闹钟
#
#         :param current_time: 当前时间字符串
#         """
#         if self.alarm.time_in_alarm(current_time):
#             self.logger.info(f"触发自定义闹钟: {current_time}")
#
#             try:
#                 strategy_ids = self.alarm.get_strategy_ids(current_time)
#
#                 for strategy_id in strategy_ids:
#                     if not strategy_id:
#                         continue
#
#                     strategy_key = strategy_id
#                     if strategy_key not in self.strategy_map:
#                         self.logger.warning(f"策略 {strategy_id} 不存在")
#                         continue
#
#                     strategy = self.strategy_map[strategy_key]
#
#                     # 执行策略闹钟回调
#                     for instrument_id in strategy.sub_ins_id:
#                         if instrument_id in strategy.specific_strategy_map:
#                             specific_strategy = strategy.specific_strategy_map[instrument_id]
#                             self.thread_pool.submit(
#                                 self._safe_execute_callback,
#                                 specific_strategy.on_alarm,
#                                 f"策略{strategy_id}-{instrument_id}闹钟回调"
#                             )
#
#             except Exception as e:
#                 self.logger.exception(f"执行自定义闹钟失败: {e}")
#
#     def _check_system_events(self, current_time: str) -> None:
#         """
#         检查系统预定义事件
#
#         :param current_time: 当前时间字符串
#         """
#         # 登录事件
#         if current_time in self.trading_schedule.login_times:
#             self.logger.info(f"触发登录事件: {current_time}")
#             self.thread_pool.submit(
#                 self._safe_execute_callback,
#                 self._handle_login_event,
#                 "登录事件"
#             )
#
#         # 开盘前事件
#         if current_time in self.trading_schedule.pre_open_times:
#             self.logger.info(f"触发开盘前事件: {current_time}")
#             self.thread_pool.submit(
#                 self._safe_execute_callback,
#                 self._handle_pre_open_event,
#                 "开盘前事件"
#             )
#
#         # 收盘后事件
#         if current_time in self.trading_schedule.after_close_times:
#             self.logger.info(f"触发收盘后事件: {current_time}")
#             self.thread_pool.submit(
#                 self._safe_execute_callback,
#                 self._handle_close_event,
#                 "收盘后事件"
#             )
#
#     def _handle_login_event(self) -> None:
#         """处理登录事件"""
#         self.logger.info("开始登录账户")
#         sleep(3)  # 模拟登录过程
#         self.logger.info("登录交易账户成功")
#
#     def _handle_pre_open_event(self) -> None:
#         """处理开盘前事件"""
#         self.logger.info("执行开盘前事件检测")
#
#         if self.strategy_map:
#             for strategy in self.strategy_map.values():
#                 for instrument_id in strategy.sub_ins_id:
#                     if instrument_id in strategy.specific_strategy_map:
#                         specific_strategy = strategy.specific_strategy_map[instrument_id]
#                         self.thread_pool.submit(
#                             self._safe_execute_callback,
#                             specific_strategy.on_before_open,
#                             f"开盘前回调-{instrument_id}"
#                         )
#
#     def _handle_close_event(self) -> None:
#         """处理收盘后事件"""
#         self.logger.info("执行收盘后退出事件")
#
#     def _safe_execute_callback(self, callback: Callable, description: str) -> None:
#         """
#         安全执行回调函数
#         :param callback: 要执行的回调函数
#         :param description: 回调描述
#         """
#         try:
#             callback()
#             self.logger.debug(f"{description} 执行成功")
#         except Exception as e:
#             self.logger.exception(f"{description} 执行失败: {e}")
#
#     def _signal_handler(self, signum, _frame) -> None:
#         """信号处理器"""
#         self.logger.debug(f"收到信号 {signum}，正在关闭...")
#         self.stop()
#
#
# if __name__ == '__main__':
#     # 做测试的一些时间
#     now_time = datetime.datetime.now()
#     t_login_time = now_time + datetime.timedelta(days=0, hours=0, seconds=10)
#     t_login = t_login_time.time().strftime('%H:%M')
#
#     t_pre_open_time = now_time + datetime.timedelta(days=0, hours=0, seconds=20)
#     t_pre_open = t_pre_open_time.time().strftime('%H:%M')
#
#     t_pre_strategy_time = now_time + datetime.timedelta(days=0, hours=0, seconds=30)
#     t_pre_strategy = t_pre_strategy_time.time().strftime('%H:%M')
#
#     t_sub_id_time = now_time + datetime.timedelta(days=0, hours=0, seconds=40)
#     t_sub = t_sub_id_time.time().strftime('%H:%M')
#
#     t_close_time = now_time + datetime.timedelta(days=0, hours=0, seconds=50)
#     t_close = t_close_time.time().strftime('%H:%M')
#
#     # 创建自定义交易时间配置
#     custom_schedule = TradingSchedule(
#         login_times=["08:45", "20:45", t_login],  # 登录时间
#         pre_open_times=["08:50", "20:50", t_pre_open],  # 开盘前事件时间
#         after_close_times=["21:59", t_close],  # 收盘后事件时间
#         check_interval=60
#     )
#
#     # 使用新的调度器
#     scheduler = AlarmScheduler(custom_schedule)
#
#     # 添加一些测试闹钟 - 使用动态时间进行测试
#     test_alarm_time = now_time + datetime.timedelta(seconds=30)
#     test_alarm_str = test_alarm_time.time().strftime('%H:%M')
#     scheduler.alarm.set_alarm(test_alarm_str, "1001")
#     scheduler.logger.info(f"设置测试闹钟: {test_alarm_str} -> 策略1001")
#
#     try:
#         # 启动调度器
#         if scheduler.start():
#             scheduler.logger.info("调度器启动成功，按 Ctrl+C 停止")
#
#             # 主线程保持运行
#             while scheduler.is_running():
#                 time.sleep(1)
#
#                 # 每30秒打印一次状态
#                 if int(time.time()) % 30 == 0:
#                     status = scheduler.get_status()
#                     scheduler.logger.info(f"调度器状态: {status}")
#         else:
#             print("调度器启动失败")
#
#     except KeyboardInterrupt:
#         scheduler.logger.info("收到中断信号")
#     finally:
#         scheduler.stop()
#         scheduler.logger.info("程序结束")
