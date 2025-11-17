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
支持双层策略设计（BaseStrategy + SpecificStrategy）
负责数据分发到具体合约的策略实例
"""
import traceback
from threading import Thread

import zmq

from src.utils.strategy_logger import get_strategy_logger

_logger = get_strategy_logger("strategy_worker")


def run_strategy_process(strategy_id: str, module_path: str, class_name: str, params: dict, conn, zmq_port: int = 5555):
    """
    子进程入口：导入模块，实例化策略（class_name），并通过 conn 双向通信。
    conn: multiprocessing.Connection (duplex=True)
    zmq_port: ZeroMQ 订阅端口
    """
    try:
        _run_strategy_process_impl(strategy_id, module_path, class_name, params, conn, zmq_port)
    except KeyboardInterrupt:
        # 优雅退出，不打印 Traceback
        try:
            conn.send({"type": "stopped", "sid": strategy_id})
        except Exception:
            pass
    except Exception as e:
        try:
            conn.send({"type": "error", "sid": strategy_id, "payload": "unexpected error", "trace": traceback.format_exc()})
            conn.send({"type": "stopped", "sid": strategy_id})
        except Exception:
            pass
        _logger.exception(e)


def _run_strategy_process_impl(strategy_id: str, module_path: str, class_name: str, params: dict, conn, zmq_port: int):
    """策略进程实现（内部函数）"""
    try:
        # import by module path like "src.strategy.strategies.example"
        components = module_path.split(".")
        mod = __import__(module_path, fromlist=[components[-1]])
        strategy_class = getattr(mod, class_name)
    except Exception as e:
        conn.send({"type": "error", "sid": strategy_id, "payload": "import failed", "trace": traceback.format_exc()})
        conn.send({"type": "stopped", "sid": strategy_id})
        _logger.exception(e)
        return

    try:
        strategy = strategy_class(**(params or {}))
    except Exception as e:
        conn.send({"type": "error", "sid": strategy_id, "payload": "instantiate failed", "trace": traceback.format_exc()})
        conn.send({"type": "stopped", "sid": strategy_id})
        _logger.exception(e)
        return

    conn.send({"type": "log", "sid": strategy_id, "payload": f"strategy {strategy_id} started"})
    
    # 获取策略订阅的合约列表和K线周期（使用双层设计的属性）
    subscribed_instruments = getattr(strategy, 'instruments', [])
    bar_intervals = getattr(strategy, 'bar_intervals', {})
    
    if not subscribed_instruments:
        conn.send({"type": "error", "sid": strategy_id, "payload": "No instruments subscribed"})
        conn.send({"type": "stopped", "sid": strategy_id})
        return
    
    conn.send({"type": "log", "sid": strategy_id, "payload": f"Subscribed to instruments: {subscribed_instruments}"})
    conn.send({"type": "log", "sid": strategy_id, "payload": f"Bar intervals: {bar_intervals}"})
    
    # 提取所有唯一的K线周期（将dict格式转换为list格式）
    all_intervals = set()
    if isinstance(bar_intervals, dict):
        for intervals_list in bar_intervals.values():
            if isinstance(intervals_list, list):
                all_intervals.update(intervals_list)
            else:
                all_intervals.add(intervals_list)
    elif isinstance(bar_intervals, list):
        all_intervals.update(bar_intervals)
    
    # 发送订阅信息到主进程（统一使用 list[Interval] 格式）
    conn.send({
        "type": "subscription",
        "sid": strategy_id,
        "payload": {
            "instruments": subscribed_instruments,
            "intervals": list(all_intervals)  # 统一为 list[Interval] 格式
        }
    })
    
    # 检查是否为双层策略设计
    specific_strategy_map = getattr(strategy, 'specific_strategy_map', None)
    if not specific_strategy_map:
        conn.send({"type": "error", "sid": strategy_id, "payload": "Missing specific_strategy_map, not a valid BaseStrategy"})
        conn.send({"type": "stopped", "sid": strategy_id})
        return
    
    # 调用所有SpecificStrategy的on_init()
    conn.send({"type": "log", "sid": strategy_id, "payload": "Initializing specific strategies..."})
    for inst_id, spec_strategy in specific_strategy_map.items():
        try:
            if hasattr(spec_strategy, 'on_init'):
                spec_strategy.on_init()
                conn.send({"type": "log", "sid": strategy_id, "payload": f"on_init() called for {inst_id}"})
        except Exception as e:
            conn.send({"type": "error", "sid": strategy_id, 
                     "payload": f"on_init() failed for {inst_id}", 
                     "trace": traceback.format_exc()})
            _logger.exception(e)
    
    # 启动 ZeroMQ 订阅线程
    running = True
    zmq_thread = Thread(
        target=_zmq_subscriber_loop,
        args=(strategy_id, zmq_port, subscribed_instruments, specific_strategy_map, conn, lambda: running),
        daemon=True,
        name=f"ZMQ-Sub-{strategy_id}"
    )
    zmq_thread.start()
    conn.send({"type": "log", "sid": strategy_id, "payload": f"ZeroMQ subscriber thread started on port {zmq_port}"})
    
    # 给 ZMQ 一点时间建立连接 (ZMQ 使用异步连接)
    import time as time_module
    time_module.sleep(0.2)  # 200ms 足够 ZMQ 建立连接
    conn.send({"type": "log", "sid": strategy_id, "payload": "ZMQ connection established, ready to receive data"})
    while running:
        try:
            msg = conn.recv()
        except KeyboardInterrupt:
            # 优雅退出，不打印 Traceback
            break
        except EOFError:
            break
        except Exception as e:
            conn.send({"type": "error", "sid": strategy_id, "payload": "recv failed", "trace": traceback.format_exc()})
            _logger.exception(e)
            break

        if not isinstance(msg, dict):
            continue

        try:
            if msg.get("type") == "event":
                ev = msg.get("event", {})
                ev_type = ev.get("type")
                data = ev.get("data")
                
                # 提取合约ID进行数据过滤和分发
                instrument_id = None
                if hasattr(data, 'instrument_id'):
                    instrument_id = data.instrument_id
                elif isinstance(data, dict):
                    instrument_id = data.get('instrument_id')
                
                # 跳过未订阅的合约数据
                if instrument_id and instrument_id not in subscribed_instruments:
                    continue
                
                # 如果数据中没有instrument_id，跳过（无法分发）
                if not instrument_id:
                    conn.send({"type": "log", "sid": strategy_id, "payload": f"Event {ev_type} has no instrument_id, skipping"})
                    continue
                
                # 根据instrument_id找到对应的SpecificStrategy实例
                specific_strategy = specific_strategy_map.get(instrument_id)
                if not specific_strategy:
                    conn.send({"type": "log", "sid": strategy_id, "payload": f"No specific strategy for {instrument_id}, skipping"})
                    continue
                
                # 分发数据到对应的SpecificStrategy实例
                try:
                    if ev_type == "tick" and hasattr(specific_strategy, "on_tick"):
                        specific_strategy.on_tick(data)
                    elif ev_type == "bar" and hasattr(specific_strategy, "on_bar"):
                        specific_strategy.on_bar(data)
                    elif ev_type == "order" and hasattr(specific_strategy, "on_order"):
                        specific_strategy.on_order(data)
                    elif ev_type == "trade" and hasattr(specific_strategy, "on_trade"):
                        specific_strategy.on_trade(data)
                except Exception as e:
                    conn.send({"type": "error", "sid": strategy_id, "payload": f"handler error for {instrument_id}", "trace": traceback.format_exc()})
                    _logger.exception(e)
            elif msg.get("type") == "command":
                cmd = msg.get("command")
                if cmd == "save_state":
                    # 保存所有SpecificStrategy的状态
                    try:
                        states = {}
                        for inst_id, spec_strategy in specific_strategy_map.items():
                            if hasattr(spec_strategy, "save_state"):
                                try:
                                    state_data = spec_strategy.save_state()
                                    if state_data:
                                        states[inst_id] = state_data
                                except Exception as e:
                                    conn.send({"type": "error", "sid": strategy_id, 
                                             "payload": f"save_state failed for {inst_id}", 
                                             "trace": traceback.format_exc()})
                                    _logger.exception(e)
                        conn.send({"type": "save_state_result", "sid": strategy_id, "payload": states})
                    except Exception as e:
                        conn.send({"type": "error", "sid": strategy_id, "payload": "save_state failed", "trace": traceback.format_exc()})
                        _logger.exception(e)
                elif cmd == "load_state":
                    # 加载所有SpecificStrategy的状态
                    st = msg.get("state")
                    try:
                        if st and isinstance(st, dict):
                            for inst_id, state_data in st.items():
                                spec_strategy = specific_strategy_map.get(inst_id)
                                if spec_strategy and hasattr(spec_strategy, "load_state"):
                                    try:
                                        spec_strategy.load_state(state_data)
                                        conn.send({"type": "log", "sid": strategy_id, 
                                                 "payload": f"load_state done for {inst_id}"})
                                    except Exception as e:
                                        conn.send({"type": "error", "sid": strategy_id, 
                                                 "payload": f"load_state failed for {inst_id}", 
                                                 "trace": traceback.format_exc()})
                                        _logger.exception(e)
                            conn.send({"type": "log", "sid": strategy_id, "payload": "All states loaded"})
                        else:
                            conn.send({"type": "log", "sid": strategy_id, "payload": "No state to load"})
                    except Exception as e:
                        conn.send({"type": "error", "sid": strategy_id, "payload": "load_state failed", "trace": traceback.format_exc()})
                        _logger.exception(e)
                elif cmd == "stop":
                    # 调用所有SpecificStrategy的on_close方法
                    try:
                        for inst_id, spec_strategy in specific_strategy_map.items():
                            if hasattr(spec_strategy, "on_close"):
                                try:
                                    spec_strategy.on_close()
                                    conn.send({"type": "log", "sid": strategy_id, 
                                             "payload": f"on_close called for {inst_id}"})
                                except Exception as e:
                                    conn.send({"type": "error", "sid": strategy_id, 
                                             "payload": f"on_close failed for {inst_id}", 
                                             "trace": traceback.format_exc()})
                                    _logger.exception(e)
                    except Exception as e:
                        conn.send({"type": "error", "sid": strategy_id, "payload": "on_stop failed", "trace": traceback.format_exc()})
                        _logger.exception(e)
                    running = False
            else:
                conn.send({"type": "log", "sid": strategy_id, "payload": f"unknown msg: {msg}"})
        except Exception as e:
            conn.send({"type": "error", "sid": strategy_id, "payload": "processing loop error", "trace": traceback.format_exc()})
            _logger.exception(e)

    conn.send({"type": "stopped", "sid": strategy_id})
    # close connection and exit
    try:
        if conn:
            conn.close()
    except Exception as e:
        _logger.exception(e)


def _zmq_subscriber_loop(strategy_id: str, zmq_port: int, subscribed_instruments: list, specific_strategy_map: dict, conn, is_running_func):
    """
    ZeroMQ 订阅线程，接收主进程推送的行情数据
    
    Args:
        strategy_id: 策略ID
        zmq_port: ZeroMQ 端口
        subscribed_instruments: 订阅的合约列表
        specific_strategy_map: 合约 -> SpecificStrategy 映射
        conn: 与主进程的 IPC 连接（仅用于检查，不要在线程中使用！）
        is_running_func: 返回是否继续运行的函数
    """
    import pickle
    
    try:
        # 创建 ZeroMQ Subscriber
        context = zmq.Context()
        subscriber = context.socket(zmq.SUB)
        subscriber.connect(f"tcp://127.0.0.1:{zmq_port}")
        
        # 订阅所有策略关心的合约的 tick 和 bar 数据
        for instrument_id in subscribed_instruments:
            subscriber.setsockopt_string(zmq.SUBSCRIBE, f"tick:{instrument_id}")
            subscriber.setsockopt_string(zmq.SUBSCRIBE, f"bar:{instrument_id}")
        
        # 设置接收超时（1秒），以便定期检查 running 状态
        subscriber.setsockopt(zmq.RCVTIMEO, 1000)
        
        # 使用 logger 而不是 conn.send()，避免 Pipe 线程安全问题
        _logger.info(f"[{strategy_id}] ZMQ subscribed to {len(subscribed_instruments)} instruments")
        
        while is_running_func():
            try:
                # 接收消息（topic + payload）
                message_parts = subscriber.recv_multipart()
                if len(message_parts) != 2:
                    _logger.warning(
                        f"[{strategy_id}] ZMQ 收到异常消息: {len(message_parts)} 个部分（期望2个），"
                        f"各部分长度: {[len(p) for p in message_parts]}"
                    )
                    continue
                
                topic_bytes, payload_bytes = message_parts
                topic = topic_bytes.decode('utf-8')
                
                # 解析 topic（格式: "tick:SA601" 或 "bar:SA601"）
                parts = topic.split(':', 1)
                if len(parts) != 2:
                    continue
                data_type, instrument_id = parts
                
                # 跳过未订阅的合约
                if instrument_id not in subscribed_instruments:
                    continue
                
                # 反序列化数据
                data = pickle.loads(payload_bytes)
                
                # 找到对应的 SpecificStrategy
                specific_strategy = specific_strategy_map.get(instrument_id)
                if not specific_strategy:
                    continue
                
                # 调用对应的回调
                if data_type == "tick" and hasattr(specific_strategy, "on_tick"):
                    specific_strategy.on_tick(data)
                elif data_type == "bar" and hasattr(specific_strategy, "on_bar"):
                    specific_strategy.on_bar(data)
                    
            except zmq.Again:
                # 超时，继续循环检查 running 状态
                continue
            except Exception as e:
                _logger.error(f"[{strategy_id}] ZMQ receive error: {e}", exc_info=True)
                
    except Exception as e:
        _logger.error(f"[{strategy_id}] ZMQ subscriber failed: {e}", exc_info=True)
    finally:
        try:
            subscriber.close()
            context.term()
            _logger.info(f"[{strategy_id}] ZMQ subscriber stopped")
        except Exception as e:
            _logger.error(f"[{strategy_id}] ZMQ cleanup error: {e}")
