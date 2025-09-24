#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : thread_pool.py
@Date       : 2025/9/15 11:15
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 线程池工具类

有以下主要功能：
1. 动态扩展线程池 - 支持多个线程池实例
2. 警戒线管理 - 当线程使用达到警戒线时自动准备新的线程池
3. 线程安全 - 使用锁保护任务提交
4. 异常处理 - 在回调中处理任务异常
5. 资源清理 - 支持上下文管理器和手动清理
6. 线程监控 - 提供线程数量统计功能
"""
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable

from src.utils.log.logger import get_logger


class ThreadPool:
    """
    自定义的线程池类
    """
    def __init__(self, max_workers: int, add_max_workers: int = 5) -> None:
        """
        初始化线程池
        
        Args:
            max_workers: 初始线程池最大线程数
            add_max_workers: 扩展线程池最大线程数
        """
        # 当前使用的线程池序号
        self.now_pool_num: int = 1

        # 当前线程池满了之后的下一个线程池序号
        self.next_pool_num: int = -1

        # 线程池中最大线程池的个数
        self.max_workers: int = max_workers

        # 增加线程池中最大线程池的个数
        self.add_max_workers: int = add_max_workers

        # 简化警戒位置设计，使用固定比例80%
        self.warn_workers_num = int(max_workers * 0.8)
        self.add_warn_workers_num = int(add_max_workers * 0.8)

        self.thread_pool_map: dict[int, ThreadPoolExecutor] = {
            self.now_pool_num: ThreadPoolExecutor(max_workers=max_workers,
                                                  thread_name_prefix=f"ThreadPool_{self.now_pool_num}")
        }
        # 线程池中活跃线程个数的字典
        self.pool_alive_num_map: dict[int, int] = {self.now_pool_num: 0}

        # 提交锁，防止同时提交
        self.submit_lock: threading.Lock = threading.Lock()

        # 准备信号，是否准备好下一个空闲线程池
        self.prepare_flag: bool = False

        self.logger = get_logger(self.__class__.__name__)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，自动清理资源"""
        self.clean_pool()

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        """
        提交任务到线程池 - 简化版
        
        Args:
            fn: 要执行的函数
            *args: 函数的位置参数
            **kwargs: 函数的关键字参数
            
        Returns:
            Future对象，可用于获取执行结果
        """
        with self.submit_lock:
            current_pool = self.now_pool_num
            current_active = self.pool_alive_num_map[current_pool]
            
            # 确定当前线程池的容量限制
            max_capacity = self.max_workers if current_pool == 1 else self.add_max_workers
            warn_threshold = self.warn_workers_num if current_pool == 1 else self.add_warn_workers_num
            
            # 线程池满载处理：切换到预备池
            if current_active >= max_capacity and self.next_pool_num != -1:
                self.now_pool_num = self.next_pool_num
                self.prepare_flag = False
                current_pool = self.now_pool_num
            
            # 达到警戒线：准备下一个池
            elif current_active >= warn_threshold and not self.prepare_flag:
                self.find_free_pool()
                self.prepare_flag = True

            # 提交任务并更新计数
            future = self.thread_pool_map[current_pool].submit(fn, *args, **kwargs)
            self.pool_alive_num_map[current_pool] += 1
            future.add_done_callback(self.callback)
            
            return future

    def find_free_pool(self) -> None:
        """
        寻找空闲线程池或创建新池 - 简化版
        """
        # 先查找现有空闲池
        free_pool = self.which_pool_free()
        
        if free_pool != -1:
            # 找到空闲池，直接使用
            self.next_pool_num = free_pool
        else:
            # 无空闲池，创建新池
            self.next_pool_num = self.add_pool()

    def add_pool(self) -> int:
        """
        增加一个线程池，并返回增加线程池在线程池字典中的序号
        :return:
        """
        add_pool_num = self.get_max_pool_num() + 1

        # 添加线程池
        self.thread_pool_map[add_pool_num] = ThreadPoolExecutor(
            max_workers=self.add_max_workers, thread_name_prefix=f"ThreadPool_{add_pool_num}")
        # 添加线程池活跃线程字典
        self.pool_alive_num_map[add_pool_num] = 0

        return add_pool_num

    def get_max_pool_num(self) -> int:
        """
        获取线程池字典中最大的线程序号
        :return:
        """
        max_num = 0
        for num in self.thread_pool_map.keys():
            if num > max_num:
                max_num = num
        return max_num

    def which_pool_free(self) -> int:
        """
        判断当前线程池字典是否有空闲的线程池
        :return:
        """
        for pool_num in self.thread_pool_map.keys():
            if self.is_pool_free(pool_num):
                return pool_num
        return -1

    def is_pool_free(self, pool_num: int) -> bool:
        """
        判断线程池是否空闲 - 简化版
        使用50%作为空闲标准，更宽松的策略
        """
        max_capacity = self.max_workers if pool_num == 1 else self.add_max_workers
        current_active = self.pool_alive_num_map.get(pool_num, 0)
        
        return current_active < (max_capacity * 0.5)

    def callback(self, ret: Future[Any]) -> None:
        """
        线程池任务完成后的回调函数

        Args:
            ret: 任务执行完成后返回的Future对象
        """
        with self.submit_lock:
            # 获取当前线程所在的线程池编号，并更新活跃线程计数
            pool_num = self.get_pool_num()
            if pool_num != -1 and pool_num in self.pool_alive_num_map:
                if self.pool_alive_num_map[pool_num] > 0:
                    self.pool_alive_num_map[pool_num] -= 1

            # 检查并记录任务执行过程中的异常
            exception = ret.exception()
            if exception is not None:
                self.logger.exception(f"线程池任务执行异常: {exception}")

    @staticmethod
    def get_pool_all_thread(prefix: str = "ThreadPool") -> list:
        """
        获取线程池中的所有线程
        300个活跃线程，循环一万次花费1.1933586597442627s
        :param prefix:
        :return:
        """
        pool_alive_thread = []
        for t in threading.enumerate():
            if prefix in t.name:
                pool_alive_thread.append(t)
        return pool_alive_thread

    @staticmethod
    def get_pool_all_thread_num(prefix: str = "ThreadPool") -> int:
        """获取线程池中所有活跃的线程的数量"""
        pool_alive_thread = []
        for t in threading.enumerate():
            if prefix in t.name:
                pool_alive_thread.append(t)
        return len(pool_alive_thread)

    @staticmethod
    def get_pool_num() -> int:
        """
        获取当前线程所属的线程池编号

        Returns:
            int: 线程池编号，如果当前线程不属于任何线程池则返回-1
        """
        thread_name = threading.current_thread().name
        if 'ThreadPool' not in thread_name:
            return -1
        else:
            return int(thread_name.split('_')[1])

    def clean_pool(self) -> None:
        """
        清理所有线程池并重置为初始状态 - 简化版
        :return:
        """
        with self.submit_lock:
            pool_count = len(self.thread_pool_map)
            total_active = sum(self.pool_alive_num_map.values())
            
            self.logger.info(f'清理线程池: {pool_count}个池, {total_active}个活跃任务')
            
            # 关闭所有线程池
            for pool_num in list(self.thread_pool_map.keys()):
                try:
                    self.thread_pool_map[pool_num].shutdown(wait=True)
                except Exception as e:
                    self.logger.error(f'关闭线程池{pool_num}失败: {e}')
            
            # 重置状态
            self.now_pool_num = 1
            self.next_pool_num = -1
            self.prepare_flag = False
            
            # 重建线程池
            self.thread_pool_map = {
                self.now_pool_num: ThreadPoolExecutor(max_workers=self.max_workers,
                                                      thread_name_prefix=f"ThreadPool_{self.now_pool_num}")
            }
            
            # 重置计数器
            self.pool_alive_num_map = {self.now_pool_num: 0}
            
            self.logger.info('线程池重置完成')

    def show_all_thread(self) -> None:
        """
        显示所有线程池中的线程信息 - 简化版
        """
        total_threads = len(threading.enumerate())
        pool_summary = []
        
        for pool_num in self.thread_pool_map.keys():
            active_threads = self.get_pool_all_thread_num(f"ThreadPool_{pool_num}")
            pool_summary.append(f"池{pool_num}:{active_threads}线程")
        
        self.logger.info(f"线程状态 - 系统总计:{total_threads}, 池分布:[{', '.join(pool_summary)}]")

    def get_simple_status(self) -> dict:
        """
        获取简化的线程池状态信息
        """
        total_pools = len(self.thread_pool_map)
        total_active = sum(self.pool_alive_num_map.values())
        current_pool_active = self.pool_alive_num_map.get(self.now_pool_num, 0)
        
        return {
            'pool_count': total_pools,
            'total_active_tasks': total_active,
            'current_pool': self.now_pool_num,
            'current_pool_load': current_pool_active,
            'next_pool_ready': self.next_pool_num != -1,
            'status': '运行中' if total_active > 0 else '空闲'
        }


class ThreadPoolAdapter:
    """ThreadPool 适配器，让自定义线程池兼容 ThreadPoolExecutor 接口"""

    def __init__(self, max_workers: int, add_max_workers: int | None = None, thread_name_prefix: str = "ThreadPool"):
        """
        初始化线程池适配器

        Args:
            max_workers: 初始最大线程数
            add_max_workers: 扩展线程池最大线程数，默认为 max_workers
            thread_name_prefix: 线程名称前缀（暂时不使用，保持兼容性）
        """
        if add_max_workers is None:
            add_max_workers = max_workers

        self._thread_pool = ThreadPool(max_workers=max_workers, add_max_workers=add_max_workers)
        self._thread_name_prefix = thread_name_prefix

    def submit(self, fn, *args, **kwargs):
        """提交任务到线程池"""
        return self._thread_pool.submit(fn, *args, **kwargs)

    def get_thread_pool(self) -> ThreadPool:
        """获取线程池"""
        return self._thread_pool

    def get_simple_status(self) -> dict:
        """获取简化状态信息"""
        return self._thread_pool.get_simple_status()

    def shutdown(self):
        """关闭线程池"""
        # ThreadPool 的 clean_pool 方法相当于 shutdown(wait=True)
        self._thread_pool.clean_pool()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()
