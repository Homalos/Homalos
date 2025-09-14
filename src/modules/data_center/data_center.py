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

职责：管理数据中心的业务逻辑
1. self._running 控制数据中心内部状态
2. 负责管理网关连接和数据处理
"""
from typing import Any

from src.core.constants import ErrorCode
from src.core.event import EventType, Event
from src.core.event_bus import EventBus
from src.modules.gateway.market_gateway import MarketGateway
from src.utils.log import get_logger


class DataCenter(object):

    def __init__(self, event_bus: EventBus, data_center_config: dict[str, Any]) -> None:
        self.event_bus = event_bus
        self.data_center_config = data_center_config  # 数据中心配置
        self.logger = get_logger(__class__.__name__)
        self._running: bool = False  # 数据中心运行状态
        self.market_gateway: MarketGateway | None = None  # 行情网关
        self.broker_info: dict = {}  # 交易所节点信息

        self._register_event_handlers()  # 注册事件处理器

    def md_gateway_login_handler(self, event: Event) -> None:
        """
        处理行情网关登录事件
        :param event: 行情网关登录事件
        :return:
        """
        self.logger.info("收到行情网关登录事件，判断行情服务器是否登录成功")
        rsp_login_data: dict = event.payload
        self.logger.info(f"收到行情网关登录事件数据：{rsp_login_data}")
        if rsp_login_data and rsp_login_data.get("code") == 0:
            self.logger.info(rsp_login_data.get("message"))

    def datacenter_shutdown_handler(self, event: Event) -> None:
        """
        负责数据中心业务级别的停止（数据中心状态管理），处理停止事件
        self._running = False → 数据中心状态更新
        :param event: 数据中心关闭事件
        :return: None
        """
        self.logger.info("数据中心收到停止信号，开始停止...")
        self.logger.info(f"收到事件类型：{event.event_type}")
        self._running = False

    def _register_event_handlers(self) -> None:
        """
        注册事件处理器
        :return: None
        """
        # 订阅行情网关登录事件
        self.event_bus.subscribe(EventType.MD_GATEWAY_LOGIN, self.md_gateway_login_handler)
        # 订阅事件总线停止事件
        self.event_bus.subscribe(EventType.EVENT_BUS_SHUTDOWN, self.datacenter_shutdown_handler)

    def _init_gateway(self):
        self.market_gateway = MarketGateway(self.event_bus, gateway_name="DataCenter")

        self.broker_info: dict = self.data_center_config.get('broker', {})
        broker_config: dict = self.broker_info.get('broker_config', {})

        # 连接行情服务器并登录
        self.market_gateway.connect(broker_config)


    def start(self) -> None:
        """启动数据中心"""
        try:
            if self._running:
                self.logger.warning("数据中心已在运行")
                return

            self.logger.info("启动数据中心......")

            # 初始化网关
            self._init_gateway()
            # 设置运行状态
            self._running = True

            # 发布数据中心启动事件(成功)
            self.event_bus.publish(Event(EventType.DATA_CENTER_START, {
                "code": ErrorCode.SUCCESS,
                "message": "数据中心启动成功",
                "data": None
            }))

            self.logger.info("数据中心启动成功")

        except Exception as e:
            self.logger.error(f"启动数据中心失败: {e}", exc_info=True)
            self.stop()
            # 发布数据中心启动事件(成功)
            self.event_bus.publish(Event(EventType.DATA_CENTER_START, {
                "code": ErrorCode.DATA_CENTER_START_FAILED,
                "message": "数据中心启动失败",
                "data": None
            }))
            raise

    def stop(self) -> None:
        if not self._running:
            self.logger.info("数据中心未在运行")
            return

        self.logger.info("停止数据中心...")

        # 设置停止标志
        self._running = False

        # 停止网关
        if self.market_gateway:
            self.market_gateway.close()
            self.market_gateway = None

        # 发布数据中心断开事件
        self.event_bus.publish(Event(EventType.DATA_CENTER_STOP, {
            "code": ErrorCode.SUCCESS,
            "message": "数据中心已停止",
            "data": None
        }))

        # self.event_bus.stop()

    def get_status(self) -> bool:
        return self._running