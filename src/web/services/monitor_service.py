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
import psutil
from datetime import datetime
from src.utils.log import get_logger

logger = get_logger(__name__)


class MonitorService:
    """系统监控服务类"""
    
    @staticmethod
    def get_system_stats() -> dict:
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

