# -*- coding: utf-8 -*-
"""
DataService全功能混合测试脚本（修正版，异步链路/并发/活跃合约优化）
"""
import asyncio
import os
import threading
from unittest.mock import MagicMock

import pytest

from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.services.data_service import DataService
from src.core.object import TickData, BarData
from src.config.constant import Exchange, Interval
from datetime import datetime

# 统一使用活跃合约
ACTIVE_TICKER = "FG509"
ACTIVE_EXCHANGE = "CZCE"

class DummyTick:
    def __init__(self, symbol=ACTIVE_TICKER, exchange=ACTIVE_EXCHANGE, dt=None):
        from datetime import datetime
        self.symbol = symbol
        self.exchange = MagicMock(value=exchange)
        self.datetime = dt or datetime.now()
        self.last_price = 100.0
        self.volume = 10
        self.turnover = 1000
        self.open_interest = 100
        self.bid_price_1 = 99.5
        self.ask_price_1 = 100.5
        self.bid_volume_1 = 5
        self.ask_volume_1 = 5

class DummyBar:
    def __init__(self, symbol=ACTIVE_TICKER, exchange=ACTIVE_EXCHANGE, interval='1m', dt=None):
        from datetime import datetime
        self.symbol = symbol
        self.exchange = MagicMock(value=exchange)
        self.interval = MagicMock(value=interval)
        self.datetime = dt or datetime.now()
        self.open_price = 99.0
        self.high_price = 101.0
        self.low_price = 98.0
        self.close_price = 100.0
        self.volume = 100
        self.turnover = 10000
        self.open_interest = 100

class EventCapture:
    def __init__(self):
        self.events = []
        self.lock = threading.Lock()
    def __call__(self, event):
        with self.lock:
            self.events.append((event.type, event.data))
    def get(self, event_type=None):
        with self.lock:
            if event_type:
                return [e for e in self.events if e[0] == event_type]
            return list(self.events)
    def clear(self):
        with self.lock:
            self.events.clear()

@pytest.fixture(scope="module")
def event_bus():
    bus = EventBus("TestBus")
    yield bus
    bus.stop()

@pytest.fixture(scope="module")
def config_manager(tmp_path_factory):
    tmpdir = tmp_path_factory.mktemp("db")
    cfg = MagicMock()
    cfg.get.side_effect = lambda k, d=None: {
        "database.path": str(tmpdir/"tests.db"),
        "database.batch_size": 2,
        "database.flush_interval": 1,
        "data.market.buffer_size": 10,
        "data.market.enable_persistence": True
    }.get(k, d)
    return cfg

@pytest.fixture(scope="module")
def data_service(event_bus, config_manager):
    ds = DataService(event_bus, config_manager)
    asyncio.get_event_loop().run_until_complete(ds.initialize())
    yield ds
    asyncio.get_event_loop().run_until_complete(ds.shutdown())

@pytest.fixture
def event_capture(event_bus):
    cap = EventCapture()
    event_bus.add_monitor(cap)
    yield cap
    event_bus.remove_monitor(cap)

@pytest.mark.asyncio
async def test_database_init(data_service):
    db_path = data_service.db_manager.db_path
    assert os.path.exists(db_path)

@pytest.mark.asyncio
async def test_tick_bar_persist(data_service):
    tick = DummyTick()
    bar = DummyBar()
    await data_service.db_manager.save_tick_data(tick)
    await data_service.db_manager.save_bar_data(bar)
    await asyncio.sleep(2)
    rows = await data_service.db_manager.query_tick_data(ACTIVE_TICKER, ACTIVE_EXCHANGE)
    assert rows
    rows = await data_service.db_manager.query_bar_data(ACTIVE_TICKER, ACTIVE_EXCHANGE, "1m")
    assert rows

@pytest.mark.asyncio
async def test_subscribe_unsubscribe(data_service, event_bus):
    await data_service.subscribe_market_data([ACTIVE_TICKER], "strat1")
    assert "strat1" in data_service.strategy_subscriptions
    assert ACTIVE_TICKER in data_service.subscribers
    await data_service.unsubscribe_market_data([ACTIVE_TICKER], "strat1")
    assert "strat1" not in data_service.strategy_subscriptions or ACTIVE_TICKER not in data_service.strategy_subscriptions.get("strat1", set())

@pytest.mark.asyncio
async def test_tick_bar_event_chain(data_service, event_bus, event_capture):
    await data_service.subscribe_market_data([ACTIVE_TICKER], "strat2")
    await asyncio.sleep(0.2)  # 确保订阅生效
    tick = TickData(
        symbol=ACTIVE_TICKER,
        exchange=Exchange.CZCE,
        datetime=datetime.now(),
        gateway_name="unittest"
    )
    bar = BarData(
        symbol=ACTIVE_TICKER,
        exchange=Exchange.CZCE,
        datetime=datetime.now(),
        gateway_name="unittest",
        interval=Interval.MINUTE
    )
    event_bus.publish(Event("market.tick.raw", tick))
    event_bus.publish(Event("market.bar.raw", bar))
    # 等待异步分发
    for _ in range(10):
        await asyncio.sleep(0.2)
        ticks = [e for e in event_capture.get() if e[0] == EventType.MARKET_TICK]
        bars = [e for e in event_capture.get() if e[0] == EventType.MARKET_BAR]
        if ticks and bars:
            break
    assert ticks and bars

@pytest.mark.asyncio
async def test_query_interface(data_service):
    tick = DummyTick()
    bar = DummyBar()
    await data_service.db_manager.save_tick_data(tick)
    await data_service.db_manager.save_bar_data(bar)
    await asyncio.sleep(2)
    rows = await data_service.db_manager.query_tick_data(ACTIVE_TICKER, ACTIVE_EXCHANGE)
    assert rows
    rows = await data_service.db_manager.query_bar_data(ACTIVE_TICKER, ACTIVE_EXCHANGE, "1m")
    assert rows

@pytest.mark.asyncio
async def test_error_handling(data_service, event_bus, event_capture):
    event_bus.publish(Event("market.tick.raw", "not_a_tick"))
    event_bus.publish(Event("market.bar.raw", 12345))
    await asyncio.sleep(0.5)
    orig = data_service.db_manager._flush_tick_batch
    data_service.db_manager._flush_tick_batch = lambda: (_ for _ in ()).throw(Exception("db error"))
    tick = DummyTick("rberror", ACTIVE_EXCHANGE)
    await data_service.db_manager.save_tick_data(tick)
    await asyncio.sleep(2)
    data_service.db_manager._flush_tick_batch = orig

@pytest.mark.asyncio
async def test_concurrent_push(data_service):
    async def push():
        tick = DummyTick("FG510", ACTIVE_EXCHANGE)
        await data_service.db_manager.save_tick_data(tick)
    await asyncio.gather(*(push() for _ in range(5)))
    await asyncio.sleep(2)
    rows = await data_service.db_manager.query_tick_data("FG510", ACTIVE_EXCHANGE)
    assert rows

@pytest.mark.asyncio
async def test_service_stats(data_service):
    stats = data_service.get_service_stats()
    assert "tick_count" in stats and "bar_count" in stats
    assert "buffer_size" in stats and "db_path" in stats
    print("服务统计信息:", stats) 