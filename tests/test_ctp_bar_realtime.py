# -*- coding: utf-8 -*-
"""
CTP实时tick驱动K线合成集成测试脚本
"""
import asyncio
import sys
import time
from src.core.event_bus import EventBus
from src.services.data_service import DataService
from src.ctp.gateway.market_data_gateway import MarketDataGateway, symbol_contract_map
from src.core.object import ContractData, SubscribeRequest
from src.config.constant import Exchange, Product
from src.core.event import EventType
from unittest.mock import MagicMock

class BarCapture:
    def __init__(self):
        self.bars = []
    def __call__(self, event):
        if event.type == "market.bar":
            self.bars.append(event.data)
            print(f"[BAR] {event.data.symbol} {event.data.interval} {event.data.datetime} O:{event.data.open_price} H:{event.data.high_price} L:{event.data.low_price} C:{event.data.close_price} V:{event.data.volume}")

async def main():
    # 配置
    test_symbols = ["FG509", "SA509"]
    ctp_config = {
        "userid": "160219",
        "password": "donny@103010",
        "broker_id": "9999",
        "md_address": "tcp://182.254.243.31:30011",
        "appid": "simnow_client_test",
        "auth_code": "0000000000000000"
    }
    # 预加载合约
    for symbol in test_symbols:
        contract = ContractData(
            symbol=symbol,
            exchange=Exchange.CZCE,
            name=f"{symbol}合约",
            product=Product.FUTURES,
            size=1,
            price_tick=0.01,
            min_volume=1,
            gateway_name="CTP_MD"
        )
        symbol_contract_map[symbol] = contract
    # 初始化
    event_bus = EventBus("CTPBarTest")
    config = MagicMock()
    config.get.side_effect = lambda k, d=None: {
        "database.path": ":memory:",
        "database.batch_size": 2,
        "database.flush_interval": 1,
        "data.market.buffer_size": 10,
        "data.market.enable_persistence": False
    }.get(k, d)
    ds = DataService(event_bus, config)
    bar_cap = BarCapture()
    event_bus.add_monitor(bar_cap)
    # 启动行情网关
    md_gateway = MarketDataGateway(event_bus, "CTP_MD")
    md_gateway.connect(ctp_config)
    await asyncio.sleep(2)
    # 订阅合约
    for symbol in test_symbols:
        req = SubscribeRequest(symbol=symbol, exchange=Exchange.CZCE)
        md_gateway.subscribe(req)
        await asyncio.sleep(0.5)
    print("已连接CTP并订阅，开始实时tick→K线合成输出... (Ctrl+C退出)")
    try:
        while True:
            await asyncio.sleep(5)
            print(f"累计合成K线数量: {len(bar_cap.bars)}")
    except KeyboardInterrupt:
        print("\n用户中断，退出...")
    finally:
        ds.db_manager.stop()
        event_bus.stop()

if __name__ == "__main__":
    if sys.version_info < (3, 10):
        print("❌ 需要Python 3.10或更高版本")
        sys.exit(1)
    asyncio.run(main()) 