#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : monitor_service.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统监控服务
"""
import time
from datetime import datetime
from typing import Optional

import psutil  # type: ignore

from src.core.alarm_manager import AlarmManager
from src.utils.log import get_logger

logger = get_logger(__name__)


class MonitorService:
    """系统监控服务类"""

    # 告警管理器实例（由外部设置）
    alarm_manager: Optional["AlarmManager"] = None
    
    # 告警去重缓存 {alarm_type: last_trigger_time}
    _last_alarm_time: dict = {}
    _alarm_cooldown = 300  # 5分钟内同类告警只触发一次
    
    # 资源监控历史（用于持续性检测）
    _cpu_high_start: Optional[float] = None
    _memory_high_start: Optional[float] = None
    _check_duration = 60  # 持续60秒才触发告警
    
    @classmethod
    def set_alarm_manager(cls, alarm_manager):
        """设置告警管理器"""
        cls.alarm_manager = alarm_manager
        logger.info("监控服务已关联告警管理器")
    
    @classmethod
    async def get_system_stats(cls) -> dict:
        """
        获取系统监控数据
        
        Returns:
            dict: 包含CPU、内存使用率和时间戳的字典
            {
                "cpu_percent": 25.3,
                "memory_percent": 45.7,
                "timestamp": "2025-10-08T21:30:45.123456"
            }
        """
        try:
            # 获取CPU使用率（阻塞100ms以获取准确值）
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 获取内存使用率
            memory_percent = psutil.virtual_memory().percent
            
            # 获取当前时间戳
            timestamp = datetime.now().isoformat()
            
            # 检查是否需要触发告警
            if cls.alarm_manager:
                await cls._check_resource_alarms(cpu_percent, memory_percent)
            
            # 保留1位小数
            return {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory_percent, 1),
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"获取系统监控数据失败: {e}")
            # 返回默认值
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "timestamp": datetime.now().isoformat()
            }
    
    @classmethod
    async def _check_resource_alarms(cls, cpu_percent: float, memory_percent: float):
        """
        检查资源使用率并触发告警
        
        Args:
            cpu_percent: CPU使用率
            memory_percent: 内存使用率
        """
        now = time.time()
        
        # 获取告警配置
        config = await cls.alarm_manager.get_config()
        cpu_threshold = float(config.get("cpu_threshold", 80))
        memory_threshold = float(config.get("memory_threshold", 85))
        
        # 检查严重资源不足（立即告警）
        if cpu_percent > 95 or memory_percent > 95:
            alarm_key = "critical_resource"
            last_time = cls._last_alarm_time.get(alarm_key, 0)
            
            if now - last_time > cls._alarm_cooldown:
                await cls.alarm_manager.trigger_alarm(
                    alarm_type="critical_resource",
                    severity="critical",
                    source="system_monitor",
                    message=f"系统资源严重不足: CPU {cpu_percent}%, 内存 {memory_percent}%",
                    details={"cpu_percent": cpu_percent, "memory_percent": memory_percent}
                )
                cls._last_alarm_time[alarm_key] = now
                logger.warning(f"触发严重资源告警: CPU {cpu_percent}%, 内存 {memory_percent}%")
        
        # 检查CPU持续过高
        if cpu_percent > cpu_threshold:
            if cls._cpu_high_start is None:
                cls._cpu_high_start = now
            elif now - cls._cpu_high_start > cls._check_duration:
                alarm_key = "high_cpu"
                last_time = cls._last_alarm_time.get(alarm_key, 0)
                
                if now - last_time > cls._alarm_cooldown:
                    await cls.alarm_manager.trigger_alarm(
                        alarm_type="high_cpu",
                        severity="warning",
                        source="system_monitor",
                        message=f"CPU使用率持续过高: {cpu_percent}% (阈值: {cpu_threshold}%)",
                        details={"cpu_percent": cpu_percent, "threshold": cpu_threshold}
                    )
                    cls._last_alarm_time[alarm_key] = now
                    logger.warning(f"触发CPU告警: {cpu_percent}%")
                
                # 重置计时器，避免频繁告警
                cls._cpu_high_start = now
        else:
            cls._cpu_high_start = None
        
        # 检查内存持续过高
        if memory_percent > memory_threshold:
            if cls._memory_high_start is None:
                cls._memory_high_start = now
            elif now - cls._memory_high_start > cls._check_duration:
                alarm_key = "high_memory"
                last_time = cls._last_alarm_time.get(alarm_key, 0)
                
                if now - last_time > cls._alarm_cooldown:
                    await cls.alarm_manager.trigger_alarm(
                        alarm_type="high_memory",
                        severity="warning",
                        source="system_monitor",
                        message=f"内存使用率持续过高: {memory_percent}% (阈值: {memory_threshold}%)",
                        details={"memory_percent": memory_percent, "threshold": memory_threshold}
                    )
                    cls._last_alarm_time[alarm_key] = now
                    logger.warning(f"触发内存告警: {memory_percent}%")
                
                # 重置计时器，避免频繁告警
                cls._memory_high_start = now
        else:
            cls._memory_high_start = None

