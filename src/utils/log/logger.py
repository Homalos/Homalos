#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : logger.py
@Date       : 2025/9/8 15:15
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 全局日志模块（loguru+配置化+上下文标签）

1. 外部配置文件 config/log_config.yaml
可配置 level, log_dir, rotation, retention。
方便开发/生产环境切换。

2. 上下文绑定 (logger.bind)
支持给日志增加 context（比如 "strategy", "engine", "datafeed"）。
打印时自动带上 context，便于过滤。

3. 异步环境支持
已经用 enqueue=True，高频 tick 日志写入不会阻塞主线程/事件循环。

4. 全链路日志用同一个 trace_id 串联
"""
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from src.constants import CONFIG_DIR_NAME, LOG_CONFIG_FILENAME, file_format
from src.core.trace_context import get_trace_id

__all__ = ["logger", "get_logger", "get_console_logger"]

# 从当前文件往上获取项目根目录
current_file = Path(__file__).resolve()

# 从当前文件向上获取到项目根目录 /Homalos
root_path: Path = current_file.parent.parent.parent.parent


def _load_log_config(config_filepath: str) -> dict:
    """内部函数：加载日志配置文件，避免循环导入"""
    if not os.path.exists(config_filepath):
        # 如果配置文件不存在，返回默认配置
        return {"logging": {}}
    try:
        with open(config_filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError):
        # 如果配置文件解析失败，返回默认配置
        return {"logging": {}}


# ===================== 初始化全局日志配置 =====================
# 获取日志配置文件名
log_config_name = f"{CONFIG_DIR_NAME}/{LOG_CONFIG_FILENAME}"
config_path = str(root_path / log_config_name)
# 加载日志配置
config = _load_log_config(config_path)
cfg = config.get("logging", {})

is_debug = cfg.get("is_debug", False)  # 是否开启 DEBUG 模式
log_filename = cfg.get("log_filename", "homalos.log")
log_error_filename = cfg.get("log_error_filename", "homalos_error.log")
log_dir_name = cfg.get("log_dir_name", "logs")
level = cfg.get("level", "INFO")            # 输出的最小日志级别
rotation = cfg.get("rotation", "10 MB")     # 日志轮转大小
retention = cfg.get("retention", "7 days")  # 保留天数
compression = cfg.get("compression", "zip") # 压缩

colorize = cfg.get("colorize", True)    # 颜色
enqueue = cfg.get("enqueue", True)      # 多进程程安全
backtrace = cfg.get("backtrace", True)  # 堆栈回溯
diagnose = cfg.get("diagnose", True)    # 诊断

log_dir_path = root_path / log_dir_name
# 确保日志目录存在
Path(log_dir_path).mkdir(parents=True, exist_ok=True)


# ===================== TraceId 自动注入 Filter =====================
class TraceIdFilter:
    """自动注入 trace_id 到日志 extra"""

    def __call__(self, record):
        record["extra"]["trace_id"] = get_trace_id() or "-"
        return True


# ===================== 初始化全局日志配置 =====================
# 清理默认 logger 配置（避免重复打印）
logger.remove()

# 控制台输出格式（根据debug模式决定是否显示详细信息）
if is_debug:
    console_format = ("<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                      "<level>{level: <8}</level> | "
                      "<magenta>[{extra[context]}]</magenta> "
                      "<yellow>{extra[trace_id]}</yellow> "
                      "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
                      "- <level>{message}</level>")
else:
    console_format = ("<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                      "<level>{level: <8}</level> | "
                      "<magenta>[{extra[context]}]</magenta> "
                      "<yellow>{extra[trace_id]}</yellow> "
                      "<cyan>{name}</cyan>:<cyan>{function}</cyan> "
                      "- <level>{message}</level>")

file_format = ("<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<magenta>[{extra[context]}]</magenta> "
               "<yellow>{extra[trace_id]}</yellow> "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
               "- <level>{message}</level>")

# 控制台输出
logger.add(
    sys.stdout,
    level=level,
    format=console_format,
    colorize=colorize,
    backtrace=backtrace,
    diagnose=diagnose,
    enqueue=enqueue,
    filter=TraceIdFilter()
)

# 文件输出（全量日志）
logger.add(
    os.path.join(log_dir_path, log_filename),
    level=level,
    format=file_format,
    colorize=colorize,
    rotation=rotation,
    retention=retention,
    compression=compression,
    encoding="utf-8",
    enqueue=enqueue,
    backtrace=backtrace,
    diagnose=diagnose,
    filter=TraceIdFilter()
)

# 错误日志单独保存
logger.add(
    os.path.join(log_dir_path, log_error_filename),
    level="ERROR",
    format=file_format,
    rotation=rotation,
    retention=retention,
    compression=compression,
    encoding="utf-8",
    enqueue=enqueue,
    backtrace=backtrace,
    diagnose=diagnose,
    filter=TraceIdFilter()
)


# ===================== 控制台专用日志过滤器 =====================
# 存储控制台专用的上下文
_console_only_contexts: set[str] = set()


class FileLogFilter:
    """文件日志过滤器：排除控制台专用的日志"""
    
    def __call__(self, record):
        # 注入 trace_id
        record["extra"]["trace_id"] = get_trace_id() or "-"
        
        # 检查是否为控制台专用上下文
        context = record["extra"].get("context", "")
        is_console_only = any(ctx in context for ctx in _console_only_contexts)
        
        # 如果是控制台专用上下文，则不写入文件
        return not is_console_only


# 重新配置日志器，添加文件过滤器
logger.remove()

# 控制台输出（所有日志）
logger.add(
    sys.stdout,
    level=level,
    colorize=colorize,
    format=console_format,
    backtrace=backtrace,
    diagnose=diagnose,
    enqueue=enqueue,
    filter=TraceIdFilter()
)

# ===================== 对外 API =====================
def get_logger(context: str = "Homalos") -> Any:
    """
    根据模块上下文获取 logger
    trace_id 会自动从全局上下文获取（无需手动传）
    :param context: 模块上下文，默认"Homalos"
    :return: logger
    """
    return logger.bind(context=context)


def get_console_logger(context: str = "Console") -> Any:
    """
    获取只输出到控制台的 logger（不写入文件）
    trace_id 会自动从全局上下文获取（无需手动传）
    :param context: 模块上下文，默认"Console"
    :return: 只输出到控制台的logger
    """
    # 将上下文添加到控制台专用集合
    _console_only_contexts.add(context)
    return logger.bind(context=context)
