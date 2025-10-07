#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : task_scheduler.py
@Date       : 2025/10/7 20:32
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 任务调度器
"""
import threading
import traceback
from datetime import timedelta

from src.api.thread_pool import thread_pool_ins
from src.utils.log import get_logger
from src.utils.time import time_module_ins


class TaskScheduler:

    def __init__(self):
        # 任务列表，字典类型，键为任务编号，值为任务信息的元组
        self.tasks = {}
        # 当前任务编号，从0开始递增，用于给新任务分配编号
        self.task_id = 0
        # 锁，用于保护对任务列表的访问，防止多线程下出现数据竞争、数据不一致等问题
        self.lock = threading.Lock()
        # 定时器，用于定期检查任务列表中是否有任务需要执行，并执行该任务
        self.timer = None
        self.logger = get_logger(__class__.__name__)

    def statistic(self):
        self.logger.info(f"{'='*18} taskScheduler 模块 {'='*18}")
        nowtime = time_module_ins.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.logger.info(f"当前时间是：{nowtime}")
        self.lock.acquire()
        try:
            # 遍历任务列表，依次输出任务信息
            for task_id, (task_type, task_time, func, day_of_week, month_day, taskName) in self.tasks.items():

                content = f"任务编号：{task_id}，任务类型：{task_type}"
                if taskName is not None:
                    content += f"任务名称：{taskName}"
                if task_time is not None:
                    content += f"，任务时间：{task_time}"
                if day_of_week is not None:
                    content += f"，星期：{day_of_week}"
                if month_day is not None:
                    content += f"，日期：{month_day}"
                self.logger.info(content)
        finally:
            self.lock.release()
        self.logger.info(f"{'='*40}")

    def _add(self, task_type, task_time, func, day_of_week=None, month_day=None, task_name=None) -> int:
        """
        添加一个任务到任务列表，内部使用，添加任务时需要获取锁，以保证对任务列表的操作是原子的

        Args:
            task_type:
            task_time:
            func:
            day_of_week:
            month_day:
            task_name:

        Returns:

        """

        if func is None:
            raise ValueError("传入函数错误"
                             f"task_type:{task_type}\n"
                             f"taskName:{task_name}\n"
                             f"func:{func}\n"
                             f"day_of_week:{day_of_week}\n"
                             f"month_day:{month_day}\n"
                             f"taskName:{task_name}\n")
        with self.lock:
            task_id = self.task_id
            self.tasks[task_id] = (task_type, task_time, func, day_of_week, month_day, task_name)
            self.task_id += 1
            return task_id

    def add_daily_task(self, time_str, func, task_name=None) -> int:
        """
        添加一个每天都要执行的任务，传入时间如“10:00”，返回任务编号

        Args:
            time_str:
            func:
            task_name:

        Returns:
            int task id
        """
        return self._add("daily", time_str, func, task_name=task_name)

    def add_once_task(self, time_str, func, task_name=None) -> int:
        """
        添加一个只执行一次的任务，传入时间如“2023年5月27日13:42:21”，返回任务编号

        Args:
            time_str:
            func:
            task_name:

        Returns:
            int task id
        """
        return self._add("once", time_str, func, task_name=task_name)

    def add_minute_task(self, func, task_name=None) -> int:
        """
        添加一个每分钟都要执行的任务，传入要执行的函数，返回任务编号

        Args:
            func:
            task_name:

        Returns:
            int task id
        """
        return self._add("minute", None, func, task_name=task_name)

    def add_weekday_task(self, time_str, func, day_of_week, task_name=None) -> int:
        """
        添加一个每周某几天都要执行的任务，传入时间、要执行的函数和要执行的星期几，返回任务编号

        Args:
            time_str:
            func:
            day_of_week:
            task_name:

        Returns:
            int task id
        """
        return self._add("weekday", time_str, func, day_of_week, None, task_name)

    def add_monthly_task(self, time_str, func, month_day, task_name=None) -> int:
        """
        添加一个每月某天或某几天都要执行的任务，传入时间、要执行的函数和要执行的日期，返回任务编号

        Args:
            time_str:
            func:
            month_day:
            task_name:

        Returns:
            int task id
        """
        return self._add("monthly", time_str, func, None, month_day, task_name)

    def del_task(self, task_id) -> bool:
        """
        从任务列表中删除一个任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 删除成功返回True，任务不存在返回False
        """
        # 使用 with self.lock: 上下文管理器，自动处理锁的获取和释放
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                return True
            return False

    def check_tasks(self) -> None:
        """
        检查所有任务是否需要执行

        Returns:
            None
        """
        try:
            self.logger.info("执行检查任务函数：check_tasks")
            # 获取当前时间，格式为“年-月-日 时:分:秒”
            now = time_module_ins.now().strftime("%Y-%m-%d %H:%M")
            # print(now)
            # 需要执行的任务列表
            tasks_to_run = []
            # 获取锁，保护对任务列表的访问
            self.lock.acquire()
            try:
                # 遍历任务列表，将需要执行的任务加入到需要执行的任务列表中
                for task_id, (task_type, task_time, func, day_of_week, month_day, taskName) in self.tasks.items():
                    # 如果是每天要执行的任务，并且时间与当前时间匹配，则将其加入待执行列表
                    if task_type == "daily":
                        if time_module_ins.now().strftime("%H:%M") == task_time:
                            tasks_to_run.append(task_id)
                    # 如果是只执行一次的任务，并且时间与当前时间匹配，则将其加入待执行列表
                    elif task_type == "once":
                        if now == task_time:
                            tasks_to_run.append(task_id)
                    # 如果是每分钟都要执行的任务，则将其加入待执行列表
                    elif task_type == "minute":
                        tasks_to_run.append(task_id)
                    # 如果是每周某几天都要执行的任务，并且时间与当前时间匹配，则将其加入待执行列表
                    elif task_type == "weekday":
                        if day_of_week == time_module_ins.now().strftime("%a") and task_time == time_module_ins.now().strftime("%H:%M"):
                            tasks_to_run.append(task_id)
                    # 如果是每月某天或某几天都要执行的任务，并且时间与当前时间匹配，则将其加入待执行列表
                    elif task_type == "monthly":
                        if month_day == time_module_ins.now().strftime("%d") and task_time == time_module_ins.now().strftime("%H:%M"):
                            tasks_to_run.append(task_id)
            finally:
                # 释放锁
                self.lock.release()

            # 对所有需要执行的任务进行依次执行
            for task_id in tasks_to_run:
                task_type, _, func, _, _, _ = self.tasks.get(task_id)
                # 如果是每分钟都要执行的任务，则直接执行任务函数
                if task_type in ["minute", "daily", "weekday", "monthly"]:
                    thread_pool_ins.submit(func)

                # 否则先执行任务函数，然后从任务列表中将该任务删除
                elif task_type in ["once"]:
                    thread_pool_ins.submit(func)
                    self.del_task(task_id)
                else:
                    ValueError(f"task_type有误，task_type：{task_type}")
        except Exception as e:
            self.logger.exception(f"Exception: {e}")
            self.logger.exception(traceback.format_exc())
        finally:
            # 设置下一次检查任务的时间，并启动定时器
            time_now = time_module_ins.now()
            next_minute = (time_now + timedelta(minutes=1)).replace(second=0, microsecond=0)
            self.timer = threading.Timer((next_minute - time_now).total_seconds(), self.check_tasks)
            self.timer.start()

    def run(self) -> None:
        """
        启动任务调度器

        Returns:
            None
        """
        self.timer = threading.Timer(1, self.check_tasks)
        self.timer.start()

    def stop(self) -> None:
        """
        停止任务调度器，取消定时器

        Returns:
            None
        """
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
