#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : service_registry
@Date       : 2025/7/5 21:09
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 服务注册中心
"""
from threading import Thread
from time import time_ns, sleep
from typing import Dict, Optional

from src.core.event import EventType
from src.core.event_bus import EventBus, Event
from src.core.logger import get_logger

logger = get_logger("ServiceRegistry")


class ServiceRegistry:
    """
    服务注册中心
    - 服务注册与发现
    - 健康检查（心跳检测）
    - 服务状态监控
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.services: Dict[str, dict] = {}  # service_name -> service_info
        self.heartbeat_checker = Thread(target=self._check_heartbeats, daemon=True)  # 心跳检测线程
        self.running = False

        # 注册事件处理器
        self.event_bus.subscribe(EventType.SERVICE_REGISTER, self.handle_register)
        self.event_bus.subscribe(EventType.SERVICE_UNREGISTER, self.handle_unregister)
        self.event_bus.subscribe(EventType.SERVICE_HEART_BEAT, self.handle_heartbeat)
        self.event_bus.subscribe(EventType.SERVICE_DISCOVERY, self.handle_discovery_request)

    def start(self):
        """启动服务注册中心"""
        self.running = True
        self.heartbeat_checker.start()
        logger.info("ServiceRegistry 已启动")

    def stop(self):
        """停止服务注册中心"""
        self.running = False
        self.heartbeat_checker.join(timeout=5)
        logger.info("ServiceRegistry 已停止")

    def handle_register(self, event: Event):
        """处理服务注册事件"""
        service_info = event.data
        service_name = service_info["name"]

        # 添加最后心跳时间
        service_info["last_heartbeat"] = time_ns()

        # 注册服务
        self.services[service_name] = service_info
        logger.info(f"已注册服务：{service_name}")

        # 广播服务更新事件(原来是ServiceUpdated)
        self.event_bus.publish(Event(EventType.SERVICE_UPDATED, {
            "action": "register",
            "service": service_info
        }))

    def handle_unregister(self, event: Event):
        """处理服务注销事件"""
        service_name = event.data["name"]

        if service_name in self.services:
            service_info = self.services.pop(service_name)
            logger.info(f"服务未注册：{service_name}")

            # 广播服务更新事件(原来是ServiceUpdated)
            self.event_bus.publish(Event(EventType.SERVICE_UPDATED, {
                "action": "unregister",
                "service": service_info
            }))

    def handle_heartbeat(self, event: Event):
        """处理心跳事件"""
        service_name = event.data["name"]

        if service_name in self.services:
            self.services[service_name]["last_heartbeat"] = time_ns()
            logger.debug(f"从 {service_name} 收到心跳")

    def handle_discovery_request(self, event: Event):
        """处理服务发现请求"""
        request = event.data
        response = {
            "request_id": request.get("request_id"),
            "services": {}
        }

        # 根据请求过滤服务
        if "pattern" in request:
            pattern = request["pattern"]
            for name, info in self.services.items():
                if pattern in name:
                    # 返回服务基本信息（不含敏感数据）
                    response["services"][name] = {
                        "name": info["name"],
                        "type": info["type"],
                        "status": info.get("status", "active"),
                        "capabilities": info.get("capabilities", [])
                    }
        else:
            for name, info in self.services.items():
                response["services"][name] = {
                    "name": info["name"],
                    "type": info["type"],
                    "status": info.get("status", "active"),
                    "capabilities": info.get("capabilities", [])
                }

        # 发送服务发现响应(原来是ServiceDiscoveryResponse)
        self.event_bus.publish(Event(EventType.SERVICE_DISCOVERY_RESPONSE, response))

    def _check_heartbeats(self):
        """定期检查服务心跳"""
        heartbeat_timeout = 10  # 10秒超时
        while self.running:
            sleep(5)  # 每5秒检查一次

            current_time = time_ns()
            threshold = current_time - heartbeat_timeout * 1e9

            for service_name, service_info in list(self.services.items()):
                last_heartbeat = service_info.get("last_heartbeat", 0)

                if last_heartbeat < threshold:
                    logger.warning(f"服务 {service_name} 心跳超时，正在取消注册")

                    # 注销服务
                    self.services.pop(service_name, None)

                    # 广播服务失败事件(原来是ServiceFailed)
                    self.event_bus.publish(Event(EventType.SERVICE_FAILED, {
                        "service": service_info,
                        "reason": "heartbeat_timeout"
                    }))

    def get_service_info(self, service_name: str) -> Optional[dict]:
        """获取服务完整信息"""
        return self.services.get(service_name)

    def list_services(self) -> Dict[str, dict]:
        """列出所有注册服务"""
        return self.services.copy()
