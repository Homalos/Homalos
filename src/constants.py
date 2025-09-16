#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : constants.py
@Date       : 2025/9/9 17:10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 全局常量
"""
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.thread_pool import ThreadPool

# ================== 项目中目录名称 ==================
# PROJECT_NAME = "Homalos"  # 项目名称
#
# LOG_DIR_NAME = "log"  # 日志目录名
#
# DATA_DIR_NAME = "data"  # 数据目录名

CONFIG_DIR_NAME = "config"  # 配置目录名

# ================== 项目中文件名称 ==================
SYSTEM_CONFIG_FILENAME = "system.yaml"

SYSTEM_DEV_CONFIG_FILENAME = "extra.dev.yaml"

SYSTEM_PROD_CONFIG_FILENAME = "extra.prod.yaml"

BROKERS_FILENAME = "brokers.yaml"  # 多源服务器节点配置文件名

LOG_CONFIG_FILENAME = "log_config.yaml"  # 全局日志配置文件名

INSTRUMENT_EXCHANGE_FILENAME = "instrument_exchange.json"  # 期货合约与交易所映射信息文件名

PRODUCT_INFO_FILENAME = "product_info.ini"  # 合约乘数及手续费信息文件名

HOLIDAY_FILENAME = "holidays.json"  # 节假日文件名称

# ================== 代码中常量 ==================
file_format = "%Y%m%d"  # 日志文件名格式

log_time_format = "%Y-%m-%d %H:%M:%S.%f"  # 日志文件中时间格式

print_time_format = "%Y-%m-%d %H:%M:%S.%f"  # 控制台打印的时间格式

strategy_map: dict[str, Any] = {}

# 线程池
thread_pool: Optional["ThreadPool"] = None

def init_thread_pool(max_workers: int = 10, add_max_workers: int = 20) -> "ThreadPool":
    """
    初始化全局线程池
    
    Args:
        max_workers: 初始线程池最大线程数
        add_max_workers: 扩展线程池最大线程数
        
    Returns:
        ThreadPool实例
    """
    global thread_pool
    if thread_pool is None:
        from src.utils.thread_pool import ThreadPool
        thread_pool = ThreadPool(max_workers, add_max_workers)
    return thread_pool

def get_thread_pool() -> Optional["ThreadPool"]:
    """
    获取全局线程池实例
    
    Returns:
        ThreadPool实例或None
    """
    return thread_pool

# tick合成K线系统
tick_to_kline_sys = None
