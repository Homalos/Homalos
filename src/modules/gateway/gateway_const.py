#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : gateway_const.py
@Date       : 2025/9/10 21:26
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 网关常量
"""
from src.core.constants import Status, ErrorReason
from src.ctp.api.ctp_constant import (
    THOST_FTDC_OST_Unknown,
    THOST_FTDC_OST_AllTraded,
    THOST_FTDC_OST_PartTradedQueueing,
    THOST_FTDC_OST_PartTradedNotQueueing,
    THOST_FTDC_OST_NoTradeQueueing,
    THOST_FTDC_OST_NoTradeNotQueueing,
    THOST_FTDC_OST_Canceled
)


class GatewayConst:

    # 错误码与错误原因映射
    reason_mapping: dict[str, ErrorReason] = {
        "0x1001": ErrorReason.REASON_0x1001,
        "0x1002": ErrorReason.REASON_0x1002,
        "0x2001": ErrorReason.REASON_0x2001,
        "0x2002": ErrorReason.REASON_0x2002,
        "0x2003": ErrorReason.REASON_0x2003
    }

    # 订单状态常量映射  Order Status Constant Mapping
    order_status_names: dict[str, Status] = {
        THOST_FTDC_OST_Unknown: Status.UNKNOWN,
        THOST_FTDC_OST_AllTraded: Status.ALL_TRADED,
        THOST_FTDC_OST_PartTradedQueueing: Status.PART_TRADED_QUEUEING,
        THOST_FTDC_OST_PartTradedNotQueueing: Status.PART_TRADED_NOT_QUEUEING,
        THOST_FTDC_OST_NoTradeQueueing: Status.NO_TRADE_QUEUEING,
        THOST_FTDC_OST_NoTradeNotQueueing: Status.NO_TRADE_NOT_QUEUEING,
        THOST_FTDC_OST_Canceled: Status.CANCELED
    }