#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_service.py
@Date       : 2025/10/16
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略管理服务层，封装 StrategyManager 业务逻辑
"""
import asyncio
from typing import Optional, Dict, Any

from src.core.strategy_manager import StrategyManager
from src.utils.log import get_logger
from src.utils.get_path import get_path_ins


class StrategyService:
    """策略管理服务"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._manager: Optional[StrategyManager] = None
        self._initialized = False
        self._trading_core = None  # TradingCoreService引用
    
    def set_trading_core(self, trading_core: 'TradingCoreService'):
        """设置交易核心服务"""
        self._trading_core = trading_core
        self.logger.info("交易核心服务已关联到策略服务")
    
    def register_position_listener(self):
        """
        在交易核心启动后注册持仓事件监听器
        
        这个方法应该在交易核心完全启动后调用
        """
        if not self._trading_core:
            self.logger.warning("交易核心未设置，无法注册持仓监听器")
            return
        
        event_bus = self._trading_core.get_event_bus()
        if not event_bus:
            self.logger.warning("交易核心的EventBus为None，无法注册持仓监听器")
            return
        
        # 检查数据库会话
        if not self._db:
            self.logger.warning("数据库会话未初始化，持仓事件将无法同步到数据库")
        
        from src.core.event import EventType
        event_bus.subscribe(
            EventType.POSITION,
            self._on_position_event,
            async_mode=True
        )
        event_bus.subscribe(
            EventType.TRADE_EXECUTION,
            self._on_trade_event,
            async_mode=True
        )
        self.logger.info("✓ 持仓事件监听器已注册到交易核心EventBus")
        self.logger.info("✓ 成交事件监听器已注册到交易核心EventBus")
    
    def update_core_dependencies(self):
        """
        更新交易核心依赖（在交易核心启动后调用）
        
        这用于处理以下场景：
        - 策略管理器在交易核心启动前初始化，使用了独立的EventBus
        - 交易核心启动后，需要切换到交易核心的EventBus
        """
        if not self._initialized or not self._manager:
            self.logger.warning("策略管理器未初始化，无法更新依赖")
            return
        
        if not self._trading_core:
            self.logger.warning("交易核心未设置，无法更新依赖")
            return
        
        try:
            # 获取交易核心的EventBus
            event_bus = self._trading_core.get_event_bus()
            if event_bus:
                self.logger.info("从交易核心获取EventBus，准备更新策略管理器")
                # 更新策略管理器的EventBus
                self._manager.update_event_bus(event_bus)
                self.logger.info("✓ 策略管理器已更新为使用交易核心的EventBus")
            else:
                self.logger.warning("交易核心的EventBus为None，无法更新")
        except Exception as e:
            self.logger.error(f"更新策略管理器依赖失败: {e}", exc_info=True)
    
    def get_manager(self) -> StrategyManager:
        """获取策略管理器实例"""
        if not self._initialized or self._manager is None:
            raise RuntimeError("StrategyService not initialized. Call initialize_manager() first.")
        return self._manager
    
    async def initialize_manager(self, loop: asyncio.AbstractEventLoop, db=None):
        """
        初始化策略管理器
        
        Args:
            loop: asyncio事件循环
            db: 数据库会话工厂（async_session_maker）或会话实例（用于持仓同步）
        """
        if self._initialized:
            self.logger.warning("StrategyManager already initialized")
            return
        
        try:
            # 保存数据库会话工厂（用于持仓事件监听）
            self._db = db
            if db:
                self.logger.info(f"数据库会话已设置: {type(db).__name__}")
            
            # 构建 strategy_registry.json 路径
            registry_path = get_path_ins.join_path("src", "strategy", "strategy_registry.json")
            
            self.logger.info(f"初始化策略管理器，注册中心路径: {registry_path}")
            
            # 从交易核心获取EventBus等依赖
            if self._trading_core:
                core_status = self._trading_core.get_status()
                if core_status['status'] == 'running':
                    # 核心运行中，使用核心的EventBus和模块
                    event_bus = self._trading_core.get_event_bus()
                    subscription_manager = self._trading_core.get_subscription_manager()
                    trade_signal_handler = self._trading_core.get_trade_signal_handler()
                    alarm_manager = self._trading_core.get_alarm_manager()
                    
                    self.logger.info("使用交易核心的EventBus和模块")
                else:
                    # 核心未运行，创建独立的EventBus（仅用于策略管理，无交易功能）
                    self.logger.warning("交易核心未运行，策略将无法接收行情和交易")
                    self.logger.info("创建独立EventBus（仅用于策略管理）")
                    
                    from src.core.event_bus import EventBus
                    event_bus = EventBus(
                        context="WebService_StrategyOnly",
                        general_max_workers=50,
                        market_max_workers=100,
                        register_signals=False,
                        auto_start=True
                    )
                    subscription_manager = None
                    trade_signal_handler = None
                    alarm_manager = None
            else:
                # 未设置交易核心，创建独立EventBus
                self.logger.warning("未设置交易核心服务")
                from src.core.event_bus import EventBus
                event_bus = EventBus(
                    context="WebService_Standalone",
                    general_max_workers=50,
                    market_max_workers=100,
                    register_signals=False,
                    auto_start=True
                )
                subscription_manager = None
                trade_signal_handler = None
                alarm_manager = None
            
            # 创建策略管理器实例
            self._manager = StrategyManager(
                event_bus=event_bus,
                strategies_pkg="src.strategy.strategies",
                registry_path=str(registry_path)
            )
            
            # 设置依赖（如果可用）
            if subscription_manager:
                self._manager.set_subscription_manager(subscription_manager)
                self.logger.info("已设置订阅管理器依赖")
            
            if trade_signal_handler:
                self._manager.set_trade_signal_handler(trade_signal_handler)
                self.logger.info("已设置交易信号处理器依赖")
            
            if alarm_manager:
                self._manager.alarm_manager = alarm_manager
                self.logger.info("已设置告警管理器依赖")
            
            # 设置事件循环（用于 WebSocket 线程安全转发）
            self._manager.set_event_loop(loop)
            
            # 启动状态加载和自动保存任务
            await self._manager.startup()
            
            # 注册持仓事件监听器（用于实时同步持仓到数据库）
            if self._manager.event_bus:
                from src.core.event import EventType
                self._manager.event_bus.subscribe(
                    EventType.POSITION,
                    self._on_position_event,
                    async_mode=True
                )
                self.logger.info("✓ 持仓事件监听器已注册")
            
            # 策略热重载功能已禁用（出于安全考虑）
            # strategies_dir = get_path_ins.join_path("src", "strategy", "strategies")
            # self._manager.start_watchdog(str(strategies_dir))
            
            self._initialized = True
            self.logger.info("策略管理器初始化完成")
            
            if not subscription_manager or not trade_signal_handler:
                self.logger.warning("⚠️ 策略管理器缺少交易依赖，启动策略前请先启动交易核心")
            
        except Exception as e:
            self.logger.error(f"初始化策略管理器失败: {e}", exc_info=True)
            raise
    
    async def shutdown(self):
        """关闭策略管理器"""
        if not self._initialized or not self._manager:
            return
        
        try:
            self.logger.info("关闭策略管理器...")
            
            # 调用管理器的shutdown（会保存状态并停止自动保存任务）
            await self._manager.shutdown()
            
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
    
    def update_core_dependencies(self):
        """
        更新策略管理器的核心依赖（在交易核心启动后调用）
        
        这个方法用于在交易核心启动后，将核心的EventBus、SubscriptionManager等
        依赖注入到策略管理器中，使策略能够订阅行情和发送交易信号。
        """
        if not self._manager or not self._trading_core:
            self.logger.warning("策略管理器或交易核心未初始化，无法更新依赖")
            return
        
        try:
            core_status = self._trading_core.get_status()
            if core_status['status'] != 'running':
                self.logger.warning("交易核心未运行，无法更新依赖")
                return
            
            # 获取核心依赖
            event_bus = self._trading_core.get_event_bus()
            subscription_manager = self._trading_core.get_subscription_manager()
            trade_signal_handler = self._trading_core.get_trade_signal_handler()
            alarm_manager = self._trading_core.get_alarm_manager()
            
            # 更新策略管理器的依赖
            self._manager.event_bus = event_bus
            self._manager._subscription_manager = subscription_manager
            self._manager._trade_signal_handler = trade_signal_handler
            self._manager.alarm_manager = alarm_manager
            
            # 为已运行的策略重新注册订阅
            running_strategies = self._manager.get_running_strategies()
            for sid in running_strategies:
                try:
                    # 获取策略的订阅信息
                    sub_info = self._manager._strategy_subscriptions.get(sid)
                    if sub_info:
                        instruments = list(sub_info.get('instruments', []))
                        intervals = list(sub_info.get('intervals', []))
                        
                        if instruments and subscription_manager:
                            # 重新注册订阅
                            subscription_manager.register_strategy_subscription(sid, instruments, intervals)
                            self.logger.info(f"已为策略 {sid} 重新注册订阅: {len(instruments)} 个合约")
                except Exception as e:
                    self.logger.error(f"为策略 {sid} 重新注册订阅失败: {e}", exc_info=True)
            
            self.logger.info("✓ 策略管理器核心依赖已更新")
            
        except Exception as e:
            self.logger.error(f"更新核心依赖失败: {e}", exc_info=True)
    
    def list_strategies(self) -> Dict[str, Any]:
        """列出所有策略"""
        manager = self.get_manager()
        return manager.registry.list_all()
    
    def get_strategy_by_uuid(self, strategy_uuid: str) -> tuple[str, Dict[str, Any]] | None:
        """
        通过UUID获取策略配置
        
        Args:
            strategy_uuid: 策略UUID
            
        Returns:
            tuple[str, dict] | None: (策略ID, 策略配置) 或 None
        """
        manager = self.get_manager()
        return manager.registry.get_by_uuid(strategy_uuid)
    
    async def start_strategy(self, sid: str, db=None):
        """启动策略（异步）"""
        manager = self.get_manager()
        
        if sid not in manager.registry.strategies:
            raise ValueError(f"策略 {sid} 不存在")
        
        # 在独立线程中执行同步操作，避免阻塞FastAPI事件循环
        import asyncio
        await asyncio.to_thread(manager.load_strategy, sid)
        self.logger.info(f"策略 {sid} 已启动")
        
        # 注意：持仓同步现在通过事件驱动方式处理
        # 当交易网关推送持仓事件时，会自动同步到数据库
        # 无需在启动时手动同步
    
    async def stop_strategy(self, sid: str):
        """停止策略（异步）"""
        manager = self.get_manager()
        # 在独立线程中执行同步操作
        import asyncio
        await asyncio.to_thread(manager.unload_strategy, sid)
        self.logger.info(f"策略 {sid} 已停止")
    
    async def stop_all_strategies(self) -> int:
        """
        停止所有运行中的策略
        
        Returns:
            int: 停止的策略数量
        """
        manager = self.get_manager()
        running_strategies = manager.get_running_strategies()
        
        stopped_count = 0
        for sid in running_strategies:
            try:
                manager.unload_strategy(sid)
                self.logger.info(f"策略 {sid} 已停止（因交易核心停止）")
                stopped_count += 1
            except Exception as e:
                self.logger.error(f"停止策略 {sid} 失败: {e}")
        
        return stopped_count
    
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
    
    async def _sync_account_positions_to_strategy(self, sid: str, db):
        """将账户持仓同步到策略"""
        try:
            from sqlalchemy import select
            from src.web.models.strategy import Strategy
            from src.web.models.strategy_position import StrategyPosition
            
            # 1. 获取策略 ID
            result = await db.execute(
                select(Strategy).where(Strategy.module_path == sid)
            )
            strategy = result.scalar_one_or_none()
            if not strategy:
                self.logger.warning(f"策略 {sid} 不存在，无法同步持仓")
                return
            
            strategy_id = strategy.strategy_id
            self.logger.info(f"开始同步账户持仓到策略 {sid} (ID: {strategy_id})")
            
            # 2. 从交易核心获取账户持仓
            if not self._trading_core:
                self.logger.warning("交易核心未设置，无法获取账户持仓")
                return
            
            trader_gateway = self._trading_core.get_trader_gateway()
            if not trader_gateway:
                self.logger.warning("交易网关未初始化，无法获取账户持仓")
                return
            
            # 获取账户持仓（从 trader_gateway.positions 字典中获取）
            account_positions = list(trader_gateway.positions.values()) if hasattr(trader_gateway, 'positions') else []
            if not account_positions:
                self.logger.info(f"账户无持仓，策略 {sid} 同步完成")
                return
            
            self.logger.info(f"账户持仓数: {len(account_positions)}")
            
            # 3. 为每个持仓创建或更新 StrategyPosition 记录
            synced_count = 0
            for pos_data in account_positions:
                try:
                    # 检查持仓是否已存在
                    result = await db.execute(
                        select(StrategyPosition).where(
                            StrategyPosition.strategy_id == strategy_id,
                            StrategyPosition.symbol == pos_data.instrument_id,
                            StrategyPosition.direction == ('LONG' if pos_data.direction.value == '多' else 'SHORT'),
                            StrategyPosition.is_closed == False
                        )
                    )
                    existing_pos = result.scalar_one_or_none()
                    
                    if existing_pos:
                        # 更新现有持仓
                        existing_pos.volume = pos_data.volume
                        existing_pos.frozen = pos_data.frozen
                        existing_pos.avg_price = pos_data.price
                        existing_pos.last_price = pos_data.price
                        existing_pos.position_pnl = pos_data.pnl
                        self.logger.info(f"更新持仓: {pos_data.instrument_id} {pos_data.direction.value} {pos_data.volume}手")
                    else:
                        # 创建新持仓
                        new_pos = StrategyPosition(
                            strategy_id=strategy_id,
                            symbol=pos_data.instrument_id,
                            exchange=pos_data.exchange_id.value if pos_data.exchange_id else '',
                            direction='LONG' if pos_data.direction.value == '多' else 'SHORT',
                            volume=pos_data.volume,
                            frozen=pos_data.frozen,
                            avg_price=pos_data.price,
                            last_price=pos_data.price,
                            position_pnl=pos_data.pnl,
                            yd_volume=pos_data.yd_volume,
                            is_closed=False
                        )
                        db.add(new_pos)
                        self.logger.info(f"新增持仓: {pos_data.instrument_id} {pos_data.direction.value} {pos_data.volume}手")
                    
                    synced_count += 1
                
                except Exception as e:
                    self.logger.error(f"同步持仓失败 {pos_data.instrument_id}: {e}", exc_info=True)
            
            # 4. 保存到数据库
            await db.commit()
            self.logger.info(f"✅ 策略 {sid} 持仓同步完成，共同步 {synced_count} 个持仓")
        
        except Exception as e:
            await db.rollback()
            self.logger.error(f"同步账户持仓失败: {e}", exc_info=True)
            raise
    
    def scan_and_load_strategies(self) -> Dict[str, Any]:
        """
        扫描策略目录并加载全部策略到注册表
        
        Returns:
            dict: 扫描结果统计
            {
                "total_discovered": 总共发现的策略数,
                "newly_added": 新添加的策略数,
                "updated": 更新的策略数,
                "strategies": 所有策略列表
            }
        """
        from pathlib import Path
        from src.strategy.strategy_scanner import StrategyScanner
        
        try:
            # 初始化扫描器
            strategies_dir = Path.cwd() / "src" / "strategy" / "strategies"
            scanner = StrategyScanner(strategies_dir)
            
            # 扫描策略
            self.logger.info("开始扫描策略目录，加载全部策略...")
            discovered = scanner.scan_strategies()
            
            # 获取现有配置
            manager = self.get_manager()
            existing = manager.registry.strategies.copy()
            
            # 合并配置
            merged = scanner.merge_with_existing(discovered, existing)
            
            # 更新注册表
            manager.registry.strategies = merged
            manager.registry.save()
            
            # 统计结果
            newly_added = len([sid for sid in discovered if sid not in existing])
            updated = len([sid for sid in discovered if sid in existing])
            
            result = {
                "total_discovered": len(discovered),
                "newly_added": newly_added,
                "updated": updated,
                "strategies": list(discovered.keys())
            }
            
            self.logger.info(
                f"策略扫描完成: 发现 {result['total_discovered']} 个策略, "
                f"新增 {result['newly_added']} 个, 更新 {result['updated']} 个"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"扫描策略失败: {e}", exc_info=True)
            raise
    
    def get_available_strategy_files(self) -> Dict[str, Any]:
        """
        获取所有可用的策略文件列表
        
        Returns:
            dict: {
                "success": true,
                "files": [
                    {
                        "filename": "strategy1.py",
                        "strategy_id": "src.strategy.strategies.strategy1.Strategy1",
                        "strategy_name": "策略名称",
                        "class_name": "类名",
                        "loaded": true,
                        "enabled": true
                    },
                    ...
                ]
            }
        """
        from pathlib import Path
        from src.strategy.strategy_scanner import StrategyScanner
        
        try:
            strategies_dir = Path.cwd() / "src" / "strategy" / "strategies"
            scanner = StrategyScanner(strategies_dir)
            manager = self.get_manager()
            existing_strategies = manager.registry.strategies
            
            files = []
            
            # 遍历所有.py文件
            for py_file in strategies_dir.glob("*.py"):
                if py_file.name.startswith("_") or py_file.name.startswith("."):
                    continue
                
                try:
                    # 扫描文件获取策略信息
                    strategy_info = scanner._scan_file(py_file)
                    
                    if strategy_info:
                        strategy_id = strategy_info["strategy_id"]
                        is_loaded = strategy_id in existing_strategies
                        
                        files.append({
                            "filename": py_file.name,
                            "strategy_id": strategy_id,
                            "strategy_name": strategy_info["name"],
                            "class_name": strategy_info["class"],
                            "loaded": is_loaded,
                            "enabled": existing_strategies[strategy_id].get("enabled") if is_loaded else None
                        })
                except Exception as e:
                    self.logger.warning(f"扫描文件 {py_file.name} 失败: {e}")
                    continue
            
            return {
                "success": True,
                "files": files
            }
        
        except Exception as e:
            self.logger.error(f"获取策略文件列表失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "files": []
            }
    
    def scan_single_strategy(self, filename: str) -> Dict[str, Any]:
        """
        扫描并加载单个策略文件
        
        Args:
            filename: 策略文件名，如 "strategy2.py"
        
        Returns:
            dict: {
                "success": true,
                "message": "策略加载成功",
                "strategy": {...}
            }
        """
        from pathlib import Path
        from src.strategy.strategy_scanner import StrategyScanner
        
        try:
            strategies_dir = Path.cwd() / "src" / "strategy" / "strategies"
            py_file = strategies_dir / filename
            
            # 检查文件是否存在
            if not py_file.exists():
                return {
                    "success": False,
                    "message": f"策略文件 {filename} 不存在"
                }
            
            # 扫描文件
            scanner = StrategyScanner(strategies_dir)
            strategy_info = scanner._scan_file(py_file)
            
            if not strategy_info:
                return {
                    "success": False,
                    "message": f"文件 {filename} 中未找到有效的策略类"
                }
            
            strategy_id = strategy_info["strategy_id"]
            manager = self.get_manager()
            
            # 检查策略是否已存在
            if strategy_id in manager.registry.strategies:
                # 已存在：更新元数据，保留enabled和params
                existing = manager.registry.strategies[strategy_id]
                manager.registry.strategies[strategy_id] = {
                    "file": strategy_info["file"],
                    "module": strategy_info["module"],
                    "class": strategy_info["class"],
                    "name": strategy_info["name"],
                    "description": strategy_info["description"],
                    "author": strategy_info["author"],
                    "instruments": strategy_info["instruments"],
                    "enabled": existing.get("enabled", True),  # 保留原值
                    "params": existing.get("params", {})
                }
                message = f"策略 {strategy_info['name']} 已更新"
            else:
                # 新策略：添加到注册表，enabled=true
                manager.registry.strategies[strategy_id] = {
                    "file": strategy_info["file"],
                    "module": strategy_info["module"],
                    "class": strategy_info["class"],
                    "name": strategy_info["name"],
                    "description": strategy_info["description"],
                    "author": strategy_info["author"],
                    "instruments": strategy_info["instruments"],
                    "enabled": True,  # 默认启用
                    "params": {}
                }
                message = f"策略 {strategy_info['name']} 已加载"
            
            # 保存注册表
            manager.registry.save()
            
            self.logger.info(message)
            
            return {
                "success": True,
                "message": message,
                "strategy": {
                    "strategy_id": strategy_id,
                    "name": strategy_info["name"],
                    "filename": filename
                }
            }
        
        except Exception as e:
            self.logger.error(f"加载策略文件 {filename} 失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"加载失败: {str(e)}"
            }
    
    def get_status(self) -> Dict[str, Any]:
        """获取所有策略运行状态"""
        manager = self.get_manager()
        meta = {}
        
        for sid, m in manager._meta.items():
            proc = m.get("proc")
            
            # 生成策略显示名称（基于类名或策略ID）
            class_name = m.get("class") or ""
            strategy_name = class_name.replace("Strategy", "").replace("_", " ").strip()
            if not strategy_name:
                strategy_name = sid.replace("_", " ").title()
            
            meta[sid] = {
                "pid": proc.pid if proc else None,
                "alive": proc.is_alive() if proc else False,
                "module": m.get("module") or "",  # 确保不返回None
                "class": m.get("class") or "",      # 确保不返回None
                "strategy_name": strategy_name,
                "start_time": m.get("start_time"),  # 启动时间
                "pnl": self._get_mock_pnl(sid),     # 模拟浮动盈亏
                "trade_count": self._get_mock_trade_count(sid)  # 模拟交易次数
            }
        
        return meta
    
    def _get_mock_pnl(self, sid: str) -> float:
        """获取模拟浮动盈亏（临时硬编码）"""
        # 基于策略ID生成模拟数据
        import hashlib
        hash_val = int(hashlib.md5(sid.encode()).hexdigest()[:8], 16)
        
        # 生成-10000到10000之间的随机盈亏
        pnl = (hash_val % 20001) - 10000
        return round(pnl * 0.1, 2)  # 缩小到合理范围
    
    def _get_mock_trade_count(self, sid: str) -> int:
        """获取模拟交易次数（临时硬编码）"""
        # 基于策略ID生成模拟数据
        import hashlib
        hash_val = int(hashlib.md5((sid + "_trades").encode()).hexdigest()[:8], 16)
        
        # 生成0到100之间的交易次数
        return hash_val % 101
    
    def unload_strategy(self, sid: str):
        """卸载策略（停止运行并从管理器中移除）"""
        manager = self.get_manager()
        
        # 检查策略是否存在于注册表中
        if sid not in manager.registry.strategies:
            raise ValueError(f"策略 {sid} 不存在")
        
        # 如果策略正在运行，先停止它
        if sid in manager._meta:
            manager.unload_strategy(sid)
            self.logger.info(f"运行中的策略 {sid} 已停止并卸载")
        else:
            # 策略已停止，只需要从注册表中移除
            self.logger.info(f"策略 {sid} 已停止，直接从注册表中卸载")
        
        # 从注册表中移除策略配置
        del manager.registry.strategies[sid]
        manager.registry.save()
        self.logger.info(f"策略 {sid} 已从注册表中移除")
    
    def register_ws_queue(self, q: asyncio.Queue):
        """注册 WebSocket 队列"""
        manager = self.get_manager()
        manager.register_ws_queue(q)
    
    def unregister_ws_queue(self, q: asyncio.Queue):
        """注销 WebSocket 队列"""
        manager = self.get_manager()
        manager.unregister_ws_queue(q)
    
    # 以下方法已删除（与热重载功能相关）：
    # - get_reloading_strategies()
    # - clear_reload_lock(sid)
    
    # ========== 状态持久化相关方法 ==========
    
    async def save_strategy_state(self, sid: str) -> bool:
        """
        手动保存单个策略的状态
        
        Args:
            sid: 策略ID
            
        Returns:
            bool: 是否保存成功
        """
        import asyncio
        
        manager = self.get_manager()
        
        # 获取策略当前状态
        with manager._lock:
            meta = manager._meta.get(sid)
            if not meta:
                raise ValueError(f"策略 {sid} 未加载")
            
            conn = meta.get("conn")
            proc = meta.get("proc")
            
            if not proc or not proc.is_alive() or not conn:
                self.logger.warning(f"策略 {sid} 未运行或连接无效，无法保存状态")
                return False
            
            # 清除旧缓存
            meta["last_state"] = None
            
            # 请求策略保存状态
            try:
                conn.send({"type": "command", "command": "save_state"})
            except Exception as e:
                self.logger.error(f"发送save_state命令失败: {e}")
                return False
        
        # 等待状态返回
        import time
        state = None
        start = time.time()
        while time.time() - start < 2.0:
            await asyncio.sleep(0.05)
            with manager._lock:
                cached = meta.get("last_state")
                if cached is not None:
                    state = cached
                    meta["last_state"] = None
                    break
        
        if state is None:
            self.logger.warning(f"策略 {sid} 没有返回状态")
            return False
        
        # 保存到文件
        success = await manager.state_persistence.save_strategy_state(sid, state)
        if success:
            self.logger.info(f"已手动保存策略 {sid} 的状态")
        return success
    
    async def load_strategy_state(self, sid: str, timestamp: Optional[str] = None) -> Optional[dict]:
        """
        加载策略状态
        
        Args:
            sid: 策略ID
            timestamp: 可选，指定时间戳（格式：20251016_143000）
            
        Returns:
            dict: 策略状态，如果不存在返回None
        """
        manager = self.get_manager()
        state = await manager.state_persistence.load_strategy_state(sid, timestamp or "")
        return state
    
    async def get_state_history(self, sid: str, limit: int = 10) -> list:
        """
        获取策略的状态历史列表
        
        Args:
            sid: 策略ID
            limit: 返回最近N条
            
        Returns:
            list: 历史记录列表
        """
        manager = self.get_manager()
        history = await manager.state_persistence.get_state_history(sid, limit)
        return history
    
    async def cleanup_old_states(self, days: int = 30) -> dict:
        """
        清理超过N天的旧状态
        
        Args:
            days: 保留最近N天
            
        Returns:
            dict: 清理结果
        """
        manager = self.get_manager()
        await manager.state_persistence.cleanup_old_states(days)
        return {"status": "cleaned", "days": days}
    
    def get_storage_info(self) -> dict:
        """获取状态存储信息统计"""
        manager = self.get_manager()
        return manager.state_persistence.get_storage_info()
    
    def get_strategy_logs(self, sid: str, limit: int = 100, trace_id: str = None, context: str = None) -> dict:
        """
        获取策略的日志，支持按 trace_id 和 context 过滤
        
        注意：只返回当前策略相关的日志，不返回其他模块的日志
        
        Args:
            sid: 策略ID
            limit: 返回的最大日志条数（仅在没有 trace_id 过滤时使用）
            trace_id: 可选，按 trace_id 过滤日志（精确追踪）
            context: 可选，按 context 标签过滤日志（通常为策略相关的 context）
            
        Returns:
            dict: 包含日志列表和统计信息
        """
        try:
            from datetime import datetime
            from pathlib import Path
            
            manager = self.get_manager()
            
            # 从策略管理器获取策略的日志缓冲区
            # 如果策略正在运行，获取其进程的日志
            if sid in manager.registry.strategies:
                strategy_config = manager.registry.strategies[sid]
                
                # 构建日志文件路径：logs/strategy_YYYYMMDD.log
                logs_dir = get_path_ins.get_logs_dir()
                log_file_path = logs_dir / f"strategy_{datetime.now().strftime('%Y%m%d')}.log"
                
                logs = []
                trace_ids = set()  # 收集所有 trace_id
                contexts = set()   # 收集所有 context
                
                try:
                    if log_file_path.exists():
                        with open(log_file_path, 'r', encoding='utf-8') as f:
                            # 读取所有行用于过滤
                            all_lines = f.readlines()
                            
                            for line in all_lines:
                                line = line.strip()
                                if not line:
                                    continue
                                
                                # 解析日志行，提取 trace_id 和 context
                                parsed = self._parse_log_line(line)
                                
                                # 只收集有 trace_id 或 context 的日志（即策略相关的日志）
                                # 这样可以过滤掉其他模块的日志
                                if not (parsed.get('trace_id') or parsed.get('context')):
                                    continue
                                
                                # 收集所有 trace_id 和 context
                                if parsed.get('trace_id'):
                                    trace_ids.add(parsed['trace_id'])
                                if parsed.get('context'):
                                    contexts.add(parsed['context'])
                                
                                # 应用过滤条件
                                if trace_id and parsed.get('trace_id') != trace_id:
                                    continue
                                if context and parsed.get('context') != context:
                                    continue
                                
                                logs.append(parsed)
                            
                            # 如果指定了 trace_id，返回所有匹配的日志（完整链路）
                            # 否则只保留最后 limit 条
                            if not trace_id:
                                logs = logs[-limit:] if len(logs) > limit else logs
                    else:
                        self.logger.debug(f"日志文件不存在: {log_file_path}")
                        logs = []
                    
                except Exception as e:
                    self.logger.warning(f"读取日志文件失败 {log_file_path}: {str(e)}")
                    logs = []
                
                return {
                    "logs": logs,
                    "count": len(logs),
                    "available_trace_ids": sorted(list(trace_ids)),
                    "available_contexts": sorted(list(contexts)),
                    "filter": {
                        "trace_id": trace_id,
                        "context": context
                    }
                }
            else:
                self.logger.warning(f"策略 {sid} 不存在")
                return {"logs": [], "count": 0, "available_trace_ids": [], "available_contexts": [], "filter": {}}
                
        except Exception as e:
            self.logger.error(f"获取策略日志失败: {str(e)}", exc_info=True)
            return {"logs": [], "count": 0, "available_trace_ids": [], "available_contexts": [], "filter": {}}
    
    def _parse_log_line(self, line: str) -> dict:
        """
        解析日志行，提取时间戳、级别、trace_id、context 等信息
        日志格式: 2025-11-25 10:54:06.843 | INFO | [context] trace_id - module:line - 消息
        
        Args:
            line: 日志行
            
        Returns:
            dict: 解析后的日志信息
        """
        result = {
            "message": line,
            "timestamp": None,
            "level": None,
            "context": None,
            "trace_id": None,
            "module": None,
            "content": None
        }
        
        try:
            # 尝试解析日志格式
            parts = line.split(' | ')
            
            if len(parts) >= 3:
                # 提取时间戳
                result["timestamp"] = parts[0].strip()
                
                # 提取日志级别
                result["level"] = parts[1].strip()
                
                # 提取 context 和 trace_id
                rest = ' | '.join(parts[2:])
                
                # 从 [context] 中提取 context
                import re
                context_match = re.search(r'\[([^\]]+)\]', rest)
                if context_match:
                    result["context"] = context_match.group(1)
                
                # 从日志中提取 trace_id（通常在 context 后面）
                # 格式: [context] trace_id - module:line - message
                trace_match = re.search(r'\[([^\]]+)\]\s+([a-f0-9\-]+)\s+', rest)
                if trace_match:
                    result["trace_id"] = trace_match.group(2)
                
                # 提取模块信息
                module_match = re.search(r'-\s+([^:]+):(\d+)\s+-', rest)
                if module_match:
                    result["module"] = f"{module_match.group(1)}:{module_match.group(2)}"
                
                # 提取消息内容
                content_match = re.search(r'-\s+(.+)$', rest)
                if content_match:
                    result["content"] = content_match.group(1)
                else:
                    result["content"] = rest
                    
        except Exception as e:
            self.logger.error(f"解析日志行失败: {e}")
        
        return result
    
    async def _on_position_event(self, event):
        """
        持仓事件处理器
        
        当交易网关推送持仓事件时，自动同步到数据库
        """
        if not self._db:
            self.logger.debug("数据库会话工厂未初始化，跳过持仓同步")
            return
        
        # 从事件 payload 中提取 PositionData 对象
        payload = event.payload
        if not payload:
            return
        
        # payload 格式: {"code": ..., "message": ..., "data": PositionData}
        position_data = payload.get("data") if isinstance(payload, dict) else payload
        if not position_data:
            return
        
        # 创建数据库会话
        db = None
        try:
            # 如果 _db 是可调用的（async_session_maker），则创建会话
            if callable(self._db):
                db = self._db()
            else:
                # 否则直接使用（AsyncSession 实例）
                db = self._db
            
            from sqlalchemy import select
            from src.web.models.strategy_position import StrategyPosition
            from src.web.models.strategy import Strategy
            
            # 获取所有策略（不仅是运行中的）
            # 因为持仓是账户级别的，应该同步到所有策略
            manager = self.get_manager()
            all_strategies = list(manager.registry.strategies.keys())
            
            if not all_strategies:
                self.logger.debug("[持仓事件] 没有可用的策略")
                return
            
            self.logger.info(f"[持仓事件] 收到持仓更新: {position_data.instrument_id} {position_data.direction.value} {position_data.volume}手，将同步到 {len(all_strategies)} 个策略")
            
            # 为每个策略同步持仓
            for sid in all_strategies:
                try:
                    # 获取策略 ID
                    result = await db.execute(
                        select(Strategy).where(Strategy.module_path == sid)
                    )
                    strategy = result.scalar_one_or_none()
                    if not strategy:
                        continue
                    
                    strategy_id = strategy.strategy_id
                    
                    # 检查持仓是否已存在
                    result = await db.execute(
                        select(StrategyPosition).where(
                            StrategyPosition.strategy_id == strategy_id,
                            StrategyPosition.symbol == position_data.instrument_id,
                            StrategyPosition.direction == ('LONG' if position_data.direction.value == '多' else 'SHORT'),
                            StrategyPosition.is_closed == False
                        )
                    )
                    existing_pos = result.scalar_one_or_none()
                    
                    if existing_pos:
                        # 更新现有持仓
                        existing_pos.volume = position_data.volume
                        existing_pos.frozen = position_data.frozen
                        existing_pos.avg_price = position_data.price
                        existing_pos.last_price = position_data.price
                        existing_pos.position_pnl = position_data.pnl
                    else:
                        # 创建新持仓
                        new_pos = StrategyPosition(
                            strategy_id=strategy_id,
                            symbol=position_data.instrument_id,
                            exchange=position_data.exchange_id.value if position_data.exchange_id else '',
                            direction='LONG' if position_data.direction.value == '多' else 'SHORT',
                            volume=position_data.volume,
                            frozen=position_data.frozen,
                            avg_price=position_data.price,
                            last_price=position_data.price,
                            position_pnl=position_data.pnl,
                            is_closed=False
                        )
                        db.add(new_pos)
                    
                except Exception as e:
                    self.logger.error(f"同步持仓到策略 {sid} 失败: {e}", exc_info=True)
            
            # 提交数据库更改
            await db.commit()
            self.logger.info(f"[持仓事件] 持仓已同步到数据库: {position_data.instrument_id} {position_data.direction.value} {position_data.volume}手")
            
        except Exception as e:
            self.logger.error(f"处理持仓事件失败: {e}", exc_info=True)
            if db:
                try:
                    await db.rollback()
                except:
                    pass
        finally:
            # 关闭会话（如果是由 async_session_maker 创建的）
            if db and callable(self._db):
                try:
                    await db.close()
                except:
                    pass

    async def _on_trade_event(self, event):
        """
        成交事件处理器
        
        当交易网关推送成交事件时，自动创建成交记录到数据库
        """
        if not self._db:
            self.logger.debug("数据库会话工厂未初始化，跳过成交记录创建")
            return
        
        # 从事件 payload 中提取 TradeData 对象
        payload = event.payload
        if not payload:
            return
        
        # payload 格式: {"code": ..., "message": ..., "data": TradeData}
        trade_data = payload.get("data") if isinstance(payload, dict) else payload
        if not trade_data:
            return
        
        try:
            # 创建数据库会话
            async with self._db() as db:
                from src.web.services.strategy_position_service import StrategyPositionService
                from src.web.services.commission_loader import get_commission_loader
                position_service = StrategyPositionService()
                commission_loader = get_commission_loader()
                
                # 获取所有策略
                manager = self.get_manager()
                all_strategies = list(manager.registry.strategies.keys())
                
                if not all_strategies:
                    self.logger.debug("[成交事件] 没有可用的策略")
                    return
                
                self.logger.info(f"[成交事件] 收到成交更新: {trade_data.instrument_id} {trade_data.direction.value} {trade_data.offset.value} {trade_data.volume}手 @ {trade_data.price}")
                
                # 确定开平类型
                offset_type = 'OPEN' if trade_data.offset.value == '开' else 'CLOSE'
                
                # 计算手续费
                commission = commission_loader.get_commission(
                    symbol=trade_data.instrument_id,
                    volume=trade_data.volume,
                    price=trade_data.price,
                    offset_type=offset_type
                )
                
                # 为每个策略创建成交记录
                for sid in all_strategies:
                    try:
                        # 获取策略 ID
                        from sqlalchemy import select
                        from src.web.models.strategy import Strategy
                        
                        query = select(Strategy).where(Strategy.module_path == sid)
                        result = await db.execute(query)
                        strategy = result.scalar_one_or_none()
                        
                        if not strategy:
                            self.logger.debug(f"[成交事件] 策略 {sid} 未在数据库中找到")
                            continue
                        
                        strategy_id = strategy.strategy_id
                        
                        # 创建成交记录
                        await position_service.create_trade(
                            db=db,
                            strategy_id=strategy_id,
                            symbol=trade_data.instrument_id,
                            exchange=trade_data.exchange_id.value if trade_data.exchange_id else '',
                            direction='LONG' if trade_data.direction.value == '多' else 'SHORT',
                            offset_type=offset_type,
                            trade_price=trade_data.price,
                            trade_volume=trade_data.volume,
                            commission=commission,
                            order_id=trade_data.order_id,
                            pnl=0.0,  # 成交时盈亏为0，平仓时才有盈亏
                            trade_time=trade_data.timestamp
                        )
                        
                        self.logger.info(f"[成交事件] 成交记录已创建: 策略 {sid} {trade_data.instrument_id} {trade_data.direction.value} {offset_type} {trade_data.volume}手 手续费: {commission}")
                    
                    except Exception as e:
                        self.logger.error(f"为策略 {sid} 创建成交记录失败: {e}", exc_info=True)
                
                # 提交数据库更改
                await db.commit()
        
        except Exception as e:
            self.logger.error(f"[成交事件] 处理成交事件失败: {e}", exc_info=True)
            try:
                await db.rollback()
            except:
                pass


# 全局单例
strategy_service = StrategyService()
