#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_send_order.py
@Date       : 2025/9/14 21:29
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 测试下单
"""
import time

from src.core.constants import Exchange, Direction, OrderType, Offset
from src.core.object import OrderRequest
from src.modules.gateway.trader_gateway import TraderGateway
from src.utils.log import get_logger

_logger = get_logger("test_send_order")


def main():
    _logger.info("测试下单")

    trader = TraderGateway()

    # CTP配置（使用SimNow测试环境）
    # CTP configuration (using SimNow test environment)
    ctp_config = {
        # "td_address": "tcp://182.254.243.31:30001",  # 交易服务器地址 Trade server address
        "td_address": "tcp://182.254.243.31:40001",  # 7x24易服务器地址 Trade server address
        "broker_id": "",  # 经纪商代码 Broker Code
        "user_id": "",  # 用户代码 User Code
        "password": "",  # password
        "appid": "simnow_client_test",
        "auth_code": "0000000000000000"
    }

    trader.connect(setting=ctp_config)

    # 等待连接和登录完成
    _logger.info("等待连接和登录完成...")

    # 报单一些常用的期货合约（SimNow模拟环境中的活跃合约）
    _logger.info("开始下单测试...")

    order_req = OrderRequest()
    order_req.instrument_id = "SA601"
    order_req.exchange_id = Exchange.CZCE
    order_req.direction = Direction.LONG
    order_req.order_type = OrderType.LIMIT
    order_req.volume = 1
    order_req.price = 1288
    order_req.offset = Offset.OPEN

    ret_order_id = trader.send_order(order_req)
    _logger.info(f"下单完成，订单号: {ret_order_id}")

    # 等待一段时间观察订单状态
    _logger.info("等待5秒观察订单状态...")
    time.sleep(5)

    # 显示订单状态汇总
    trader.get_order_status_summary()

    # # 如果需要测试撤单，可以取消注释下面的代码
    # print("\n🛑 测试撤单...")
    # trader.cancel_order("SA601")
    # time.sleep(2)
    # trader.get_order_status_summary()

    try:
        # 保持程序运行60秒来观察订单状态变化待) ❌(失败)")
        for i in range(12):  # 60秒分成12个5秒间隔
            time.sleep(3)
            _logger.info(f"时间检查点 {i + 1}/12 (已运行{(i + 1) * 5}秒)")
            trader.get_order_status_summary()

    except KeyboardInterrupt:
        _logger.info("用户中断程序")
    finally:
        _logger.info("最终订单状态汇总:")
        trader.get_order_status_summary()
        _logger.info("正在关闭连接...")
        trader.close()
        _logger.info("程序结束")


if __name__ == "__main__":
    main()
