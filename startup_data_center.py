#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : startup_data_center.py
@Date       : 2025/9/13 20:56
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据中心启动入口
"""
import asyncio
import sys
import traceback
from pathlib import Path
from typing import Optional

from src.core.event import EventType
from src.core.event_bus import EventBus
from src.modules.data_center.data_center import DataCenter
from src.utils.config_manager import ConfigManager
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger, logger
from src.utils.utility import load_yaml, get_enable_broker

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class StartupDataCenter:

    def __init__(self,
                 brokers_file_path: str = "brokers.yaml",
                 config_file_path: str = "data_center.yaml"
                 ) -> None:
        self.brokers_file_path: str = str(get_path_ins.get_config_dir() / brokers_file_path)
        self.config_file_path: str = str(get_path_ins.get_config_dir() / config_file_path)
        self.logger = get_logger(self.__class__.__name__)
        self.event_bus: Optional[EventBus] = None
        self.data_center: Optional[DataCenter] = None  # 数据中心实例
        self.data_center_config: dict = {}
        self.running: bool = False

    def shutdown_handler(self, event):
        """处理停止事件"""
        self.logger.info("StartupDataCenter收到停止信号，开始停止应用...")
        self.logger.info(f"事件类型：{event.event_type}")
        self.running = False

    async def initialize(self) -> bool:
        # brokers_config = load_yaml(self.brokers_file_path)
        cfg = ConfigManager(self.brokers_file_path)

        rsp_enable_broker = get_enable_broker(cfg)
        if not rsp_enable_broker:
            self.logger.warning("没有启用的broker")
            return False

        enabled_broker_name = rsp_enable_broker.get("broker_name")
        enabled_broker_type = rsp_enable_broker.get("broker_type")

        self.logger.info(f"启用的broker名称: {enabled_broker_name}，broker类型: {enabled_broker_type}")

        data_center_config = load_yaml(self.config_file_path)
        if not data_center_config:
            self.logger.warning("没有配置data_center")
            return False

        base_config = data_center_config.get("base")
        if not base_config:
            self.logger.warning("没有配置data_center.base")
            return False
        enable_data_center = base_config.get("enable")
        if not enable_data_center:
            self.logger.warning("没有启用data_center")
            return False

        self.data_center_config['broker'] = rsp_enable_broker

        self.logger.info("创建事件总线：DataCenter")
        self.event_bus = EventBus(
            context = "DataCenter"
        )

        # 注册停止事件处理器
        self.event_bus.subscribe(EventType.EVENT_BUS_SHUTDOWN, self.shutdown_handler)

        # 创建数据中心（数据中心将独立管理网关连接）
        self.logger.info("开始创建数据中心实例...")
        try:
            self.data_center = DataCenter(self.event_bus, self.data_center_config)
            self.logger.info("数据中心实例创建成功")
            return True
        except Exception as dc_error:
            self.logger.error(f"创建数据中心实例失败: {dc_error}")
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False

    async def start(self) -> bool:
        """启动数据中心应用"""
        if not await self.initialize():
            return False

        # 启动数据中心（数据中心内部会自动创建和连接网关）
        if self.data_center:
            self.data_center.start()
            logger.info("数据中心应用初始化成功")

        # 网关已在数据中心中自动连接
        self.running = True
        logger.info("数据中心应用启动成功，开始7x24小时运行...")

        # 主循环
        try:
            while self.running:
                # 检查组件状态
                if self.data_center and not self.data_center.get_status():
                    logger.warning("数据中心连接断开，等待自动重连......")
                # 避免CPU占用过高，添加短暂休眠
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"主循环异常: {e}")
            return False
        return True

    async def shutdown(self) -> None:
        """关闭数据中心应用"""
        try:
            self.running = False

            if self.data_center:
                self.data_center.stop()

            if self.event_bus:
                self.event_bus.stop()

            logger.info("数据中心应用已关闭")

        except Exception as e:
            logger.error(f"数据中心应用关闭失败: {e}")


# 全局应用实例
data_center_app = StartupDataCenter()


async def main() -> None:
    # 注册信号处理器
    try:
        # 启动数据中心应用
        await data_center_app.start()
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，开始关闭数据中心...")
    except Exception as e:
        logger.error(f"数据中心运行异常: {e}")
    finally:
        logger.info("收到关闭信号，快速关闭数据中心...")
        # 快速关闭，不等待异步操作
        await data_center_app.shutdown()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("收到 Ctrl+C，程序退出")
