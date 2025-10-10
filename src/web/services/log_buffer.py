#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : log_buffer.py
@Date       : 2025/10/10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 日志缓冲管理器 - 用于SSE日志流
"""
import json
import queue
import threading
import sys
from collections import deque
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.utils.log import get_logger

logger = get_logger(__name__)


class LogBuffer:
    """
    日志缓冲管理器
    
    功能：
    1. 缓存最新的日志（默认500条）
    2. 支持多个SSE客户端订阅
    3. 线程安全的日志添加和读取
    4. 提供统计信息
    """
    
    def __init__(self, maxsize: int = 500, max_subscribers: int = 10):
        """
        初始化日志缓冲器
        
        Args:
            maxsize: 缓冲区最大日志数量
            max_subscribers: 最大订阅者数量
        """
        self.logs = deque(maxlen=maxsize)
        self.lock = threading.RLock()
        self.subscribers: List[queue.Queue] = []
        self.max_subscribers = max_subscribers
        self.total_logs_count = 0
        self.maxsize = maxsize
        
        logger.info(f"LogBuffer初始化完成 - 最大缓冲: {maxsize}, 最大订阅者: {max_subscribers}")
    
    def append(self, log_entry: Dict[str, Any]) -> None:
        """
        添加日志到缓冲区并通知所有订阅者
        
        Args:
            log_entry: 日志条目字典
        """
        with self.lock:
            self.logs.append(log_entry)
            self.total_logs_count += 1
            
            # 通知所有订阅者（非阻塞）
            dead_subscribers = []
            for subscriber_queue in self.subscribers:
                try:
                    subscriber_queue.put_nowait(log_entry)
                except queue.Full:
                    # 队列满了，说明客户端消费太慢，标记为待移除
                    dead_subscribers.append(subscriber_queue)
                except Exception as e:
                    logger.error(f"通知订阅者失败: {e}")
                    dead_subscribers.append(subscriber_queue)
            
            # 移除失效的订阅者
            for dead in dead_subscribers:
                try:
                    self.subscribers.remove(dead)
                except ValueError:
                    pass
    
    def get_recent(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        获取最新的N条日志
        
        Args:
            count: 要获取的日志数量
            
        Returns:
            日志列表
        """
        with self.lock:
            if count >= len(self.logs):
                return list(self.logs)
            else:
                # 使用负索引获取最后N条
                return list(self.logs)[-count:]
    
    def subscribe(self) -> queue.Queue:
        """
        创建新的订阅者队列
        
        Returns:
            订阅者专用队列
            
        Raises:
            Exception: 超过最大订阅者数量
        """
        with self.lock:
            if len(self.subscribers) >= self.max_subscribers:
                raise Exception(f"超过最大订阅者数量限制: {self.max_subscribers}")
            
            # 创建订阅者队列（容量100，防止内存溢出）
            subscriber_queue = queue.Queue(maxsize=100)
            self.subscribers.append(subscriber_queue)
            
            logger.info(f"新增订阅者，当前订阅者数量: {len(self.subscribers)}")
            return subscriber_queue
    
    def unsubscribe(self, subscriber_queue: queue.Queue) -> None:
        """
        取消订阅
        
        Args:
            subscriber_queue: 订阅者队列
        """
        with self.lock:
            try:
                self.subscribers.remove(subscriber_queue)
                logger.info(f"订阅者已移除，当前订阅者数量: {len(self.subscribers)}")
            except ValueError:
                pass  # 队列不存在，忽略
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            return {
                "buffer_size": len(self.logs),
                "max_buffer_size": self.maxsize,
                "total_logs": self.total_logs_count,
                "active_subscribers": len(self.subscribers),
                "max_subscribers": self.max_subscribers,
                "memory_usage_kb": round(sys.getsizeof(self.logs) / 1024, 2)
            }
    
    def clear(self) -> None:
        """清空缓冲区"""
        with self.lock:
            self.logs.clear()
            logger.info("日志缓冲区已清空")


# 全局单例
log_buffer = LogBuffer(maxsize=500, max_subscribers=10)


def sse_log_sink(message):
    """
    Loguru自定义Sink - 将日志发送到SSE缓冲区
    
    Args:
        message: Loguru的Message对象
    """
    try:
        record = message.record
        
        # 只处理数据中心相关的日志
        context = record["extra"].get("context", "")
        if not context or "DataCenter" not in context:
            return
        
        # 构建日志条目
        log_entry = {
            "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level": record["level"].name,
            "context": context,
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
            "trace_id": record["extra"].get("trace_id", "-")
        }
        
        # 添加到缓冲区
        log_buffer.append(log_entry)
        
    except Exception as e:
        # 避免sink错误影响日志系统
        print(f"SSE log sink error: {e}", file=sys.stderr)


def format_log_for_display(log_entry: Dict[str, Any]) -> str:
    """
    格式化日志用于显示
    
    Args:
        log_entry: 日志条目
        
    Returns:
        格式化后的日志字符串
    """
    return (
        f"{log_entry['timestamp']} | "
        f"{log_entry['level']:<8} | "
        f"[{log_entry['context']}] "
        f"{log_entry['trace_id']} "
        f"{log_entry['module']}:{log_entry['function']}:{log_entry['line']} "
        f"- {log_entry['message']}"
    )

