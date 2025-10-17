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
import os
import signal
import sys
import threading
import time
from datetime import datetime
from typing import Any, Optional

from src.common import get_enable_broker
from src.constants import DATA_CENTER_CONFIG_FILENAME, BROKERS_FILENAME
from src.modules.data_center.data_center import DataCenter
from src.utils.config_manager import ConfigManager
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger, logger


class StartDataCenter:

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._dc_config: dict[str, Any] = {}  # 数据中心所有相关配置字典
        self._data_center: Optional[DataCenter] = None
        self._running: bool = False  # 添加运行状态标志
        self._shutdown_in_progress: bool = False  # 防止重复关闭
        self._main_thread_event = threading.Event()  # 主线程等待事件

        # 注册关闭处理器
        self._register_shutdown_handlers()

    def _register_shutdown_handlers(self) -> None:
        """注册关闭处理器"""
        try:
            atexit.register(self.stop_dc)
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            self.logger.info("关闭处理器注册成功")
        except Exception as e:
            self.logger.error(f"注册关闭处理器失败: {e}")

    def load_dc_config(self) -> bool:
        """
        加载数据中心配置，并且基础数据验证
        :return: bool - 配置是否有效
        """
        self.logger.info("开始加载数据中心配置...")
        try:
            dc_config_filepath: str = str(get_path_ins.get_config_dir() / DATA_CENTER_CONFIG_FILENAME)

            if not os.path.exists(dc_config_filepath):
                self.logger.error(f"配置文件不存在: {dc_config_filepath}")
                return False

            dt_cfg_manager = ConfigManager(dc_config_filepath)
            dc_base: dict = dt_cfg_manager.get("base", {})

            if not dc_base or not dc_base.get("enable", False):
                self.logger.warning("没有配置数据中心或没有启用数据中心")
                return False

            # 从配置文件中获取定时任务配置
            alarm_schedule_cfg: dict = dc_base.get("alarm_schedule", {})
            if not alarm_schedule_cfg:
                self.logger.warning("没有配置定时任务")
                return False

            # 配置验证和提取
            login_times: list = alarm_schedule_cfg.get("login_times", [])
            before_open_times: list = alarm_schedule_cfg.get("before_open_times", [])
            sub_id_times: list = alarm_schedule_cfg.get("sub_id_times", [])
            after_close_times: list = alarm_schedule_cfg.get("after_close_times", [])
            check_interval: int = alarm_schedule_cfg.get("check_interval", 60)

            # 时间格式验证
            if not self._validate_time_formats(login_times + before_open_times + sub_id_times + after_close_times):
                self.logger.error("时间格式验证失败，请使用 HH:MM 格式")
                return False

            self._dc_config["login_times"] = login_times
            self._dc_config["before_open_times"] = before_open_times
            self._dc_config["sub_id_times"] = sub_id_times
            self._dc_config["after_close_times"] = after_close_times
            self._dc_config["check_interval"] = check_interval

            bar_generation_list: list = dc_base.get("bar_generation", {}).get("intervals", [])
            # 验证K线配置
            if not bar_generation_list:
                self.logger.warning("K线间隔未配置，请配置默认间隔: [1m, 5m, 15m, 30m, 60m, 1d]")
                bar_generation_list = ["1m", "5m", "15m", "30m", "60m", "1d"]

            self._dc_config["bar_generation_interval"] = bar_generation_list

            self.logger.info("数据中心配置加载成功")
            return True

        except Exception as e:
            self.logger.exception(f"加载数据中心配置失败: {e}")
            return False

    def _validate_time_formats(self, time_list: list) -> bool:
        """验证时间格式"""
        for time_str in time_list:
            try:
                datetime.strptime(time_str, '%H:%M')
            except ValueError:
                self.logger.error(f"无效的时间格式: {time_str}")
                return False
        return True

    def load_broker_config(self) -> bool:
        """
        加载交易商配置
        :return: bool - 配置是否有效
        """
        try:
            brokers_filepath: str = str(get_path_ins.get_config_dir() / BROKERS_FILENAME)
            if not os.path.exists(brokers_filepath):
                self.logger.error(f"经纪商配置文件不存在: {brokers_filepath}")
                return False

            brokers_cfg_manager = ConfigManager(brokers_filepath)
            # 获取启用的broker名称和类型
            rsp_enable_broker = get_enable_broker(brokers_cfg_manager)
            if not rsp_enable_broker:
                self.logger.warning("没有启用的broker")
                return False

            enabled_broker_name = rsp_enable_broker.get("broker_name", "")
            enabled_broker_type = rsp_enable_broker.get("broker_type", "")

            if not enabled_broker_name or not enabled_broker_type:
                self.logger.error("经纪商配置不完整")
                return False

            self._dc_config['broker_name'] = enabled_broker_name
            self._dc_config['broker_type'] = enabled_broker_type
            self._dc_config['broker'] = rsp_enable_broker

            self.logger.info(f"经纪商配置加载成功: {enabled_broker_name}({enabled_broker_type})")
            return True

        except Exception as e:
            self.logger.exception(f"加载经纪商配置失败: {e}")
            return False

    def get_dc_config(self) -> dict[str, Any]:
        """
        获取数据中心配置
        :return:
        """
        return self._dc_config.copy()  # 返回副本避免外部修改

    def stop_dc(self) -> None:
        """
        安全停止数据中心所有组件运行
        :return:
        """
        if self._shutdown_in_progress:
            self.logger.info("关闭操作正在进行中，跳过重复调用")
            return

        self._shutdown_in_progress = True
        self._running = False

        self.logger.info("开始停止数据中心...")

        try:
            # 记录开始时间
            start_time = time.time()

            if self._data_center:
                # 先尝试优雅关闭
                self._data_center.shutdown_dc()

                # 等待一段时间让资源清理完成
                max_wait_time = 30  # 最大等待30秒
                wait_interval = 1

                for i in range(max_wait_time):
                    if not self._is_data_center_active():
                        self.logger.info("数据中心已安全停止")
                        break
                    if i % 5 == 0:  # 每5秒输出一次状态
                        self.logger.info(f"等待数据中心停止... ({i}s)")
                    time.sleep(wait_interval)
                else:
                    self.logger.warning("数据中心未能及时停止，可能有些资源未正确清理")

            elapsed_time = time.time() - start_time
            self.logger.info(f"数据中心停止完成，耗时: {elapsed_time:.2f}秒")

        except Exception as e:
            self.logger.exception(f"停止数据中心过程中发生异常: {e}")
        finally:
            # 通知主循环可以退出了
            self._main_thread_event.set()
            self._perform_final_cleanup()

    def _is_data_center_active(self) -> bool:
        """检查数据中心是否还在运行"""
        return self._data_center.dc_running

    def _perform_final_cleanup(self) -> None:
        """执行最终清理"""
        try:
            # 清理资源
            self._data_center = None
            self._dc_config.clear()

            # 取消注册，避免重复执行
            atexit.unregister(self.stop_dc)

            self.logger.info("最终清理完成")
        except Exception as e:
            self.logger.error(f"最终清理过程中发生异常: {e}")

    def _signal_handler(self, signum, _frame):
        """
        信号处理函数 - 优化版本
        """
        signal_name = {signal.SIGINT: "SIGINT", signal.SIGTERM: "SIGTERM"}.get(signum, str(signum))
        self.logger.info(f"收到信号 {signal_name}，开始优雅关闭...")

        # 在单独的线程中处理关闭，避免信号处理阻塞
        shutdown_thread = threading.Thread(
            target=self._async_shutdown,
            name=f"ShutdownHandler-{signal_name}",
            daemon=True
        )
        shutdown_thread.start()

    def _async_shutdown(self):
        """异步关闭处理"""
        try:
            self.stop_dc()
            # 给一点时间完成清理
            time.sleep(2)
            self.logger.info("优雅关闭完成")
        except Exception as e:
            self.logger.error(f"异步关闭过程中发生异常: {e}")
        finally:
            # subprocess.call(["taskkill", "/F", "/IM", "python.exe"])
            # 正常退出程序
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(1)  # noqa: 立即退出，状态码1
                # os.kill(os.getpid(), signal.SIGTERM)


    def _initialize_data_center(self) -> bool:
        """初始化数据中心实例"""
        try:
            self.logger.info("开始初始化数据中心...")

            # 创建数据中心实例
            self._data_center = DataCenter(self.get_dc_config())

            # 按顺序初始化各个组件
            initialization_steps = [
                ("初始化数据中心配置", self._data_center.init_dc_config),
                ("初始化服务器节点配置", self._data_center.init_broker_config),
                ("初始化事件总线", self._data_center.init_dc_event_bus),
                ("初始化线程池", self._data_center.init_thread_pools),
                ("初始化网关", self._data_center.init_gateway),
            ]

            for step_name, init_func in initialization_steps:
                try:
                    self.logger.info(f"正在{step_name}...")
                    init_func()
                    self.logger.info(f"{step_name}完成")
                except Exception as e:
                    self.logger.exception(f"{step_name}失败: {e}")
                    return False

            self.logger.info("数据中心初始化成功")
            return True

        except Exception as e:
            self.logger.exception(f"初始化数据中心失败: {e}")
            return False

    def _wait_for_thread_pool_initialization(self, timeout=30) -> bool:
        """等待线程池初始化完成"""
        self.logger.info("等待线程池初始化完成...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # 检查数据中心是否已初始化线程池
                if self._data_center.thread_pools_initialized:
                    self.logger.info("线程池初始化确认完成")
                    return True

                # 检查线程池对象是否存在（现在只有主线程池）
                if self._data_center.thread_pool:
                    self.logger.info("线程池对象已创建")
                    return True

                time.sleep(1)
            except Exception as e:
                self.logger.error(f"检查线程池状态失败: {e}")
                time.sleep(1)

        self.logger.error(f"等待线程池初始化超时 ({timeout}秒)")
        return False

    def _start_monitoring(self) -> None:
        """启动监控任务"""
        try:
            # 启动状态监控循环
            monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="DCStatusMonitor",
                daemon=True
            )
            monitor_thread.start()
            self.logger.info("监控线程已启动")

        except Exception as e:
            self.logger.error(f"启动监控失败: {e}")

    def _monitor_loop(self) -> None:
        """监控循环"""
        self.logger.info("监控循环开始")
        last_status_time = time.time()
        last_status_write_time = time.time()
        status_interval = 30  # 每30秒输出一次状态
        status_write_interval = 5  # 每5秒写入一次状态文件

        while self._running and self._data_center and not self._shutdown_in_progress:
            try:
                # 检查闹钟是否在运行
                alarm_running = self._data_center.is_alarm_running()
                if not alarm_running:
                    self.logger.warning("闹钟已停止运行")
                    break

                current_time = time.time()

                # 定期输出状态
                if current_time - last_status_time >= status_interval:
                    if hasattr(self._data_center, 'get_thread_pool_status'):
                        status = self._data_center.get_thread_pool_status()
                        self.logger.info(f"系统状态: {status}")
                    else:
                        self.logger.info("数据中心运行中...")
                    last_status_time = current_time

                # 定期写入状态文件供Web服务读取
                if current_time - last_status_write_time >= status_write_interval:
                    if hasattr(self._data_center, 'write_status_file'):
                        self._data_center.write_status_file()
                    last_status_write_time = current_time

                # 短暂睡眠，避免CPU占用过高
                time.sleep(0.5)

            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                time.sleep(0.5)  # 异常时等待

    def start(self) -> bool:
        """
        启动数据中心
        返回: bool - 启动是否成功
        """
        self.logger.info("开始启动数据中心...")

        try:
            # 1. 加载配置
            if not self.load_dc_config():
                self.logger.error("加载数据中心配置失败")
                return False

            if not self.load_broker_config():
                self.logger.error("加载经纪商配置失败")
                return False

            # 2. 初始化数据中心
            if not self._initialize_data_center():
                self.logger.error("初始化数据中心失败")
                return False

            # 3. 等待线程池完全初始化
            if not self._wait_for_thread_pool_initialization():
                self.logger.error("线程池初始化等待超时")
                return False

            # 4. 启动闹钟调度器
            self.logger.info("启动闹钟调度器...")
            if not self._data_center.start_alarm():
                self.logger.error("启动闹钟调度器失败")
                return False

            # 5. 确认闹钟已启动
            time.sleep(2)  # 等待闹钟线程启动
            if not self._data_center.is_alarm_running():
                self.logger.error("闹钟调度器启动后未正常运行")
                return False

            self._running = True
            self.logger.info("数据中心启动成功，开始运行...")

            # 6. 启动监控
            self._start_monitoring()

            # 7. 阻塞主线程，等待关闭信号
            self._main_loop()

            return True

        except KeyboardInterrupt:
            self.logger.info("接收到键盘中断")
            self.stop_dc()
            return False
        except Exception as e:
            self.logger.exception(f"启动数据中心过程中发生异常: {e}")
            self.stop_dc()
            return False
        finally:
            sys.exit(1)


    def wait_for_shutdown(self) -> None:
        """等待关闭完成"""
        try:
            while self._shutdown_in_progress:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("强制退出等待")

    def _main_loop(self) -> None:
        """主循环，保持程序运行"""
        self.logger.info("进入主循环，等待信号...")

        try:
            while self._running and not self._shutdown_in_progress:
                try:
                    # 检查闹钟是否还在运行
                    if self._data_center and self._data_center.is_alarm_running and not self._data_center.is_alarm_running():
                        self.logger.warning("闹钟已停止运行，准备关闭数据中心")
                        break

                    # 短暂睡眠，避免CPU占用过高
                    time.sleep(0.5)  # 增加睡眠时间，减少CPU占用

                except Exception as e:
                    self.logger.error(f"主循环异常: {e}")

        except KeyboardInterrupt:
            self.logger.info("主循环被键盘中断")
        finally:
            self.logger.info("退出主循环")

def main() -> None:
    """
    主函数
    """
    log = get_logger("Main")
    try:
        log.info("=" * 60)
        log.info("数据中心启动程序")
        log.info("=" * 60)

        start_data_center = StartDataCenter()
        if start_data_center.start():
            log.info("数据中心运行中，等待关闭信号...")
            start_data_center.wait_for_shutdown()
        else:
            logger.error("数据中心启动失败")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.exception(f"程序运行异常: {e}")
        sys.exit(1)
    finally:
        logger.info("程序退出")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(1)  # noqa


if __name__ == '__main__':
    main()
