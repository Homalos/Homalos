#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_service.py
@Date       : 2025/10/16
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略管理服务层，封装 StrategyManagerIPC 业务逻辑
"""
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from src.core.strategy_manager import StrategyManagerIPC
from src.utils.log import get_logger
from src.utils.get_path import get_path_ins


class StrategyService:
    """策略管理服务"""
    
    def __init__(self):
        self.logger = get_logger(__class__.__name__)
        self._manager: Optional[StrategyManagerIPC] = None
        self._initialized = False
    
    def get_manager(self) -> StrategyManagerIPC:
        """获取策略管理器实例"""
        if not self._initialized:
            raise RuntimeError("StrategyService not initialized. Call initialize_manager() first.")
        return self._manager
    
    async def initialize_manager(self, loop: asyncio.AbstractEventLoop):
        """
        初始化策略管理器
        
        Args:
            loop: asyncio事件循环
        """
        if self._initialized:
            self.logger.warning("StrategyManager already initialized")
            return
        
        try:
            # 构建 strategies.json 路径
            registry_path = get_path_ins.join_path("src", "strategy", "strategies.json")
            
            self.logger.info(f"初始化策略管理器，注册中心路径: {registry_path}")
            
            # 创建管理器实例
            self._manager = StrategyManagerIPC(
                strategies_pkg="src.strategy.strategies",
                registry_path=str(registry_path)
            )
            
            # 设置事件循环（用于 WebSocket 线程安全转发）
            self._manager.set_event_loop(loop)
            
            # 启动文件监控
            strategies_dir = get_path_ins.join_path("src", "strategy", "strategies")
            self._manager.start_watchdog(str(strategies_dir))
            
            # 自动加载已启用的策略
            enabled_strategies = self._manager.registry.list_enabled()
            self.logger.info(f"发现 {len(enabled_strategies)} 个已启用的策略")
            
            for sid, cfg in enabled_strategies.items():
                try:
                    self.logger.info(f"自动加载策略: {sid}")
                    self._manager.load_strategy(sid)
                except Exception as e:
                    self.logger.error(f"加载策略 {sid} 失败: {e}", exc_info=True)
            
            self._initialized = True
            self.logger.info("策略管理器初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化策略管理器失败: {e}", exc_info=True)
            raise
    
    async def shutdown(self):
        """关闭策略管理器"""
        if not self._initialized or not self._manager:
            return
        
        try:
            self.logger.info("关闭策略管理器...")
            
            # 停止文件监控
            self._manager.stop_watchdog()
            
            # 卸载所有策略
            for sid in list(self._manager._meta.keys()):
                try:
                    self.logger.info(f"卸载策略: {sid}")
                    self._manager.unload_strategy(sid)
                except Exception as e:
                    self.logger.error(f"卸载策略 {sid} 失败: {e}", exc_info=True)
            
            self._initialized = False
            self.logger.info("策略管理器已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭策略管理器失败: {e}", exc_info=True)
    
    def list_strategies(self) -> Dict[str, Any]:
        """列出所有策略"""
        manager = self.get_manager()
        return manager.registry.list_all()
    
    def start_strategy(self, sid: str):
        """启动策略"""
        manager = self.get_manager()
        
        if sid not in manager.registry.strategies:
            raise ValueError(f"策略 {sid} 不存在")
        
        manager.load_strategy(sid)
        self.logger.info(f"策略 {sid} 已启动")
    
    def stop_strategy(self, sid: str):
        """停止策略"""
        manager = self.get_manager()
        manager.unload_strategy(sid)
        self.logger.info(f"策略 {sid} 已停止")
    
    async def reload_strategy(self, sid: str):
        """重载策略（异步执行）"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        manager = self.get_manager()
        
        # 先检查是否正在reload
        if sid in manager._reloading:
            raise ValueError(f"策略 {sid} 正在重载中，请稍后再试")
        
        # 在线程池中执行reload操作，避免阻塞
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        
        try:
            await loop.run_in_executor(executor, manager.reload_strategy, sid)
            self.logger.info(f"策略 {sid} 重载完成")
        except Exception as e:
            self.logger.error(f"策略 {sid} 重载失败: {e}")
            raise
        finally:
            executor.shutdown(wait=False)
    
    def enable_strategy(self, sid: str):
        """启用策略"""
        manager = self.get_manager()
        manager.registry.strategies.setdefault(sid, {})
        manager.registry.strategies[sid]["enabled"] = True
        manager.registry.save()
        self.logger.info(f"策略 {sid} 已启用")
    
    def disable_strategy(self, sid: str):
        """禁用策略"""
        manager = self.get_manager()
        if sid in manager.registry.strategies:
            manager.registry.strategies[sid]["enabled"] = False
            manager.registry.save()
        self.logger.info(f"策略 {sid} 已禁用")
    
    def get_status(self) -> Dict[str, Any]:
        """获取所有策略运行状态"""
        manager = self.get_manager()
        meta = {}
        
        for sid, m in manager._meta.items():
            proc = m.get("proc")
            meta[sid] = {
                "pid": proc.pid if proc else None,
                "alive": proc.is_alive() if proc else False,
                "module": m.get("module"),
                "class": m.get("class")
            }
        
        return meta
    
    def register_ws_queue(self, q: asyncio.Queue):
        """注册 WebSocket 队列"""
        manager = self.get_manager()
        manager.register_ws_queue(q)
    
    def unregister_ws_queue(self, q: asyncio.Queue):
        """注销 WebSocket 队列"""
        manager = self.get_manager()
        manager.unregister_ws_queue(q)
    
    def get_reloading_strategies(self) -> list:
        """获取当前正在reload的策略列表"""
        return self.get_manager().get_reloading_strategies()
    
    def clear_reload_lock(self, sid: str) -> bool:
        """清除reload锁（用于恢复）"""
        return self.get_manager().clear_reload_lock(sid)


# 全局单例
strategy_service = StrategyService()

