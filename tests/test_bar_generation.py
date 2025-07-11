# -*- coding: utf-8 -*-
"""
独立测试脚本：验证DataService多周期K线合成效果
"""
import time
from datetime import datetime, timedelta
from src.core.event_bus import EventBus
from src.core.event import Event
from src.core.object import TickData
from src.config.constant import Exchange
from src.services.data_service import DataService
from unittest.mock import MagicMock

class BarCapture:
    def __init__(self):
        self.bars = []
    def __call__(self, event):
        if event.type == "market.bar":
            self.bars.append(event.data)
            print(f"[BAR] {event.data.symbol} {event.data.interval} {event.data.datetime} O:{event.data.open_price} H:{event.data.high_price} L:{event.data.low_price} C:{event.data.close_price} V:{event.data.volume}")

def simulate_ticks(event_bus, symbol, exchange, start_dt, count, interval_sec=10):
    """模拟推送一组tick数据，跨越多个K线周期"""
    dt = start_dt
    price = 100.0
    for i in range(count):
        price += (i % 5 - 2) * 0.5  # 模拟波动
        tick = TickData(
            symbol=symbol,
            exchange=exchange,
            datetime=dt,
            gateway_name="unittest",
            last_price=price,
            volume=100 + i,
            turnover=10000 + i * 10,
            open_interest=1000 + i
        )
        event_bus.publish(Event("market.tick.raw", tick))
        dt += timedelta(seconds=interval_sec)
        time.sleep(0.01)  # 模拟真实推送节奏

def main():
    symbol = "FG509"
    exchange = Exchange.CZCE
    event_bus = EventBus("BarTest")
    # 配置DataService（mock config）
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
    # 推送模拟tick
    start_dt = datetime(2025, 7, 10, 9, 0, 0)
    print("推送tick数据，观察K线合成...")
    simulate_ticks(event_bus, symbol, exchange, start_dt, count=40, interval_sec=15)
    print("\n合成K线数量：", len(bar_cap.bars))
    # 关闭服务
    ds.db_manager.stop()
    event_bus.stop()

if __name__ == "__main__":
    main() 