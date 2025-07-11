# -*- coding: utf-8 -*-
"""
服务注册中心功能混合测试脚本
"""
import threading
import time
from src.core.event_bus import EventBus
from src.core.service_registry import ServiceRegistry
from src.core.event import Event, EventType

# 事件捕获器
class EventCapture:
    def __init__(self):
        self.lock = threading.Lock()
        self.events = []
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

def print_services(registry):
    print("当前注册服务:")
    for name, info in registry.list_services().items():
        print(f"  - {name}: {info}")
    print()

def test_register_and_unregister(event_bus, registry, capture):
    print("[测试] 服务注册与注销")
    service_info = {"name": "TestService", "type": "tests", "capabilities": ["ping"]}
    event_bus.publish(Event(EventType.SERVICE_REGISTER, service_info))
    time.sleep(0.2)
    print_services(registry)
    assert "TestService" in registry.list_services()
    # 注销
    event_bus.publish(Event(EventType.SERVICE_UNREGISTER, {"name": "TestService"}))
    time.sleep(0.2)
    print_services(registry)
    assert "TestService" not in registry.list_services()
    print("  -> 通过\n")

def test_heartbeat(event_bus, registry, capture):
    print("[测试] 心跳检测")
    service_info = {"name": "HeartBeatService", "type": "hb", "capabilities": []}
    event_bus.publish(Event(EventType.SERVICE_REGISTER, service_info))
    time.sleep(0.2)
    # 发送心跳
    for _ in range(3):
        event_bus.publish(Event(EventType.SERVICE_HEART_BEAT, {"name": "HeartBeatService"}))
        time.sleep(0.1)
    print_services(registry)
    assert "HeartBeatService" in registry.list_services()
    print("  -> 通过\n")

def test_discovery(event_bus, registry, capture):
    print("[测试] 服务发现")
    # 注册多个服务
    for i in range(3):
        event_bus.publish(Event(EventType.SERVICE_REGISTER, {"name": f"S{i}", "type": "t", "capabilities": []}))
    time.sleep(0.2)
    # 发送发现请求
    req = {"request_id": 123, "pattern": "S"}
    event_bus.publish(Event(EventType.SERVICE_DISCOVERY, req))
    time.sleep(0.2)
    responses = [e for e in capture.get() if e[0] == "ServiceDiscoveryResponse"]
    assert responses, "未收到发现响应"
    print("  -> 发现响应:", responses[-1][1])
    print("  -> 通过\n")

def test_heartbeat_timeout(event_bus, registry, capture):
    print("[测试] 心跳超时自动注销")
    # 缩短超时时间
    registry.running = False
    time.sleep(0.1)
    registry.running = True
    def short_checker():
        timeout = 2
        while registry.running:
            time.sleep(0.5)
            now = time.time_ns()
            for name, info in list(registry.services.items()):
                last = info.get("last_heartbeat", 0)
                if last < now - timeout * 1e9:
                    registry.services.pop(name, None)
                    event_bus.publish(Event("ServiceFailed", {"service": info, "reason": "heartbeat_timeout"}))
    registry.heartbeat_checker = threading.Thread(target=short_checker, daemon=True)
    registry.heartbeat_checker.start()
    # 注册服务但不发心跳
    event_bus.publish(Event(EventType.SERVICE_REGISTER, {"name": "TimeoutService", "type": "t", "capabilities": []}))
    time.sleep(3)
    print_services(registry)
    assert "TimeoutService" not in registry.list_services()
    failed = [e for e in capture.get() if e[0] == "ServiceFailed"]
    assert failed, "未捕获到超时失败事件"
    print("  -> 通过\n")

def test_concurrent_register(event_bus, registry, capture):
    print("[测试] 并发注册")
    def reg(i):
        event_bus.publish(Event(EventType.SERVICE_REGISTER, {"name": f"C{i}", "type": "t", "capabilities": []}))
    threads = [threading.Thread(target=reg, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    time.sleep(0.5)
    print_services(registry)
    assert len([n for n in registry.list_services() if n.startswith("C")]) == 10
    print("  -> 通过\n")

def test_error_handling(event_bus, registry, capture):
    print("[测试] 错误处理")
    # 缺失name字段
    try:
        event_bus.publish(Event(EventType.SERVICE_REGISTER, {"type": "t"}))
    except Exception as e:
        print("  -> 捕获到异常:", e)
    # 重复注册
    event_bus.publish(Event(EventType.SERVICE_REGISTER, {"name": "DupService", "type": "t", "capabilities": []}))
    event_bus.publish(Event(EventType.SERVICE_REGISTER, {"name": "DupService", "type": "t", "capabilities": []}))
    time.sleep(0.2)
    print_services(registry)
    print("  -> 通过\n")

def main():
    print("\n===== 服务注册中心功能混合测试 =====\n")
    event_bus = EventBus("TestBus")
    registry = ServiceRegistry(event_bus)
    capture = EventCapture()
    # 捕获所有事件
    event_bus.add_monitor(capture)
    registry.start()
    try:
        test_register_and_unregister(event_bus, registry, capture)
        test_heartbeat(event_bus, registry, capture)
        test_discovery(event_bus, registry, capture)
        test_heartbeat_timeout(event_bus, registry, capture)
        test_concurrent_register(event_bus, registry, capture)
        test_error_handling(event_bus, registry, capture)
        print("所有测试通过！\n")
    finally:
        registry.stop()
        event_bus.stop()

if __name__ == "__main__":
    main() 