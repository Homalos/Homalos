#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_logger.py
@Date       : 2025/11/17
@Author     : Lumosylva
@Description: 策略专用日志配置
将策略日志单独存储到 strategy_YYYYMMDD.log 文件中
"""
import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from src.utils.get_path import get_path_ins


class StrategyLoggerManager:
    """策略日志管理器"""
    
    _instance: Optional['StrategyLoggerManager'] = None
    _strategy_loggers: dict[str, logging.Logger] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._log_dir = get_path_ins.get_logs_dir()
            self._log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_strategy_logger(self, name: str) -> logging.Logger:
        """
        获取策略专用logger
        
        Args:
            name: logger名称（通常是策略类名或"strategy_worker"）
        
        Returns:
            logging.Logger: 配置好的logger实例
        """
        # 如果已存在，直接返回
        if name in self._strategy_loggers:
            return self._strategy_loggers[name]
        
        # 创建新的logger
        logger = logging.getLogger(f"strategy.{name}")
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
        
        # 创建格式化器
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 1. 策略专用文件处理器（按天轮转）
        strategy_log_file = self._log_dir / f"strategy_{datetime.now().strftime('%Y%m%d')}.log"
        strategy_file_handler = TimedRotatingFileHandler(
            filename=strategy_log_file,
            when='midnight',
            interval=1,
            backupCount=30,  # 保留30天
            encoding='utf-8'
        )
        strategy_file_handler.setLevel(logging.DEBUG)
        strategy_file_handler.setFormatter(formatter)
        strategy_file_handler.suffix = "%Y%m%d"  # 备份文件后缀格式
        logger.addHandler(strategy_file_handler)
        
        # 2. 控制台处理器（可选，用于调试）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 3. 可选：同时写入主日志文件（如果需要在主日志中也保留策略日志）
        # 取消注释以下代码以启用
        # main_log_file = self._log_dir / f"homalos_{datetime.now().strftime('%Y%m%d')}.log"
        # main_file_handler = TimedRotatingFileHandler(
        #     filename=main_log_file,
        #     when='midnight',
        #     interval=1,
        #     backupCount=30,
        #     encoding='utf-8'
        # )
        # main_file_handler.setLevel(logging.INFO)
        # main_file_handler.setFormatter(formatter)
        # main_file_handler.suffix = "%Y%m%d"
        # logger.addHandler(main_file_handler)
        
        # 防止日志传播到根logger（避免重复记录）
        logger.propagate = False
        
        # 缓存logger
        self._strategy_loggers[name] = logger
        
        return logger


# 全局单例
_manager = StrategyLoggerManager()


def get_strategy_logger(name: str = "strategy") -> logging.Logger:
    """
    获取策略专用logger（便捷函数）
    
    Args:
        name: logger名称
    
    Returns:
        logging.Logger: 配置好的logger实例
    
    Example:
        >>> from src.utils.strategy_logger import get_strategy_logger
        >>> logger = get_strategy_logger("MACrossStrategy")
        >>> logger.info("策略启动")
    """
    return _manager.get_strategy_logger(name)
