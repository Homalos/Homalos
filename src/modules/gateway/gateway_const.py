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
from src.ctp.api.ctp_constant import THOST_FTDC_OST_Unknown, THOST_FTDC_OST_AllTraded, \
    THOST_FTDC_OST_PartTradedQueueing, THOST_FTDC_OST_PartTradedNotQueueing, THOST_FTDC_OST_NoTradeQueueing, \
    THOST_FTDC_OST_NoTradeNotQueueing, THOST_FTDC_OST_Canceled


class GatewayConst:

    # 错误码与错误原因映射
    reason_mapping = {
        0x1001: "网络读失败",
        0x1002: "网络写失败",
        0x2001: "接收心跳超时",
        0x2002: "发送心跳失败",
        0x2003: "收到错误报文"
    }

    # 订单状态常量映射  Order Status Constant Mapping
    order_status_names = {
        THOST_FTDC_OST_Unknown: "未知",
        THOST_FTDC_OST_AllTraded: "全部成交",
        THOST_FTDC_OST_PartTradedQueueing: "部分成交还在队列中",
        THOST_FTDC_OST_PartTradedNotQueueing: "部分成交不在队列中",
        THOST_FTDC_OST_NoTradeQueueing: "未成交还在队列中",
        THOST_FTDC_OST_NoTradeNotQueueing: "未成交不在队列中",
        THOST_FTDC_OST_Canceled: "撤单"
    }