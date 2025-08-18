#!/usr/bin/env python
"""
异步事件总线 AsyncEventBus 的单元测试
"""
import time

from src.core.async_event_bus import AsyncEventBus
from src.core.event import Event, EventType


def wait_a_bit(seconds: float = 0.15) -> None:
    time.sleep(seconds)


def test_basic_publish_and_handle_sync_and_async_handlers() -> None:
    bus = AsyncEventBus(name="test-basic", interval=1)

    called = {"sync": 0, "async": 0, "global": 0}

    def sync_handler(e: Event) -> None:
        called["sync"] += 1

    async def async_handler(e: Event) -> None:
        called["async"] += 1

    def global_handler(e: Event) -> None:
        called["global"] += 1

    bus.subscribe("custom.event", sync_handler)
    # 类型忽略异步处理器的类型检查，因为实际运行时支持
    bus.subscribe("custom.event", async_handler)  # type: ignore[arg-type]
    bus.subscribe_global(global_handler)

    bus.start()
    try:
        bus.publish(Event("custom.event", data=123))
        wait_a_bit(0.2)

        stats = bus.get_stats()
        publish_count = stats["publish_event_count"]
        assert isinstance(publish_count, int) and publish_count >= 1
        assert called["sync"] == 1
        assert called["async"] == 1
        assert called["global"] == 1
    finally:
        bus.stop()


def test_timer_events_emitted() -> None:
    # 使用整数间隔以满足类型要求，但用短间隔测试
    bus = AsyncEventBus(name="test-timer", interval=1)
    ticks = {"count": 0}

    def on_timer(e: Event) -> None:
        if e.type == EventType.TIMER:
            ticks["count"] += 1

    bus.subscribe(EventType.TIMER, on_timer)
    bus.start()
    try:
        wait_a_bit(1.2)  # 等待至少1个tick
        assert ticks["count"] >= 1
    finally:
        bus.stop()


def test_monitors_receive_events_and_stats_snapshot() -> None:
    bus = AsyncEventBus(name="test-monitor", interval=1, stats_snapshot_every_ticks=1)
    received_types: list[str] = []

    def monitor(e: Event) -> None:
        received_types.append(e.type)

    bus.add_monitor(monitor)
    bus.start()
    try:
        # 触发普通事件
        bus.publish(Event(EventType.LOG_MESSAGE, data="hello"))
        wait_a_bit(0.1)
        # 等待定时器与快照
        wait_a_bit(1.2)

        assert EventType.LOG_MESSAGE in received_types
        assert "bus.stats" in received_types
    finally:
        bus.stop()


def test_continue_on_error_true_does_not_block_other_handlers() -> None:
    bus = AsyncEventBus(name="test-err-true", interval=1, continue_on_error=True)
    called = {"ok": 0}

    def bad_handler(e: Event) -> None:
        raise ValueError("boom")

    def ok_handler(e: Event) -> None:
        called["ok"] += 1

    bus.subscribe("err.event", bad_handler)
    bus.subscribe("err.event", ok_handler)
    bus.start()
    try:
        bus.publish(Event("err.event"))
        wait_a_bit(0.2)
        assert called["ok"] == 1
        stats = bus.get_stats()
        event_stats = stats["event_type_stats"]
        assert isinstance(event_stats, dict)
        ev = event_stats["err.event"]
        assert isinstance(ev, dict)
        assert ev["processed"] == 1
        assert ev["failed"] == 1
    finally:
        bus.stop()


def test_continue_on_error_false_stops_following_handlers_in_batch() -> None:
    bus = AsyncEventBus(name="test-err-false", interval=1, continue_on_error=True)
    # 运行后再切换，以覆盖 set_continue_on_error
    bus.set_continue_on_error(False)

    called = {"ok": 0}

    def bad_handler(e: Event) -> None:
        raise RuntimeError("bad")

    def ok_handler(e: Event) -> None:
        called["ok"] += 1

    bus.subscribe("err2.event", bad_handler)
    bus.subscribe("err2.event", ok_handler)
    bus.start()
    try:
        bus.publish(Event("err2.event"))
        wait_a_bit(0.2)
        assert called["ok"] == 0
        stats = bus.get_stats()
        event_stats = stats["event_type_stats"]
        assert isinstance(event_stats, dict)
        ev = event_stats["err2.event"]
        assert isinstance(ev, dict)
        assert ev["processed"] == 1
        assert ev["failed"] == 1
    finally:
        bus.stop()


def test_publish_timeout_when_queue_not_consumed() -> None:
    # 将队列容量暂时缩小，确保容易触发超时
    old_size = AsyncEventBus.DEFAULT_QUEUE_SIZE
    AsyncEventBus.DEFAULT_QUEUE_SIZE = 1
    try:
        bus = AsyncEventBus(name="test-timeout", interval=3600, publish_timeout=0.05)
        bus.start()
        try:
            # 现在事件循环已经就绪
            loop = bus._loop
            assert loop is not None
            
            # 取消主消费任务，停止从队列取数据
            def cancel_consumer() -> None:
                if bus._main_task:
                    bus._main_task.cancel()
            
            loop.call_soon_threadsafe(cancel_consumer)
            wait_a_bit(0.1)  # 等待取消生效

            # 第一个事件可入队
            bus.publish(Event("block.event"))
            # 第二个事件由于容量已满，应在超时后被丢弃
            start = time.time()
            bus.publish(Event("block.event"))
            elapsed = time.time() - start
            stats = bus.get_stats()
            dropped_count = stats["dropped_count"]
            assert isinstance(dropped_count, int) and dropped_count >= 1
            assert elapsed >= 0.05  # 约等于 publish_timeout
        finally:
            bus.stop()
    finally:
        AsyncEventBus.DEFAULT_QUEUE_SIZE = old_size


if __name__ == '__main__':
    test_basic_publish_and_handle_sync_and_async_handlers()
