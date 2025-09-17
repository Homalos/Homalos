#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : alarm.py
@Date       : 2025/9/11 10:59
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 闹钟工具类
"""
import threading
from typing import List, Set, Dict, Optional
from collections import defaultdict
from src.utils.log.logger import get_logger


class Alarm:
    """
    线程安全的闹钟工具类
    
    使用字典数据结构提高性能，支持一个时间点关联多个策略ID
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'Alarm':
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """初始化闹钟实例"""
        if hasattr(self, '_initialized'):
            return
            
        # 使用字典存储时间->策略ID集合的映射，提高查询效率
        self._alarms: Dict[str, Set[str]] = defaultdict(set)
        self._data_lock = threading.RLock()  # 使用可重入锁
        self.logger = get_logger(self.__class__.__name__)
        self._initialized = True
        
        self.logger.info("闹钟系统初始化完成")

    def get_strategy_ids(self, alarm_time: str) -> List[str]:
        """
        根据闹钟时间获取对应的所有策略ID
        
        :param alarm_time: 闹钟时间，格式为 'HH:MM'
        :return: 与指定闹钟时间关联的策略ID列表
        :raises ValueError: 当alarm_time格式不正确时
        """
        if not self._validate_time_format(alarm_time):
            raise ValueError(f"时间格式错误: {alarm_time}，应为 'HH:MM' 格式")
            
        with self._data_lock:
            strategy_ids = list(self._alarms.get(alarm_time, set()))
            
        self.logger.debug(f"时间 {alarm_time} 对应的策略ID: {strategy_ids}")
        return strategy_ids

    def set_alarm(self, alarm_time: str, strategy_id: str = "") -> bool:
        """
        设置闹钟时间和对应的策略ID
        
        :param alarm_time: 闹钟时间，格式为 'HH:MM'
        :param strategy_id: 策略ID，默认为0
        :return: 设置成功返回True，如果已存在则返回False
        :raises ValueError: 当参数格式不正确时
        """
        if not self._validate_time_format(alarm_time):
            raise ValueError(f"时间格式错误: {alarm_time}，应为 'HH:MM' 格式")
            
        if not isinstance(strategy_id, str):
            raise ValueError(f"策略ID必须是字符串，当前值: {strategy_id}")
            
        with self._data_lock:
            if strategy_id in self._alarms[alarm_time]:
                self.logger.warning(f"闹钟 {alarm_time} 的策略ID {strategy_id} 已存在")
                return False
                
            self._alarms[alarm_time].add(strategy_id)
            
        self.logger.info(f"成功设置闹钟: {alarm_time} -> 策略ID {strategy_id}")
        return True

    def remove_alarm(self, alarm_time: str, strategy_id: Optional[str] = None) -> bool:
        """
        移除指定的闹钟设置
        
        :param alarm_time: 闹钟时间
        :param strategy_id: 策略ID，如果为None则移除该时间的所有策略
        :return: 移除成功返回True，否则返回False
        """
        if not self._validate_time_format(alarm_time):
            raise ValueError(f"时间格式错误: {alarm_time}，应为 'HH:MM' 格式")
            
        with self._data_lock:
            if alarm_time not in self._alarms:
                self.logger.warning(f"闹钟时间 {alarm_time} 不存在")
                return False
                
            if strategy_id is None:
                # 移除该时间的所有策略
                removed_count = len(self._alarms[alarm_time])
                del self._alarms[alarm_time]
                self.logger.info(f"移除时间 {alarm_time} 的所有闹钟 ({removed_count} 个)")
            else:
                # 移除指定策略
                if strategy_id not in self._alarms[alarm_time]:
                    self.logger.warning(f"策略ID {strategy_id} 在时间 {alarm_time} 不存在")
                    return False
                    
                self._alarms[alarm_time].discard(strategy_id)
                if not self._alarms[alarm_time]:  # 如果集合为空，删除键
                    del self._alarms[alarm_time]
                    
                self.logger.info(f"移除闹钟: {alarm_time} -> 策略ID {strategy_id}")
                
        return True

    def time_in_alarm(self, alarm_time: str) -> bool:
        """
        检查指定时间是否已设置闹钟
        
        :param alarm_time: 要检查的闹钟时间，格式为 'HH:MM'
        :return: 如果时间在闹钟列表中返回True，否则返回False
        """
        if not self._validate_time_format(alarm_time):
            return False
            
        with self._data_lock:
            return alarm_time in self._alarms and len(self._alarms[alarm_time]) > 0

    def get_all_alarms(self) -> Dict[str, List[str]]:
        """
        获取所有闹钟设置
        
        :return: 字典，键为时间，值为策略ID列表
        """
        with self._data_lock:
            return {time: list(strategy_ids) for time, strategy_ids in self._alarms.items()}

    def get_alarm_count(self) -> int:
        """
        获取闹钟总数
        
        :return: 闹钟总数
        """
        with self._data_lock:
            return sum(len(strategy_ids) for strategy_ids in self._alarms.values())

    def clean(self) -> None:
        """
        清理所有闹钟设置
        """
        with self._data_lock:
            count = self.get_alarm_count()
            self._alarms.clear()
            
        self.logger.info(f"已清理所有闹钟，共 {count} 个")

    @staticmethod
    def _validate_time_format(time_str: str) -> bool:
        """
        验证时间格式是否正确
        
        :param time_str: 时间字符串
        :return: 格式正确返回True，否则返回False
        """
        if not isinstance(time_str, str):
            return False
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
                
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, IndexError):
            return False

    def __repr__(self) -> str:
        """字符串表示"""
        with self._data_lock:
            return f"Alarm(alarms={dict(self._alarms)})"