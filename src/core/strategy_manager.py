#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_manager.py
@Date       : 2025/10/16 10:17
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略动态加载/卸载管理器，（进程隔离版，含 WS 支持）

主要负责：

- 动态加载策略模块，负责策略文件加载、热更新、启停、删除；
- 监控策略文件变化（watchdog）；
- 启动、销毁、重载策略进程；
- 通过 IPC 通信传递行情事件。
- 加载 (spawn)、卸载、重载、广播事件、读子进程消息并把它线程安全地投递给 WebSocket 连接（通过主事件循环）。

说明（简短）：
- `registry.strategies` 中每个策略 conf 至少要包含 `file`（文件路径），
`module`（导入路径，如 `src.strategy.example`，可与 file 相同）和
`class`（策略类名，默认 `Strategy`）；`params` 为实例化参数。
- `set_event_loop(loop)` 必须由 FastAPI app 在启动时调用（见下）。
"""
import asyncio
import multiprocessing as mp
import time
from pathlib import Path
from threading import Thread, Lock
from typing import Any, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.state_persistence import StatePersistenceManager
from src.core.strategy_worker import run_strategy_process  # child entry
from src.strategy.strategy_registry import StrategyRegistry
from src.system_config import Config
from src.utils.get_path import get_path_ins
from src.utils.log.logger import get_logger

# message delivered to WS clients will be JSON serializable dict:
# {"sid":"...", "type":"log"/"order"/"error"/"status", "payload": ...}

_DEBOUNCE = 2.0  # 增加到2秒，避免重复触发


class StrategyManagerIPC:
    """
    策略管理器IPC通信类，用于策略进程与策略管理器之间的通信
    """
    def __init__(self, event_bus: Optional[EventBus], strategies_pkg: str, registry_path: str, mp_ctx=None):
        self.logger = get_logger(self.__class__.__name__)
        self.event_bus = event_bus
        self.strategies_pkg = strategies_pkg  # module package prefix for dynamic import if needed
        self.registry = StrategyRegistry(registry_path)
        self.mp_ctx = mp_ctx or mp.get_context()  # allow injection for testing
        # meta: sid -> {proc, conn, module, class_name, file_path, last_state, cached_state}
        self._meta: dict[str, dict[str, Any]] = {}
        self._lock = Lock()
        self._reloading: set = set()  # 正在reload的策略ID集合
        self._expected_stops: set = set()  # 预期停止的策略ID集合，用于区分主动停止和意外崩溃

        # WebSocket integration:
        # we will store a set of asyncio.Queues (one per active websocket connection)
        self._ws_queues: list[asyncio.Queue] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # watchdog
        self._watch_observer: Optional[Any] = None  # Observer类型
        self._last_event_time: dict[str, float] = {}

        state_storage_dir = get_path_ins.get_data_dir() / Config.strategy_states_dir_name
        # 状态持久化管理器
        self.state_persistence = StatePersistenceManager(
            storage_dir=Path(state_storage_dir),
            max_history=288  # 24小时历史（5分钟间隔）
        )
        
        # 自动保存定时任务
        self._auto_save_task: Optional[asyncio.Task] = None
        
        # 状态缓存字典（用于在启动时临时存储持久化状态）
        self._cached_states: dict[str, dict] = {}
        
        # 告警管理器（延迟初始化，在startup中设置）
        self.alarm_manager: Optional[Any] = None
        
        # 策略订阅管理（新增）
        self._strategy_subscriptions: dict[str, dict[str, Any]] = {}  # 策略订阅信息
        self._subscription_manager: Optional[Any] = None  # 订阅管理器引用
        
        # 交易信号处理（新增）
        self._trade_signal_handler: Optional[Any] = None  # 交易信号处理器引用

    # ---------- 事件循环注册 ----------
    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """
        启动时从 FastAPI 应用程序调用一次以允许线程->循环回调。

        Args:
            loop:

        Returns:

        """
        self._loop = loop
    
    # ---------- 生命周期管理 ----------
    async def startup(self):
        """
        系统启动时调用
        - 加载所有策略的持久化状态
        - 启动自动保存定时任务
        - 设置事件订阅
        """
        self.logger.info("策略管理器启动中...")
        
        # 设置事件订阅（新增）
        if self.event_bus:
            # 订阅策略信号结果事件
            self.event_bus.subscribe(EventType.STRATEGY_SIGNAL_RESULT, self._handle_signal_result)
            self.logger.info("已订阅策略信号结果事件")
        
        # 加载所有已启用策略的持久化状态
        # 使用临时字典存储，避免影响load_strategy的判断
        self._cached_states = {}
        for sid in self.registry.list_enabled().keys():
            try:
                state = await self.state_persistence.load_strategy_state(sid)
                if state:
                    # 将状态缓存到临时字典，等待策略进程启动后注入
                    self._cached_states[sid] = state
                    self.logger.info(f"已加载 {sid} 的持久化状态")
            except Exception as e:
                self.logger.warning(f"加载 {sid} 状态失败: {e}")
        
        # 启动自动保存任务
        self._start_auto_save_task()
        
        self.logger.info("策略管理器启动完成")
    
    async def shutdown(self):
        """
        系统关闭时调用
        - 保存所有策略状态
        - 停止自动保存任务
        """
        self.logger.info("策略管理器关闭中...")
        
        # 停止自动保存任务
        if self._auto_save_task:
            self._auto_save_task.cancel()
            try:
                await self._auto_save_task
            except asyncio.CancelledError:
                pass
            self.logger.info("自动保存任务已停止")
        
        # 最后一次保存所有状态
        try:
            await self._save_all_current_states()
        except Exception as e:
            self.logger.error(f"关闭时保存状态失败: {e}")
        
        self.logger.info("策略管理器已关闭")
    
    def _start_auto_save_task(self):
        """启动自动保存任务"""
        if self._loop:
            self._auto_save_task = self._loop.create_task(self._auto_save_loop())
            self.logger.info("自动保存任务已启动（每5分钟）")
        else:
            self.logger.warning("事件循环未设置，无法启动自动保存任务")
    
    async def _auto_save_loop(self):
        """自动保存循环（每5分钟）"""
        while True:
            try:
                await asyncio.sleep(300)  # 5分钟
                await self._save_all_current_states()
            except asyncio.CancelledError:
                self.logger.info("自动保存任务被取消")
                break
            except Exception as e:
                self.logger.error(f"自动保存失败: {e}", exc_info=True)
    
    async def _save_all_current_states(self):
        """保存所有当前运行策略的状态"""
        states_to_save = {}
        
        with self._lock:
            for sid, meta in self._meta.items():
                conn = meta.get("conn")
                proc = meta.get("proc")
                
                if proc and proc.is_alive():
                    try:
                        # 清除旧缓存
                        meta["last_state"] = None
                        
                        # 请求保存状态
                        conn.send({"type": "command", "command": "save_state"})
                        
                        # 等待响应（超时2秒）
                        start = time.time()
                        while time.time() - start < 2.0:
                            time.sleep(0.05)
                            cached = meta.get("last_state")
                            if cached is not None:
                                states_to_save[sid] = cached
                                meta["last_state"] = None  # 清除缓存
                                break
                    except Exception as e:
                        self.logger.warning(f"获取 {sid} 状态失败: {e}")
        
        # 批量保存到文件
        if states_to_save:
            results = await self.state_persistence.save_all_states(states_to_save)
            success_count = sum(1 for v in results.values() if v)
            self.logger.info(f"自动保存完成：成功 {success_count}/{len(states_to_save)}")
        else:
            self.logger.debug("没有需要保存的状态")

    # ---------- 流程生命周期 ----------
    def load_strategy(self, sid: str):
        """
        根据注册表中定义的策略 ID 启动子进程。
        registry[strategy_id] 预期字段：{'file': 'src.strategy.strategies.example',
        'module':'src.strategy.strategies.example', 'class':'Strategy', 'enabled':True, 'params':{}}
        """
        cfg = self.registry.strategies.get(sid)
        if not cfg:
            self.logger.error(f"no config for {sid}")
            return

        with self._lock:
            if sid in self._meta:
                self.logger.warning(f"{sid} already loaded")
                return

            # 准备连接
            parent_conn, child_conn = mp.Pipe(duplex=True)
            # 确定模块路径和类名
            module_path = cfg.get("module") or cfg.get("file")  # 更喜欢明确的模块键
            class_name = cfg.get("class", "Strategy")
            params = cfg.get("params", {})

            # spawn 进程
            proc = self.mp_ctx.Process(target=run_strategy_process, args=(sid, module_path, class_name, params, child_conn), daemon=True)
            proc.start()

            # 检查是否有缓存的持久化状态（从临时字典中获取）
            cached_state = getattr(self, '_cached_states', {}).get(sid)
            
            meta = {
                "proc": proc,
                "conn": parent_conn,
                "module": module_path,
                "class": class_name,
                "file": cfg.get("file"),
                "last_state": None,
                "start_time": time.time()  # 记录启动时间戳
            }
            self._meta[sid] = meta

            # 为该孩子启动读者线程
            t = Thread(target=self._reader_loop, args=(sid,), daemon=True)
            t.start()

            self.logger.info(f"Loaded {sid} (proc pid={proc.pid})")
            
            # 如果有缓存的持久化状态，注入到新启动的进程
            if cached_state:
                try:
                    # 给进程一点启动时间
                    time.sleep(0.1)
                    parent_conn.send({"type": "command", "command": "load_state", "state": cached_state})
                    self.logger.info(f"已注入持久化状态到 {sid}")
                    # 清除缓存（从临时字典中移除）
                    if hasattr(self, '_cached_states') and sid in self._cached_states:
                        del self._cached_states[sid]
                except Exception as e:
                    self.logger.warning(f"注入状态失败: {e}")

    def unload_strategy(self, sid: str):
        with self._lock:
            meta = self._meta.get(sid)
            if not meta:
                self.logger.warning(f"{sid} not loaded")
                return
            
            # 标记为预期停止，避免触发崩溃告警
            self._expected_stops.add(sid)

            conn = meta["conn"]
            proc = meta["proc"]

            # 请求保存状态
            try:
                conn.send({"type": "command", "command": "save_state"})
                # 即将从 conn 读取（非阻塞短暂等待）
                start = time.time()
                saved = None
                while time.time() - start < 1.0:
                    if conn.poll():
                        msg = conn.recv()
                        if isinstance(msg, dict) and msg.get("type") == "save_state_result":
                            saved = msg.get("payload")
                            break
                        else:
                            # 转发任何其他消息
                            self._forward_to_ws(msg)
                    time.sleep(0.01)
                meta["last_state"] = saved
            except Exception as e:
                self.logger.exception(f"save_state request failed: {e}")

            # 发送停止
            try:
                conn.send({"type": "command", "command": "stop"})
            except Exception as e:
                self.logger.exception(f"stop send failed: {e}")

            # 等待然后终止（如果需要）
            proc.join(timeout=1.0)
            if proc.is_alive():
                try:
                    proc.terminate()
                except Exception as e:
                    self.logger.exception(f"terminate failed: {e}")
            # 清理连接
            try:
                conn.close()
            except Exception:
                pass

            del self._meta[sid]
            # 清理预期停止标记（延迟清理，给_reader_loop时间处理）
            # 注意：不在这里立即清理，因为_reader_loop可能还在运行
            self.logger.info(f"Unloaded {sid}")

    def reload_strategy(self, sid: str):
        """
        保存状态、卸载、重新加载、恢复状态。
        """
        # 检查是否正在reload
        if sid in self._reloading:
            self.logger.warning(f"{sid} 已在重新加载，跳过重复重新加载")
            raise RuntimeError(f"{sid} 已在重新加载")
        
        # 标记为正在reload
        self._reloading.add(sid)
        self.logger.info(f"开始重载 {sid}")
        
        try:
            with self._lock:
                meta = self._meta.get(sid)
                saved = None
                if meta:
                    # 清除旧的缓存状态
                    meta["last_state"] = None
                    
                    try:
                        conn = meta["conn"]
                        proc = meta.get("proc")
                        
                        # 检查进程是否还活着
                        if proc and not proc.is_alive():
                            self.logger.warning(f"{sid} 进程已死亡，跳过 save_state")
                        else:
                            # 尝试保存状态 - 使用meta中缓存的last_state
                            # 注意：save_state消息会被_reader_loop接收并缓存到meta["last_state"]
                            conn.send({"type": "command", "command": "save_state"})
                            
                            # 等待_reader_loop接收并缓存状态
                            start = time.time()
                            while time.time() - start < 2.0:
                                # 检查meta中是否已有缓存的状态（由_reader_loop更新）
                                # 注意：_reader_loop在锁外更新meta，所以这里需要短暂等待
                                time.sleep(0.05)  # 先等一下，让_reader_loop有机会更新
                                cached_state = meta.get("last_state")
                                if cached_state is not None:
                                    saved = cached_state
                                    self.logger.info(f"成功获取 {sid} 的状态数据")
                                    break
                            
                            if saved is None:
                                self.logger.debug(f"{sid} 没有状态需要保存（这是正常的）")
                    except Exception as e:
                        self.logger.warning(f"重新加载时 save_state 失败：{e}")
                
                self.logger.info(f"save_state阶段完成，开始unload {sid}")
                
                # unload if loaded (内联逻辑，避免嵌套锁)
                if sid in self._meta:
                    # 标记为预期停止，避免在reload过程中触发崩溃告警
                    self._expected_stops.add(sid)
                    
                    meta = self._meta[sid]
                    conn = meta["conn"]
                    proc = meta["proc"]
                    
                    # 发送停止命令
                    self.logger.info(f"发送stop命令给 {sid}")
                    try:
                        conn.send({"type": "command", "command": "stop"})
                    except Exception as e:
                        self.logger.warning(f"stop send failed: {e}")
                    
                    # 等待进程退出
                    self.logger.info(f"等待 {sid} 进程退出")
                    try:
                        proc.join(timeout=1.0)
                        if proc.is_alive():
                            self.logger.info(f"{sid} 进程未响应，强制终止")
                            proc.terminate()
                            proc.join(timeout=0.5)
                        self.logger.info(f"{sid} 进程已停止")
                    except Exception as e:
                        self.logger.warning(f"process termination failed: {e}")
                    
                    # 清理连接
                    try:
                        conn.close()
                    except Exception:
                        pass
                    
                    # remove from meta
                    del self._meta[sid]
                    self.logger.info(f"Unloaded {sid}")

            time.sleep(0.1)
            
            # 再次加载
            self.load_strategy(sid)

            # 恢复状态
            if saved is not None and sid in self._meta:
                try:
                    new_conn = self._meta[sid]["conn"]
                    new_conn.send({"type": "command", "command": "load_state", "state": saved})
                except Exception as e:
                    self.logger.warning(f"load_state send failed: {e}")

            self.logger.info(f"Reloaded {sid}")
        except Exception as e:
            # 重载失败，触发告警
            self.logger.error(f"重载策略 {sid} 失败: {e}", exc_info=True)
            
            if self.alarm_manager and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self.alarm_manager.trigger_alarm(
                        alarm_type="reload_failed",
                        severity="error",
                        source="strategy_manager",
                        target=sid,
                        message=f"策略 {sid} 重载失败: {str(e)}",
                        details={"error": str(e)}
                    ),
                    self._loop
                )
            
            raise
        finally:
            # 移除reload标记
            self._reloading.discard(sid)

    # ---------- broadcasting events to children ----------
    def broadcast_event(self, ev_type: str, data: dict) -> None:
        """
        ev_type: 'tick'/'bar'/'order' ...
        data：JSON 序列化负载
        """
        with self._lock:
            for sid, meta in list(self._meta.items()):
                try:
                    meta["conn"].send({"type": "event", "event": {"type": ev_type, "data": data}})
                except Exception as e:
                    self.logger.exception(f"forward fail to {sid}: {e}")

    # ---------- reader thread for child messages ----------
    def _reader_loop(self, sid: str) -> None:
        meta = self._meta.get(sid)
        if not meta:
            return
        conn = meta["conn"]
        while True:
            # 如果进程死亡，则停止
            proc = meta.get("proc")
            if proc and not proc.is_alive():
                # notify ws
                self._forward_to_ws({"type": "status", "sid": sid, "payload": "proc_dead"})
                
                # 检查是否为预期停止，只有意外退出才触发告警
                is_expected_stop = sid in self._expected_stops
                if not is_expected_stop and self.alarm_manager and self._loop:
                    # 只有非预期停止才触发崩溃告警
                    asyncio.run_coroutine_threadsafe(
                        self.alarm_manager.trigger_alarm(
                            alarm_type="process_crash",
                            severity="critical",
                            source="strategy_manager",
                            target=sid,
                            message=f"策略进程 {sid} 意外退出",
                            details={"pid": proc.pid, "exitcode": proc.exitcode}
                        ),
                        self._loop
                    )
                elif is_expected_stop:
                    self.logger.info(f"策略 {sid} 正常停止，不触发告警")
                
                # 清理预期停止标记
                self._expected_stops.discard(sid)
                
                try:
                    self.unload_strategy(sid)
                except Exception:
                    pass
                break

            try:
                if not conn.poll(1.0):
                    continue
                msg = conn.recv()
            except EOFError:
                break
            except Exception as e:
                self.logger.exception(f"reader recv failed: {e}")
                break

            # 将消息转发到已注册的 websocket 队列
            try:
                self._forward_to_ws(msg)
            except Exception as e:
                self.logger.exception(f"forward to ws failed: {e}")

            # 也可以选择在本地记录
            mtype = msg.get("type")
            if mtype == "log":
                self.logger.info(f"[{sid}] {msg.get('payload')}")
            elif mtype == "error":
                self.logger.error(f"[{sid}] ERROR {msg.get('payload')}\n{msg.get('trace')}")
            elif mtype == "save_state_result":
                # 缓存状态数据，供reload使用
                if sid in self._meta:
                    self._meta[sid]["last_state"] = msg.get("payload")
                self.logger.info(f"[{sid}] save_state result received")
            elif mtype == "stopped":
                self.logger.info(f"[{sid}] child stopped")
                # 子进程将被卸载
                try:
                    self.unload_strategy(sid)
                except Exception:
                    pass

    # ---------- WebSocket registration ----------
    def register_ws_queue(self, q: asyncio.Queue) -> None:
        """
        从主事件循环（FastAPI）调用以注册 websocket 队列。

        Args:
            q:

        Returns:
            None
        """
        if q not in self._ws_queues:
            self._ws_queues.append(q)

    def unregister_ws_queue(self, q: asyncio.Queue):
        """
        取消注册

        Args:
            q:

        Returns:

        """
        if q in self._ws_queues:
            self._ws_queues.remove(q)

    def _forward_to_ws(self, msg: dict):
        """
        线程安全转发 -> 在主循环中调度。
        从读取线程调用。
        """
        # 规范化消息：确保 sid/type/payload 顶级键
        normalized = {}
        if isinstance(msg, dict):
            normalized = msg.copy()
        else:
            normalized = {"type": "log", "payload": str(msg)}

        # schedule call on loop
        loop = self._loop
        if not loop:
            # fallback: nothing to push
            return

        def _put_nowait():
            for q in list(self._ws_queues):
                try:
                    q.put_nowait(normalized)
                except asyncio.QueueFull:
                    # skip full queues
                    pass

        loop.call_soon_threadsafe(_put_nowait)

    # ---------- watchdog ----------
    def start_watchdog(self, strategies_dir: str):
        try:
            p = Path(strategies_dir)
            if not p.exists():
                self.logger.warning("strategies dir not found: " + str(p))
                return
            handler = _FileEventHandler(self)
            observer = Observer()
            observer.schedule(handler, str(p), recursive=False)
            observer.start()
            self._watch_observer = observer
            self.logger.info("started watchdog on " + str(p))
        except Exception as e:
            self.logger.exception(f"start_watchdog failed: {e}")

    def stop_watchdog(self):
        if self._watch_observer:
            try:
                self._watch_observer.stop()
                self._watch_observer.join(timeout=1.0)
            except Exception as e:
                self.logger.exception(f"stop_watchdog failed: {e}")
    
    # ---------- 调试和管理方法 ----------
    def get_reloading_strategies(self) -> list:
        """
        获取当前正在reload的策略列表

        Returns:
            list
        """
        return list(self._reloading)
    
    def clear_reload_lock(self, sid: str) -> bool:
        """
        清除reload锁（仅用于调试/恢复）

        Args:
            sid:

        Returns:

        """
        if sid in self._reloading:
            self._reloading.discard(sid)
            self.logger.warning(f"手动清除 {sid} 的reload锁")
            return True
        return False
    
    # ===== 新增：订阅管理和交易信号处理 =====
    
    def set_subscription_manager(self, subscription_manager) -> None:
        """
        设置订阅管理器引用

        Args:
            subscription_manager:

        Returns:

        """
        self._subscription_manager = subscription_manager
        self.logger.info("已设置订阅管理器引用")
    
    def set_trade_signal_handler(self, trade_signal_handler):
        """设置交易信号处理器引用"""
        self._trade_signal_handler = trade_signal_handler
        self.logger.info("已设置交易信号处理器引用")
    
    def register_strategy_subscription(self, sid: str, subscription_info: dict[str, Any]):
        """
        注册策略订阅信息
        
        Args:
            sid: 策略ID
            subscription_info: 订阅信息 {instruments: [...], intervals: [...]}
        """
        with self._lock:
            self._strategy_subscriptions[sid] = subscription_info
        
        self.logger.info(f"策略 {sid} 订阅信息已注册: {subscription_info}")
        
        # 转发给订阅管理器
        if self._subscription_manager:
            instruments = subscription_info.get('instruments', [])
            intervals = subscription_info.get('intervals', [])
            self._subscription_manager.register_strategy_subscription(sid, instruments, intervals)
        
        # 发布订阅更新事件
        if self.event_bus:
            event = Event(
                EventType.STRATEGY_SUBSCRIPTION_UPDATE,
                payload={
                    "strategy_id": sid,
                    "instruments": subscription_info.get('instruments', []),
                    "intervals": subscription_info.get('intervals', [])
                }
            )
            self.event_bus.publish(event)
    
    def unregister_strategy_subscription(self, sid: str):
        """取消策略订阅信息"""
        with self._lock:
            if sid in self._strategy_subscriptions:
                del self._strategy_subscriptions[sid]
        
        # 通知订阅管理器
        if self._subscription_manager:
            self._subscription_manager.unregister_strategy_subscription(sid)
        
        self.logger.info(f"策略 {sid} 订阅信息已取消")
    
    def handle_strategy_trade_signal(self, sid: str, signal_data: dict[str, Any]):
        """
        处理来自策略的交易信号
        
        Args:
            sid: 策略ID
            signal_data: 信号数据
        """
        try:
            self.logger.info(f"收到策略 {sid} 的交易信号: {signal_data}")
            
            # 发布策略交易信号事件
            if self.event_bus:
                event = Event(
                    EventType.STRATEGY_TRADE_SIGNAL,
                    payload={
                        "strategy_id": sid,
                        "signal_data": signal_data
                    }
                )
                self.event_bus.publish(event)
            
            # 直接转发给交易信号处理器（如果存在）
            if self._trade_signal_handler:
                # 这里可以添加直接调用逻辑，或者依赖事件总线
                pass
        
        except Exception as e:
            self.logger.error(f"处理策略 {sid} 交易信号异常: {e}", exc_info=True)
    
    def _handle_signal_result(self, event):
        """处理策略信号执行结果"""
        try:
            payload = event.payload
            strategy_id = payload.get("strategy_id")
            signal_id = payload.get("signal_id")
            status = payload.get("status")
            message = payload.get("message")
            
            if not strategy_id:
                return
            
            self.logger.info(f"策略 {strategy_id} 信号 {signal_id} 执行结果: {status} - {message}")
            
            # 转发结果给策略进程
            with self._lock:
                meta = self._meta.get(strategy_id)
                if meta and meta.get("conn"):
                    try:
                        result_msg = {
                            "type": "signal_result",
                            "signal_id": signal_id,
                            "status": status,
                            "message": message,
                            "signal_data": payload.get("signal_data", {})
                        }
                        meta["conn"].send(result_msg)
                        self.logger.debug(f"已转发信号结果给策略 {strategy_id}")
                    except Exception as e:
                        self.logger.warning(f"转发信号结果失败: {e}")
        
        except Exception as e:
            self.logger.error(f"处理信号结果事件异常: {e}", exc_info=True)
    
    def get_strategy_subscriptions(self) -> dict[str, dict[str, Any]]:
        """获取所有策略的订阅信息"""
        with self._lock:
            return self._strategy_subscriptions.copy()
    
    def broadcast_market_data(self, data_type: str, data: Any):
        """
        向所有策略广播行情数据
        
        Args:
            data_type: 数据类型 ('tick', 'bar')
            data: 数据对象
        """
        event_data = {
            "type": data_type,
            "data": data
        }
        
        # 使用现有的 broadcast_event 方法
        self.broadcast_event(data_type, event_data)

    def get_last_event_time(self) -> dict[str, float]:
        """获取最后一次处理的事件时间"""
        return self._last_event_time


class _FileEventHandler(FileSystemEventHandler):
    """
    文件系统事件处理器
    """
    def __init__(self, manager: StrategyManagerIPC):
        super().__init__()
        self.manager = manager

    @staticmethod
    def _valid(path: str) -> bool:
        """
        判断文件是否有效

        Args:
            path:

        Returns:

        """
        if not path.endswith(".py"):
            return False
        name = Path(path).stem
        if name.startswith("__"):
            return False
        return True

    def on_modified(self, event) -> None:
        """
        处理文件修改事件

        Args:
            event:

        Returns:

        """
        if event.is_directory:
            return
        if not self._valid(event.src_path):
            return
        module_name = Path(event.src_path).stem
        now = time.time()
        last = self.manager.get_last_event_time().get(module_name, 0)
        if now - last < _DEBOUNCE:
            return
        self.manager.get_last_event_time()[module_name] = now
        # find which sid uses this file
        for sid, cfg in list(self.manager.registry.strategies.items()):
            f = cfg.get("file")
            if f and Path(f).stem == module_name:
                Thread(target=self.manager.reload_strategy, args=(sid,), daemon=True).start()
                break
