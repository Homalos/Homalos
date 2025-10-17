#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : system_coordinator.py
@Date       : 2025/10/17 17:00
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统集成协调器 - 管理各模块启动顺序、依赖关系和数据流协调
"""
import asyncio
import time
from threading import Lock
from typing import Optional, Any

from src.core.constants import ModuleStatus
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.object import ModuleInfo
from src.utils.log.logger import get_logger


class SystemCoordinator:
    """
    系统集成协调器
    
    功能：
    - 管理各模块的启动顺序和依赖关系
    - 协调系统初始化流程
    - 处理模块间的通信和数据流
    - 监控系统健康状态
    - 错误处理和恢复机制
    """
    
    def __init__(self, event_bus: EventBus):
        self.logger = get_logger(self.__class__.__name__)
        self.event_bus = event_bus
        
        # 模块管理
        self.modules: dict[str, ModuleInfo] = {}
        self.startup_sequence: list[str] = []
        self.shutdown_sequence: list[str] = []
        
        # 状态管理
        self.system_status = ModuleStatus.PENDING
        self.startup_complete = False
        self.shutdown_initiated = False
        
        # 同步锁
        self._lock = Lock()
        
        # 健康检查配置
        self.health_check_interval = 30  # 30秒检查一次
        self.health_check_task: Optional[asyncio.Task] = None
        
        # 数据流协调配置
        self.data_flow_initialized = False
        self.gateways_ready = {"market": False, "trader": False}
        
        self.logger.info("系统协调器初始化完成")
    
    def register_module(
            self,
            name: str,
            instance: Any,
            dependencies=None,
            startup_order: int = 0
    ) -> None:
        """
        注册模块
        
        Args:
            name: 模块名称
            instance: 模块实例
            dependencies: 依赖的模块列表
            startup_order: 启动优先级（数字越小优先级越高）
        """
        if dependencies is None:
            dependencies = []
        with self._lock:
            module_info = ModuleInfo(
                name=name,
                instance=instance,
                dependencies=dependencies or [],
                startup_order=startup_order
            )
            self.modules[name] = module_info
            
            # 重新计算启动顺序
            self._calculate_startup_sequence()
            
        self.logger.info(f"已注册模块: {name}, 依赖: {dependencies or 'None'}, 启动顺序: {startup_order}")
    
    def _calculate_startup_sequence(self) -> None:
        """
        计算模块启动顺序（拓扑排序）

        Returns:

        """
        # 简化的拓扑排序实现
        in_degree = {name: 0 for name in self.modules.keys()}
        adj_list = {name: [] for name in self.modules.keys()}
        
        # 构建依赖图
        for name, module_info in self.modules.items():
            for dep in module_info.dependencies:
                if dep in self.modules:
                    adj_list[dep].append(name)
                    in_degree[name] += 1
        
        # 拓扑排序
        queue = [name for name, degree in in_degree.items() if degree == 0]
        sequence = []
        
        while queue:
            # 按启动优先级排序
            queue.sort(key=lambda x: self.modules[x].startup_order)
            
            current = queue.pop(0)
            sequence.append(current)
            
            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否有循环依赖
        if len(sequence) != len(self.modules):
            self.logger.error("检测到模块循环依赖")
            remaining = set(self.modules.keys()) - set(sequence)
            self.logger.error(f"无法启动的模块: {remaining}")
        
        self.startup_sequence = sequence
        self.shutdown_sequence = list(reversed(sequence))
        
        self.logger.info(f"模块启动顺序: {' -> '.join(self.startup_sequence)}")
    
    async def startup_system(self) -> None:
        """
        启动整个系统

        Returns:

        """
        self.logger.info("开始系统启动流程...")
        self.system_status = ModuleStatus.INITIALIZING
        
        try:
            # 1. 按依赖顺序启动各模块
            await self._startup_modules()
            
            # 2. 等待关键模块就绪
            await self._wait_for_critical_modules()
            
            # 3. 初始化数据流
            await self._initialize_data_flow()
            
            # 4. 启动健康检查
            self._start_health_monitoring()
            
            # 5. 标记系统就绪
            self.system_status = ModuleStatus.RUNNING
            self.startup_complete = True
            
            self.logger.info("系统启动完成")
            
            # 发布系统就绪事件
            self.event_bus.publish(Event(
                EventType.SYSTEM_ALARM,
                payload={
                    "alarm_type": "system_ready",
                    "severity": "info",
                    "message": "系统启动完成，所有模块运行正常",
                    "details": {"startup_time": time.time()}
                }
            ))
            
        except Exception as e:
            self.system_status = ModuleStatus.ERROR
            self.logger.error(f"系统启动失败: {e}", exc_info=True)
            
            # 发布启动失败事件
            self.event_bus.publish(Event(
                EventType.SYSTEM_ALARM,
                payload={
                    "alarm_type": "startup_failed",
                    "severity": "critical",
                    "message": f"系统启动失败: {str(e)}",
                    "details": {"error": str(e)}
                }
            ))
            raise
    
    async def _startup_modules(self) -> None:
        """
        按顺序启动各模块

        Returns:

        """
        for module_name in self.startup_sequence:
            module_info = self.modules[module_name]
            
            try:
                self.logger.info(f"启动模块: {module_name}")
                module_info.status = ModuleStatus.INITIALIZING
                
                # 检查依赖是否就绪
                await self._wait_for_dependencies(module_name)
                
                # 启动模块
                if hasattr(module_info.instance, 'startup'):
                    await module_info.instance.startup()
                elif hasattr(module_info.instance, 'start'):
                    if asyncio.iscoroutinefunction(module_info.instance.start):
                        await module_info.instance.start()
                    else:
                        module_info.instance.start()
                
                module_info.status = ModuleStatus.READY
                module_info.last_health_check = time.time()
                
                self.logger.info(f"模块 {module_name} 启动完成")
                
                # 短暂延迟，让模块稳定
                await asyncio.sleep(0.5)
                
            except Exception as e:
                module_info.status = ModuleStatus.ERROR
                module_info.error_message = str(e)
                self.logger.error(f"模块 {module_name} 启动失败: {e}", exc_info=True)
                raise
    
    async def _wait_for_dependencies(self, module_name: str) -> None:
        """
        等待模块依赖就绪

        Args:
            module_name:

        Returns:

        """
        module_info = self.modules[module_name]
        max_wait_time = 60  # 最大等待60秒
        check_interval = 1  # 每秒检查一次
        
        for dep_name in module_info.dependencies:
            if dep_name not in self.modules:
                raise RuntimeError(f"模块 {module_name} 依赖的模块 {dep_name} 未注册")
            
            waited_time = 0
            while waited_time < max_wait_time:
                dep_module = self.modules[dep_name]
                if dep_module.status in [ModuleStatus.READY, ModuleStatus.RUNNING]:
                    break
                
                await asyncio.sleep(check_interval)
                waited_time += check_interval
            else:
                raise RuntimeError(f"等待依赖模块 {dep_name} 超时")
        
        if module_info.dependencies:
            self.logger.info(f"模块 {module_name} 的所有依赖已就绪")
    
    async def _wait_for_critical_modules(self) -> None:
        """
        等待关键模块就绪

        Returns:

        """
        critical_modules = ["event_bus", "alarm_manager", "subscription_manager"]
        max_wait_time = 30
        
        for module_name in critical_modules:
            if module_name in self.modules:
                waited_time = 0
                while waited_time < max_wait_time:
                    module_info = self.modules[module_name]
                    if module_info.status == ModuleStatus.READY:
                        break
                    await asyncio.sleep(1)
                    waited_time += 1
                else:
                    raise RuntimeError(f"关键模块 {module_name} 未能及时就绪")
        
        self.logger.info("所有关键模块已就绪")
    
    async def _initialize_data_flow(self) -> None:
        """
        初始化数据流

        Returns:

        """
        self.logger.info("初始化数据流连接...")
        
        # 1. 订阅网关状态事件
        self.event_bus.subscribe(EventType.MD_GATEWAY_LOGIN, self._handle_market_gateway_ready)
        self.event_bus.subscribe(EventType.TD_GATEWAY_READY, self._handle_trader_gateway_ready)
        # 兼容TD_CONFIRM_SUCCESS事件（结算单确认后交易网关就绪）
        self.event_bus.subscribe(EventType.TD_CONFIRM_SUCCESS, self._handle_trader_gateway_ready)
        
        # 2. 订阅策略管理相关事件
        self.event_bus.subscribe(EventType.STRATEGY_LOADED, self._handle_strategy_loaded)
        self.event_bus.subscribe(EventType.STRATEGY_TRADE_SIGNAL, self._handle_strategy_signal)
        
        # 3. 设置行情数据分发
        self._setup_market_data_distribution()
        
        # 4. 设置交易信号处理链
        self._setup_trade_signal_chain()
        
        self.data_flow_initialized = True
        self.logger.info("数据流初始化完成")
    
    def _setup_market_data_distribution(self) -> None:
        """
        设置行情数据分发

        Returns:

        """
        # 订阅tick数据，分发给策略和K线合成器
        self.event_bus.subscribe(EventType.TICK, self._distribute_tick_data)
        
        # 订阅K线数据，分发给策略
        self.event_bus.subscribe(EventType.BAR, self._distribute_bar_data)
        
        self.logger.info("行情数据分发器已设置")
    
    def _setup_trade_signal_chain(self) -> None:
        """
        设置交易信号处理链

        Returns:

        """
        # 这些连接在各模块内部已经建立，这里只是确认
        signal_chain_events = [
            EventType.STRATEGY_TRADE_SIGNAL,  # 策略信号
            EventType.TRADE_SIGNAL,          # 发送给风控
            EventType.TRADE_ORDER_APPROVED,   # 风控通过
            EventType.ORDER_SUBMIT_REQUEST,   # 提交订单
            EventType.ORDER_STATUS_UPDATE,    # 订单状态更新
            EventType.TRADE_EXECUTION        # 成交回报
        ]
        
        self.logger.info(f"交易信号处理链已确认: {len(signal_chain_events)} 个事件类型")
    
    def _start_health_monitoring(self) -> None:
        """
        启动健康监控

        Returns:

        """
        if self.health_check_task:
            return
        
        loop = asyncio.get_event_loop()
        self.health_check_task = loop.create_task(self._health_check_loop())
        self.logger.info("健康监控已启动")
    
    async def _health_check_loop(self) -> None:
        """
        健康检查循环

        Returns:

        """
        while not self.shutdown_initiated:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                self.logger.info("健康检查任务被取消")
                break
            except Exception as e:
                self.logger.error(f"健康检查异常: {e}", exc_info=True)
    
    async def _perform_health_checks(self) -> None:
        """
        执行健康检查

        Returns:

        """
        unhealthy_modules = []
        
        with self._lock:
            for module_name, module_info in self.modules.items():
                try:
                    # 检查模块是否有健康检查方法
                    if hasattr(module_info.instance, 'health_check'):
                        is_healthy = await module_info.instance.health_check()
                        if not is_healthy:
                            unhealthy_modules.append(module_name)
                    
                    # 更新健康检查时间
                    module_info.last_health_check = time.time()
                    
                except Exception as e:
                    self.logger.warning(f"模块 {module_name} 健康检查失败: {e}")
                    unhealthy_modules.append(module_name)
        
        # 处理不健康的模块
        if unhealthy_modules:
            self.logger.warning(f"发现不健康的模块: {unhealthy_modules}")
            
            # 发送告警
            self.event_bus.publish(Event(
                EventType.SYSTEM_ALARM,
                payload={
                    "alarm_type": "module_unhealthy",
                    "severity": "warning",
                    "message": f"模块健康检查失败: {', '.join(unhealthy_modules)}",
                    "details": {"unhealthy_modules": unhealthy_modules}
                }
            ))
    
    async def shutdown_system(self) -> None:
        """
        关闭整个系统

        Returns:

        """
        self.logger.info("开始系统关闭流程...")
        self.shutdown_initiated = True
        self.system_status = ModuleStatus.STOPPING
        
        try:
            # 1. 停止健康检查
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # 2. 按逆序关闭模块
            for module_name in self.shutdown_sequence:
                if module_name not in self.modules:
                    continue
                
                module_info = self.modules[module_name]
                try:
                    self.logger.info(f"关闭模块: {module_name}")
                    
                    if hasattr(module_info.instance, 'shutdown'):
                        await module_info.instance.shutdown()
                    elif hasattr(module_info.instance, 'stop'):
                        if asyncio.iscoroutinefunction(module_info.instance.stop):
                            await module_info.instance.stop()
                        else:
                            module_info.instance.stop()
                    
                    module_info.status = ModuleStatus.STOPPED
                    self.logger.info(f"模块 {module_name} 已关闭")
                    
                except Exception as e:
                    self.logger.error(f"关闭模块 {module_name} 失败: {e}", exc_info=True)
            
            self.system_status = ModuleStatus.STOPPED
            self.logger.info("系统关闭完成")
            
        except Exception as e:
            self.logger.error(f"系统关闭异常: {e}", exc_info=True)
            raise
    
    # ===== 事件处理方法 =====
    
    def _handle_market_gateway_ready(self, event: Event) -> None:
        """
        处理行情网关就绪事件

        Args:
            event:

        Returns:

        """
        data = event.payload
        if isinstance(data, dict) and data.get("code") == 0:
            self.gateways_ready["market"] = True
            self.logger.info("行情网关已就绪")
            self._check_gateways_ready()
    
    def _handle_trader_gateway_ready(self, event: Event) -> None:
        """
        处理交易网关就绪事件

        Args:
            event:

        Returns:

        """
        data = event.payload
        if isinstance(data, dict) and data.get("code") == 0:
            self.gateways_ready["trader"] = True
            self.logger.info("交易网关已就绪")
            self._check_gateways_ready()
    
    def _check_gateways_ready(self) -> None:
        """
        检查网关是否都已就绪

        Returns:

        """
        if all(self.gateways_ready.values()):
            self.logger.info("所有网关已就绪，开始启动策略管理器")
            
            # 通知策略管理器可以开始加载策略
            self.event_bus.publish(Event(
                EventType.SYSTEM_ALARM,
                payload={
                    "alarm_type": "gateways_ready",
                    "severity": "info",
                    "message": "所有网关已就绪",
                    "details": self.gateways_ready
                }
            ))
    
    def _handle_strategy_loaded(self, event: Event) -> None:
        """
        处理策略加载事件

        Args:
            event:

        Returns:

        """
        self.logger.debug(f"策略已加载: {event.payload}")
    
    def _handle_strategy_signal(self, event: Event) -> None:
        """
        处理策略交易信号

        Args:
            event:

        Returns:

        """
        self.logger.debug(f"收到策略交易信号: {event.payload}")
    
    def _distribute_tick_data(self, event: Event) -> None:
        """分发tick数据"""
        # tick数据会自动分发给订阅者，这里只是监控
        pass
    
    def _distribute_bar_data(self, event: Event) -> None:
        """分发K线数据"""
        # K线数据会自动分发给订阅者，这里只是监控
        pass
    
    # ===== 状态查询方法 =====
    
    def get_system_status(self) -> dict[str, Any]:
        """
        获取系统状态

        Returns:

        """
        with self._lock:
            modules_status = {}
            for name, info in self.modules.items():
                modules_status[name] = {
                    "status": info.status.value,
                    "dependencies": info.dependencies,
                    "startup_order": info.startup_order,
                    "last_health_check": info.last_health_check,
                    "error_message": info.error_message
                }
        
        return {
            "system_status": self.system_status.value,
            "startup_complete": self.startup_complete,
            "shutdown_initiated": self.shutdown_initiated,
            "data_flow_initialized": self.data_flow_initialized,
            "gateways_ready": self.gateways_ready.copy(),
            "modules": modules_status,
            "startup_sequence": self.startup_sequence.copy(),
            "module_count": len(self.modules)
        }
    
    def is_system_ready(self) -> bool:
        """
        检查系统是否就绪

        Returns:

        """
        return (self.system_status == ModuleStatus.RUNNING and 
                self.startup_complete and 
                not self.shutdown_initiated)
    
    def get_module_status(self, module_name: str) -> Optional[ModuleStatus]:
        """
        获取指定模块状态

        Args:
            module_name:

        Returns:

        """
        module_info = self.modules.get(module_name)
        return module_info.status if module_info else None
