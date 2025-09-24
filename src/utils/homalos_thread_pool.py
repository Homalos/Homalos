#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : homalos_thread_pool.py
@Date       : 2025/9/24 09:55
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 线程池管理类
"""
import concurrent
import os
import threading
from concurrent.futures import ThreadPoolExecutor

from src.utils.log import get_logger


class HomalosThreadPool:
    """
    线程池管理类
    """
    def __init__(self, max_workers=None, thread_name_prefix=''):
        # I/O密集型任务可以设置较多线程，CPU密集型任务不宜设置过多线程
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.thread_name_prefix = thread_name_prefix
        self.executor = None
        self.futures = []
        self.completed_count = 0
        self.lock = threading.Lock()
        self.logger = get_logger(__class__.__name__)

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown(wait=True)

    def start(self):
        """启动线程池"""
        if self.executor is None:
            self.executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix=self.thread_name_prefix
            )
            self.logger.info(f"线程池已启动，最大工作线程数: {self.max_workers}")

    def submit(self, fn, *args, **kwargs):
        """提交任务到线程池"""
        if self.executor is None:
            raise RuntimeError("线程池未启动")

        future = self.executor.submit(fn, *args, **kwargs)
        self.futures.append(future)

        # 添加完成回调
        future.add_done_callback(self._task_completed_callback)
        return future

    def _task_completed_callback(self, future):
        """任务完成回调函数"""
        with self.lock:
            self.completed_count += 1
        try:
            result = future.result()
            self.logger.debug(f"任务完成: {result}")
        except Exception as e:
            self.logger.error(f"任务执行失败: {e}")

    def map(self, fn, iterable, timeout=None, chunk_size=1):
        """映射函数到可迭代对象"""
        if self.executor is None:
            self.start()
        return self.executor.map(fn, iterable, timeout=timeout, chunksize=chunk_size)

    def wait_completion(self, timeout=None):
        """等待所有任务完成"""
        if not self.futures:
            return

        done, not_done = concurrent.futures.wait(
            self.futures, timeout=timeout,
            return_when=concurrent.futures.ALL_COMPLETED
        )

        self.logger.info(f"任务完成情况: {len(done)} 完成, {len(not_done)} 未完成")
        return done, not_done

    def get_progress(self):
        """获取任务进度"""
        total = len(self.futures)
        completed = self.completed_count
        progress = (completed / total * 100) if total > 0 else 0
        return {
            'total': total,
            'completed': completed,
            'progress': progress
        }

    def shutdown(self, wait=True):
        """关闭线程池"""
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.logger.info("线程池已关闭")

    def __del__(self):
        """析构函数，确保资源清理"""
        if self.executor:
            self.shutdown(wait=False)
