#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_worker.py
@Date       : 2025/10/16 11:10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 子进程入口 — 由 StrategyManager 启动
"""
import traceback


def run_strategy_process(strategy_id: str, module_path: str, class_name: str, params: dict, conn):
    """
    子进程入口：导入模块，实例化策略（class_name），并通过 conn 双向通信。
    conn: multiprocessing.Connection (duplex=True)
    """
    try:
        # import by module path like "src.strategy.example"
        components = module_path.split(".")
        mod = __import__(module_path, fromlist=[components[-1]])
        StrategyClass = getattr(mod, class_name)
    except Exception:
        conn.send({"type": "error", "sid": strategy_id, "payload": "import failed", "trace": traceback.format_exc()})
        conn.send({"type": "stopped", "sid": strategy_id})
        return

    try:
        strategy = StrategyClass(**(params or {}))
    except Exception:
        conn.send({"type": "error", "sid": strategy_id, "payload": "instantiate failed", "trace": traceback.format_exc()})
        conn.send({"type": "stopped", "sid": strategy_id})
        return

    conn.send({"type": "log", "sid": strategy_id, "payload": f"strategy {strategy_id} started"})
    
    # 获取策略订阅的合约列表
    subscribed_instruments = getattr(strategy, 'instruments', [])
    if subscribed_instruments:
        conn.send({"type": "log", "sid": strategy_id, "payload": f"Subscribed to instruments: {subscribed_instruments}"})
    else:
        # 向后兼容：如果没有instruments属性，尝试获取instrument_id
        instrument_id = getattr(strategy, 'instrument_id', None)
        if instrument_id:
            subscribed_instruments = [instrument_id]
            conn.send({"type": "log", "sid": strategy_id, "payload": f"Single instrument mode: {instrument_id}"})

    running = True
    while running:
        try:
            msg = conn.recv()
        except EOFError:
            break
        except Exception:
            conn.send({"type": "error", "sid": strategy_id, "payload": "recv failed", "trace": traceback.format_exc()})
            break

        if not isinstance(msg, dict):
            continue

        try:
            if msg.get("type") == "event":
                ev = msg.get("event", {})
                ev_type = ev.get("type")
                data = ev.get("data")
                
                # 数据过滤：只处理订阅的合约数据
                if subscribed_instruments and hasattr(data, 'instrument_id'):
                    instrument_id = data.instrument_id
                    if instrument_id not in subscribed_instruments:
                        continue  # 跳过未订阅的合约数据
                
                # dispatch by conventional method names
                try:
                    if ev_type == "tick" and hasattr(strategy, "on_tick"):
                        strategy.on_tick(data)
                    elif ev_type == "bar" and hasattr(strategy, "on_bar"):
                        strategy.on_bar(data)
                    elif ev_type == "order" and hasattr(strategy, "on_rtn_order"):
                        strategy.on_rtn_order(data)
                    elif ev_type == "trade" and hasattr(strategy, "on_rtn_trade"):
                        strategy.on_rtn_trade(data)
                except Exception:
                    conn.send({"type": "error", "sid": strategy_id, "payload": "handler error", "trace": traceback.format_exc()})
            elif msg.get("type") == "command":
                cmd = msg.get("command")
                if cmd == "save_state":
                    try:
                        if hasattr(strategy, "save_state"):
                            st = strategy.save_state()
                        else:
                            st = None
                        conn.send({"type": "save_state_result", "sid": strategy_id, "payload": st})
                    except Exception:
                        conn.send({"type": "error", "sid": strategy_id, "payload": "save_state failed", "trace": traceback.format_exc()})
                elif cmd == "load_state":
                    st = msg.get("state")
                    try:
                        if hasattr(strategy, "load_state"):
                            strategy.load_state(st)
                            conn.send({"type": "log", "sid": strategy_id, "payload": "load_state done"})
                    except Exception:
                        conn.send({"type": "error", "sid": strategy_id, "payload": "load_state failed", "trace": traceback.format_exc()})
                elif cmd == "stop":
                    try:
                        if hasattr(strategy, "on_stop"):
                            strategy.on_stop()
                    except Exception:
                        conn.send({"type": "error", "sid": strategy_id, "payload": "on_stop failed", "trace": traceback.format_exc()})
                    running = False
            else:
                conn.send({"type": "log", "sid": strategy_id, "payload": f"unknown msg: {msg}"})
        except Exception:
            conn.send({"type": "error", "sid": strategy_id, "payload": "processing loop error", "trace": traceback.format_exc()})

    conn.send({"type": "stopped", "sid": strategy_id})
    # close connection and exit
    try:
        conn.close()
    except Exception:
        pass
