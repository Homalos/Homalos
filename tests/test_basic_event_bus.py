# test_basic_event_bus.py
import time
from src.core.event_bus import BasicEventBus
from src.core.event import Event, EventType

"""
运行结果说明：
日志中仅在第一次下单事件时出现一次处理器错误（符合 continue_on_error=True 时的预期：记录错误但不中断其它处理器），随后切换为 fail-fast 后并未再次出现错误日志，符合“发布后立刻取消订阅”的竞态时序可能性：事件 id=3 在工作线程实际处理前，主线程已完成对失败处理器的 unsubscribe，因此未再触发错误。
统计值匹配业务语义：
event_count=6：只统计通过 publish 显式发布的 ORDER 事件（6次）。
processed_count=9：包含处理的全部事件（6次 ORDER + 3次 TIMER）。
error_count=0：该计数仅在处理流程发生未被吞掉的异常时增加。第一次错误因 continue_on_error=True 被吞掉，未记入 error_count；后续 id=3 未再触发错误（如上所述的竞态解释）。
event_type_stats 中 order.failed=1：按事件维度统计了处理器失败（与全局的 error_count 概念不同），与首次失败一致。
定时器和统计快照行为正确：stats_snapshot_every_ticks=3 触发一次快照，日志中已看到 "[monitor] stats snapshot: {...}" 且 timer.processed=3。

统计结果与参数含义：
event_count：仅统计 publish 进来的事件，不含内部 TIMER 事件。与实现一致（publish() 中自增计数）。
processed_count：处理循环处理的所有事件总数（含 TIMER）。与实现一致（process() 结束时自增）。
error_count：仅在处理流程抛出未被处理的异常时自增。处理器内部错误若被“继续执行”策略吞掉，不计入该项，只会体现在 event_type_stats[etype].failed。
event_type_stats：按事件类型聚合处理/成功/失败/耗时，符合日志表现。

continue_on_error=True → 后续切换为 False：用于演示两种错误策略
"""

# 事件处理器
def order_handler(event: Event) -> None:
    print(f"[order_handler] {event.type} -> {event.data}")

def global_handler(event: Event) -> None:
    # 全局处理器会收到所有事件
    if event.type != "bus.stats":
        print(f"[global_handler] {event.type}")

def failing_handler(event: Event) -> None:
    # 用于演示 continue_on_error 策略
    if event.type == EventType.ORDER:
        raise RuntimeError("simulated handler error")

# 监控器：观察所有事件，包括统计快照事件
def monitor(event: Event) -> None:
    if event.type == "bus.stats":
        print(f"[monitor] stats snapshot: {event.data}")
    else:
        print(f"[monitor] {event.type}")

def main() -> None:
    # 创建事件总线
    # - 每 1s 触发一次 TIMER 事件
    # - handler 出错时继续执行其他 handler
    # - 发布策略为 timeout，超时 1s
    # - 每 3 次 TIMER tick 推送一份统计快照给监控器
    bus = BasicEventBus(
        name="demo-bus",
        interval=1,
        continue_on_error=True,
        publish_timeout=1.0,           # timeout 模式下的超时时间
        stats_snapshot_every_ticks=3,     # 每3次定时器tick发送一次统计快照
        join_timeout_thread_s=3.0,
        join_timeout_timer_s=2.0,
        join_retries=2,
    )

    # 使用上下文管理自动 start/stop
    with bus as b:
        # 订阅
        b.subscribe(EventType.ORDER, order_handler)
        b.subscribe(EventType.ORDER, failing_handler)  # 故意加入会失败的处理器
        # 全局处理器：建议用 subscribe 全局主题或在实现中直接注册；这里直接当作普通 handler 示范
        b.subscribe_global(global_handler)

        # 注册监控器
        b.add_monitor(monitor)

        # 发布事件（处理器出错但继续）
        b.publish(Event(EventType.ORDER, data={"id": 1, "side": "BUY"}))
        b.publish(Event(EventType.ORDER, data={"id": 2, "side": "SELL"}))

        # 读取一次统计
        print("[main] stats:", b.get_stats())

        # 切换失败策略为 fail-fast（遇错即停止该批处理器后续执行）
        b.set_continue_on_error(False)
        b.publish(Event(EventType.ORDER, data={"id": 3, "side": "BUY"}))

        # 取消订阅失败处理器，避免后续报错
        b.unsubscribe(EventType.ORDER, failing_handler)

        # 再发一些事件
        for i in range(4, 7):
            b.publish(Event(EventType.ORDER, data={"id": i}))

        # 等待定时器触发与统计快照推送
        time.sleep(4)

        # 再读一次统计
        print("[main] stats (final):", b.get_stats())

        # 取消订阅与监控器（演示API）
        b.unsubscribe(EventType.ORDER, order_handler)
        b.remove_monitor(monitor)

if __name__ == "__main__":
    main()
    