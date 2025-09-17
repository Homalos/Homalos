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
import time
from typing import Any

from src.core.constants import ErrorCode
from src.core.event import EventType, Event
from src.core.event_bus import EventBus
from src.core.object import SubscribeRequest
from src.modules.gateway.market_gateway import MarketGateway
from src.modules.gateway.trader_gateway import TraderGateway
from src.utils.log import get_logger


class DataCenter(object):

    def __init__(self, event_bus: EventBus, data_center_config: dict[str, Any]) -> None:
        self.event_bus = event_bus
        self.data_center_config = data_center_config  # 数据中心配置
        self.logger = get_logger(__class__.__name__)
        self._running: bool = False  # 数据中心运行状态
        self.market_gateway: MarketGateway | None = None  # 行情网关
        self.trader_gateway: TraderGateway | None = None  # 交易网关
        self.broker_info: dict = {}  # 交易所节点信息
        self.md_login_status = False
        self.td_login_status = False

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
            self.md_login_status = True
            self.logger.info(rsp_login_data.get("message"))

    def td_gateway_login_handler(self, event: Event) -> None:
        """
        交易网关登录事件处理
        :param event: 交易网关登录事件
        :return:
        """
        self.logger.info("收到交易网关登录事件，判断交易服务器是否登录成功")
        rsp_login_data = event.payload
        self.logger.info(f"收到交易网关登录事件数据：{rsp_login_data}")
        if rsp_login_data and rsp_login_data.get("code") == 0:
            self.td_login_status = True
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

    # def ins_file_updated_handler(self, event: Event):
    #     self.logger.info(f"收到合约交易所映射文件更新事件，事件类型：{event.event_type}")
    #     rsp_login_data = event.payload
    #     if rsp_login_data and rsp_login_data.get("code") == 0:
    #         self.logger.info(rsp_login_data.get("message"))
    #         self.get_sub_ins_data()

    def td_gateway_ready_handler(self, event: Event):
        self.logger.info(f"收到交易网关就绪事件，事件类型：{event.event_type}")
        rsp_login_data = event.payload
        if rsp_login_data and rsp_login_data.get("code") == 0:
            self.logger.info(rsp_login_data.get("message"))
            self.get_sub_ins_data()

    def sub_ins_show_handler(self, event: Event):
        self.logger.info(f"收到事件类型：{event.event_type}")
        self.logger.info(f"收到tick数据：{event.payload}")

    def _register_event_handlers(self) -> None:
        """
        注册事件处理器
        :return: None
        """
        # 订阅行情网关登录事件
        self.event_bus.subscribe(EventType.MD_GATEWAY_LOGIN, self.md_gateway_login_handler)
        # 订阅交易网关登录事件
        self.event_bus.subscribe(EventType.TD_GATEWAY_LOGIN, self.td_gateway_login_handler)
        # 订阅事件总线停止事件
        self.event_bus.subscribe(EventType.EVENT_BUS_SHUTDOWN, self.datacenter_shutdown_handler)
        # 订阅交易网关就绪事件
        self.event_bus.subscribe(EventType.TD_GATEWAY_READY, self.td_gateway_ready_handler)
        # 订阅行情数据
        self.event_bus.subscribe(EventType.TICK, self.sub_ins_show_handler)

    def _init_gateway(self):
        self.market_gateway = MarketGateway(self.event_bus, gateway_name="DataCenter_MD")
        self.trader_gateway = TraderGateway(self.event_bus, gateway_name="DataCenter_TD")

        self.broker_info: dict = self.data_center_config.get('broker', {})
        broker_config: dict = self.broker_info.get('broker_config', {})
        self.logger.info(f"加载服务器配置: {broker_config}")

        # 连接行情服务器并登录
        self.market_gateway.connect(broker_config)

        # # 连接交易服务器并登录
        self.trader_gateway.connect(broker_config)

    def start(self) -> bool:
        """启动数据中心"""
        try:
            if self._running:
                self.logger.warning("数据中心已在运行")
                return True

            self.logger.info("启动数据中心......")

            # 初始化网关
            self._init_gateway()

            start_time: float = time.time()
            timeout: float = 5.0
            while not (self.md_login_status and self.td_login_status):
                # 检查是否超时
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    self.logger.warning(f"等待登录超时 ({timeout}秒)，当前状态 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
                    break
                time.sleep(0.1)

            if not self.md_login_status or not self.td_login_status:
                self.logger.error(f"网关登录失败 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
                self._running = False
                return False

            self.logger.info(f"所有网关登录成功 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
            self._running = True
            # 发布数据中心启动事件(成功)
            self.event_bus.publish(Event(EventType.DATA_CENTER_START, {
                "code": ErrorCode.SUCCESS,
                "message": "数据中心启动成功",
                "data": None
            }))
            self.logger.info("数据中心启动成功")

            # 发布更新合约事件
            self.event_bus.publish(Event(EventType.DATA_CENTER_QRY_INS, {}))
            self.logger.info("发布更新合约事件成功")
            return True
        except Exception as e:
            self.logger.error(f"启动数据中心失败: {e}", exc_info=True)
            self.stop()
            # 发布数据中心启动事件(成功)
            self.event_bus.publish(Event(EventType.DATA_CENTER_START, {
                "code": ErrorCode.DATA_CENTER_START_FAILED,
                "message": "数据中心启动失败",
                "data": None
            }))
            return False

    def stop(self) -> None:
        if not self._running:
            self.logger.info("数据中心未在运行")
            return

        self.logger.info("停止数据中心...")

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

        # 设置停止标志
        self._running = False

    def get_status(self) -> bool:
        return self._running

    def get_sub_ins_data(self):
        sub_req = SubscribeRequest()
        sub_req.instrument_id = "SA601"
        self.market_gateway.subscribe(sub_req)

