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
import csv
import time
from typing import Any

from src.constants import INSTRUMENT_EXCHANGE_FILENAME, TICK_DIR_NAME
from src.core.constants import ErrorCode, Interval
from src.core.event import EventType, Event
from src.core.event_bus import EventBus
from src.core.object import SubscribeRequest, TickData
from src.modules.gateway.market_gateway import MarketGateway
from src.modules.gateway.trader_gateway import TraderGateway
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger
from src.utils.utility import load_json


class DataCenter(object):

    def __init__(self, event_bus: EventBus, data_center_config: dict[str, Any]) -> None:
        self.event_bus: EventBus = event_bus
        self.data_center_config: dict[str, Any] = data_center_config  # 数据中心配置
        self.logger = get_logger(__class__.__name__)
        self._running: bool = False  # 数据中心运行状态
        self.market_gateway: MarketGateway | None = None  # 行情网关
        self.trader_gateway: TraderGateway | None = None  # 交易网关
        self.broker_info: dict = {}  # 交易所节点信息
        self.md_login_status: bool = False
        self.td_login_status: bool = False
        self.trading_day: str = ""  # 交易日
        # 是否更新合约文件，更新一次之后 symbol_contract_map 就会有合约基本信息，比如交易所代码等
        self.is_update_instrument_file: bool = True

        self.sub_ins_list: list[str] = []  # 订阅的合约
        self.sub_kline_type: list[Interval] = []  # 订阅的K线类型(周期)

        self.csv_file = None
        self.csv_writer = None

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
            self.logger.info(rsp_login_data.get("message"))
            self.td_login_status = True
            self.trading_day = rsp_login_data.get("data", {}).get("trading_day")  # 获取登录后的交易日

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

    def td_gateway_ready_handler(self, event: Event):
        self.logger.info(f"收到交易网关就绪事件，事件类型：{event.event_type}")
        rsp_login_data = event.payload
        if rsp_login_data and rsp_login_data.get("code") == 0:
            self.logger.info(rsp_login_data.get("message"))
            self.subscribe_all_instruments()

    def td_confirm_success_handler(self, event: Event):
        self.logger.info(f"收到结算单确认成功事件，事件类型：{event.event_type}")
        rsp_login_data = event.payload
        if rsp_login_data and rsp_login_data.get("code") == 0:
            self.logger.info(rsp_login_data.get("message"))
            self.subscribe_all_instruments()

    def sub_ins_show_handler(self, event: Event):
        self.logger.info(f"返回tick事件：{event.payload.get('code')}, {event.payload.get('message')}")
        tick: TickData = event.payload.get("data", None)
        print(f"收到tick数据：{tick}")
        tick_data_list = [
            tick.trading_day,
            tick.exchange_id,
            tick.last_price,
            tick.volume,
            tick.open_interest,
            tick.pre_settlement_price,
            tick.pre_close_price,
            tick.pre_open_interest,
            tick.open_price,
            tick.highest_price,
            tick.lowest_price,
            tick.volume,
            tick.turnover,
            tick.open_interest,
            tick.close_price,
            tick.settlement_price,
            tick.upper_limit_price,
            tick.lower_limit_price,
            tick.pre_delta,
            tick.curr_delta,
            tick.update_time,
            tick.update_millisec,
            tick.bid_price_1,
            tick.bid_volume_1,
            tick.ask_price_1,
            tick.ask_volume_1,
            tick.bid_price_2,
            tick.bid_volume_2,
            tick.ask_price_2,
            tick.ask_volume_2,
            tick.bid_price_3,
            tick.bid_volume_3,
            tick.ask_price_3,
            tick.ask_volume_3,
            tick.bid_price_4,
            tick.bid_volume_4,
            tick.ask_price_4,
            tick.ask_volume_4,
            tick.bid_price_5,
            tick.bid_volume_5,
            tick.ask_price_5,
            tick.ask_volume_5,
            tick.average_price,
            tick.action_day,
            tick.banding_upper_price,
            tick.banding_lower_price,
            tick.timestamp
        ]
        self.csv_writer.writerow(tick_data_list)
        self.csv_file.flush()
        # TODO: 在合适的地方添加csv文件关闭逻辑 self.csv_file.close()

    def _register_event_handlers(self, is_update_ins: bool = False) -> None:
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
        if is_update_ins:
            # 订阅交易网关就绪事件
            self.event_bus.subscribe(EventType.TD_GATEWAY_READY, self.td_gateway_ready_handler)
        else:
            # 订阅结算单确认成功事件
            self.event_bus.subscribe(EventType.TD_CONFIRM_SUCCESS, self.td_confirm_success_handler)
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

            if self.is_update_instrument_file:
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

    def subscribe_all_instruments(self):
        ins_exchange_dict = load_json(str(get_path_ins.get_config_dir() / INSTRUMENT_EXCHANGE_FILENAME))
        # 加载所有合约代码
        self.sub_ins_list = [ins for ins in list(ins_exchange_dict.keys())]
        self.logger.info(f"订阅所有合约: {self.sub_ins_list}")

        # 初始化生成csv文件
        for instrument_id in self.sub_ins_list:
            prefix_tick_path = str(get_path_ins.get_data_dir() / TICK_DIR_NAME)
            self.csv_file = open(f"{prefix_tick_path}/{self.trading_day}/{instrument_id}.csv", 'a', newline='')
            self.csv_writer = csv.writer(self.csv_file)

        if self.sub_ins_list:
            for ins in self.sub_ins_list:
                self.market_gateway.subscribe(SubscribeRequest(ins))
                time.sleep(1)

