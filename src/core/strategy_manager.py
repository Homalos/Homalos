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
from typing import Any, Dict, Optional, List

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from src.core.strategy_worker import run_strategy_process  # child entry
from src.strategy.strategy_registry import StrategyRegistry
from src.utils.log.logger import get_logger

# message delivered to WS clients will be JSON serializable dict:
# {"sid":"...", "type":"log"/"order"/"error"/"status", "payload": ...}

_DEBOUNCE = 2.0  # 增加到2秒，避免重复触发

class StrategyManagerIPC:
    def __init__(self, strategies_pkg: str, registry_path: str, mp_ctx=None):
        self.logger = get_logger("StrategyManagerIPC")
        self.strategies_pkg = strategies_pkg  # module package prefix for dynamic import if needed
        self.registry = StrategyRegistry(registry_path)
        self.mp_ctx = mp_ctx or mp.get_context()  # allow injection for testing
        # meta: sid -> {proc, conn, module, class_name, file_path, last_state}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self._reloading: set = set()  # 正在reload的策略ID集合

        # WebSocket integration:
        # we will store a set of asyncio.Queues (one per active websocket connection)
        self._ws_queues: List[asyncio.Queue] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # watchdog
        self._watch_observer: Optional[Observer] = None
        self._last_event_time: Dict[str, float] = {}

    # ---------- event loop registration ----------
    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Call once from the FastAPI app on startup to allow thread->loop callbacks."""
        self._loop = loop

    # ---------- process lifecycle ----------
    def load_strategy(self, sid: str):
        """
        Start child process for strategy id defined in registry.
        registry[strategy_id] expected fields: {'file': 'src.strategy.strategies.example',
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

            # prepare conn
            parent_conn, child_conn = mp.Pipe(duplex=True)
            # determine module path and class name
            module_path = cfg.get("module") or cfg.get("file")  # prefer explicit module key
            class_name = cfg.get("class", "Strategy")
            params = cfg.get("params", {})

            # spawn process
            proc = self.mp_ctx.Process(target=run_strategy_process, args=(sid, module_path, class_name, params, child_conn), daemon=True)
            proc.start()

            meta = {
                "proc": proc,
                "conn": parent_conn,
                "module": module_path,
                "class": class_name,
                "file": cfg.get("file"),
                "last_state": None
            }
            self._meta[sid] = meta

            # start reader thread for this child
            t = Thread(target=self._reader_loop, args=(sid,), daemon=True)
            t.start()

            self.logger.info(f"Loaded {sid} (proc pid={proc.pid})")

    def unload_strategy(self, sid: str):
        with self._lock:
            meta = self._meta.get(sid)
            if not meta:
                self.logger.warning(f"{sid} not loaded")
                return

            conn = meta["conn"]
            proc = meta["proc"]

            # request save_state
            try:
                conn.send({"type": "command", "command": "save_state"})
                # read soon from conn (non-blocking short wait)
                start = time.time()
                saved = None
                while time.time() - start < 1.0:
                    if conn.poll():
                        msg = conn.recv()
                        if isinstance(msg, dict) and msg.get("type") == "save_state_result":
                            saved = msg.get("payload")
                            break
                        else:
                            # forward any other msg
                            self._forward_to_ws(msg)
                    time.sleep(0.01)
                meta["last_state"] = saved
            except Exception:
                self.logger.exception("save_state request failed")

            # send stop
            try:
                conn.send({"type": "command", "command": "stop"})
            except Exception:
                self.logger.exception("stop send failed")

            # wait then terminate if needed
            proc.join(timeout=1.0)
            if proc.is_alive():
                try:
                    proc.terminate()
                except Exception:
                    self.logger.exception("terminate failed")
            # cleanup conn
            try:
                conn.close()
            except Exception:
                pass

            del self._meta[sid]
            self.logger.info(f"Unloaded {sid}")

    def reload_strategy(self, sid: str):
        """
        Save state, unload, reload, restore state.
        """
        # 检查是否正在reload
        if sid in self._reloading:
            self.logger.warning(f"{sid} is already reloading, skip duplicate reload")
            raise RuntimeError(f"{sid} is already reloading")
        
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
                            self.logger.warning(f"{sid} process already dead, skipping save_state")
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
                        self.logger.warning(f"save_state failed during reload: {e}")
                
                self.logger.info(f"save_state阶段完成，开始unload {sid}")
                
                # unload if loaded (内联逻辑，避免嵌套锁)
                if sid in self._meta:
                    meta = self._meta[sid]
                    conn = meta["conn"]
                    proc = meta["proc"]
                    
                    # send stop command
                    self.logger.info(f"发送stop命令给 {sid}")
                    try:
                        conn.send({"type": "command", "command": "stop"})
                    except Exception as e:
                        self.logger.warning(f"stop send failed: {e}")
                    
                    # wait for process to exit
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
                    
                    # cleanup connection
                    try:
                        conn.close()
                    except Exception:
                        pass
                    
                    # remove from meta
                    del self._meta[sid]
                    self.logger.info(f"Unloaded {sid}")

            time.sleep(0.1)
            
            # load again
            self.load_strategy(sid)

            # restore state
            if saved is not None and sid in self._meta:
                try:
                    new_conn = self._meta[sid]["conn"]
                    new_conn.send({"type": "command", "command": "load_state", "state": saved})
                except Exception as e:
                    self.logger.warning(f"load_state send failed: {e}")

            self.logger.info(f"Reloaded {sid}")
        finally:
            # 移除reload标记
            self._reloading.discard(sid)

    # ---------- broadcasting events to children ----------
    def broadcast_event(self, ev_type: str, data: dict):
        """
        ev_type: 'tick'/'bar'/'order' ...
        data: JSON-serializable payload
        """
        with self._lock:
            for sid, meta in list(self._meta.items()):
                try:
                    meta["conn"].send({"type": "event", "event": {"type": ev_type, "data": data}})
                except Exception:
                    self.logger.exception(f"forward fail to {sid}")

    # ---------- reader thread for child messages ----------
    def _reader_loop(self, sid: str):
        meta = self._meta.get(sid)
        if not meta:
            return
        conn = meta["conn"]
        while True:
            # if process died, stop
            proc = meta.get("proc")
            if proc and not proc.is_alive():
                # notify ws
                self._forward_to_ws({"type": "status", "sid": sid, "payload": "proc_dead"})
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
            except Exception:
                self.logger.exception("reader recv failed")
                break

            # forward messages to registered websocket queues
            try:
                self._forward_to_ws(msg)
            except Exception:
                self.logger.exception("forward to ws failed")

            # also optionally log locally
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
                # child will be cleaned up by unload
                try:
                    self.unload_strategy(sid)
                except Exception:
                    pass

    # ---------- WebSocket registration ----------
    def register_ws_queue(self, q: asyncio.Queue):
        """Called from main event loop (FastAPI) to register a websocket queue."""
        if q not in self._ws_queues:
            self._ws_queues.append(q)

    def unregister_ws_queue(self, q: asyncio.Queue):
        if q in self._ws_queues:
            self._ws_queues.remove(q)

    def _forward_to_ws(self, msg: dict):
        """
        Thread-safe forward -> schedule on main loop.
        Called from reader threads.
        """
        # normalize message: ensure sid/type/payload top-level keys
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
        except Exception:
            self.logger.exception("start_watchdog failed")

    def stop_watchdog(self):
        if self._watch_observer:
            try:
                self._watch_observer.stop()
                self._watch_observer.join(timeout=1.0)
            except Exception:
                self.logger.exception("stop_watchdog failed")
    
    # ---------- 调试和管理方法 ----------
    def get_reloading_strategies(self):
        """获取当前正在reload的策略列表"""
        return list(self._reloading)
    
    def clear_reload_lock(self, sid: str):
        """清除reload锁（仅用于调试/恢复）"""
        if sid in self._reloading:
            self._reloading.discard(sid)
            self.logger.warning(f"手动清除 {sid} 的reload锁")
            return True
        return False


class _FileEventHandler(FileSystemEventHandler):
    def __init__(self, manager: StrategyManagerIPC):
        super().__init__()
        self.manager = manager

    def _valid(self, path: str) -> bool:
        if not path.endswith(".py"):
            return False
        name = Path(path).stem
        if name.startswith("__"):
            return False
        return True

    def on_modified(self, event):
        if event.is_directory:
            return
        if not self._valid(event.src_path):
            return
        module_name = Path(event.src_path).stem
        now = time.time()
        last = self.manager._last_event_time.get(module_name, 0)
        if now - last < _DEBOUNCE:
            return
        self.manager._last_event_time[module_name] = now
        # find which sid uses this file
        for sid, cfg in list(self.manager.registry.strategies.items()):
            f = cfg.get("file")
            if f and Path(f).stem == module_name:
                Thread(target=self.manager.reload_strategy, args=(sid,), daemon=True).start()
                break


