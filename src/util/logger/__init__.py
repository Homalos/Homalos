#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : __init__.py
@Date       : 2025/5/27 23:57
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 日志模块，包含日志配置和日志记录器
"""
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from src.util.i18n import get_translator
from src.util.setting import SETTINGS
from src.util.utility import get_folder_path

# --- Default Configuration ---
DEFAULT_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> - "
    "<level>{level}</level> - "
    "<cyan>{extra[service]}</cyan>"
    " <magenta>{extra[config_env]}</magenta> - "
    "<level>{message}</level>"
)
DEFAULT_SERVICE_NAME = "service_default"  # 默认服务名称(Default service name if not patched)
DEFAULT_LOG_ROTATION = "100 MB"  # 当文件超过 100MB 时(Rotate when file exceeds 100MB)
DEFAULT_LOG_RETENTION = "7 days"  # 保留日志 7 天(Keep logs for 7 days)

# --- 全局记录器对象(Global Logger Object) ---
# 从 loguru 重新导出记录器对象(Re-export the logger object from loguru)
__all__ = ["logger", "setup_logging", "log"]

# 从设置中读取日志级别
DEFAULT_LOG_LEVEL: str = SETTINGS.get("log.level", "INFO")

# --- Setup Function ---
def setup_logging(
        level: str | int = "INFO",
        format_ft: str = DEFAULT_LOG_FORMAT,
        service_name: str = DEFAULT_SERVICE_NAME,
        config_env: Optional[str] = None,
        rotation: str = DEFAULT_LOG_ROTATION,
        retention: str = DEFAULT_LOG_RETENTION,
        **kwargs
):
    """
    为应用程序配置 loguru 记录器。

    参数：
        level（字符串 | int）：输出的最低日志级别（例如，“DEBUG”、“INFO”或 logging.INFO）。
        format_ft（字符串）：日志格式字符串（应包含 {extra[service]}）。
        service_name（字符串）：用于日志文件命名模式的名称。
        config_env（可选[字符串]）：配置环境的名称（例如，“dev”、“prod”）。
        rotation（字符串）：日志文件轮换条件（例如，“100 MB”、“1 天”）。
        retention（字符串）：保留旧日志文件的时间（例如，“7 天”、“1 个月”）。
        **kwargs：直接传递给 logger.add() 的附加关键字参数。

    Configures the loguru logger for the application.

    Args:
        level (str | int): The minimum log level to output (e.g., "DEBUG", "INFO", or logging.INFO).
        format_ft (str): The log format string (should include {extra[service]}).
        service_name (str): Name used for the log filename pattern.
        config_env (Optional[str]): Name of the configuration environment (e.g., 'dev', 'prod').
        rotation (str): Log file rotation condition (e.g., "100 MB", "1 day").
        retention (str): How long to keep old log files (e.g., "7 days", "1 month").
        **kwargs: Additional keyword arguments passed directly to logger.add().
    """
    try:
        logger.remove()
    except ValueError:
        pass

    # +++ Add i18n patcher function +++
    def i18n_patcher(record):
        """
        将翻译功能添加到loguru记录中

        Patches the translation function into the loguru record

        Args:
        record (dict): loguru记录(The loguru record)
        """
        translator = get_translator()  # 获取线程特定的翻译器(Get thread-specific translator)
        if isinstance(record["message"], str):
            record["message"] = translator(record["message"])

    logger.configure(patcher=i18n_patcher)  # Apply the patcher

    current_config_env = config_env if config_env else "dev"  # Use "base" if None, "dev"、"prod" otherwise

    def filter_func(record):
        record["extra"].setdefault("service", service_name)
        record["extra"].setdefault("config_env", current_config_env)  # Always set a value
        return True

    # 如果意外通过 **kwargs 传递了自定义参数，则清除 kwargs
    # Clean kwargs from our custom parameter if it was accidentally passed via **kwargs
    kwargs_cleaned = kwargs.copy()
    if 'config_env' in kwargs_cleaned:
        del kwargs_cleaned['config_env']

    if SETTINGS.get("log.console", True):
        try:
            logger.add(
                sys.stderr,
                level=level,  # Directly use the level argument
                format=format_ft,
                colorize=True,
                filter=filter_func,
                **kwargs_cleaned
            )
        except Exception as e:
            print(f"Error adding console logger: {e}", file=sys.stderr) # Use print for robustness

    if SETTINGS.get("log.file", False):
        log_path: Path = get_folder_path("log")
        file_sink = log_path.joinpath(f"{service_name}_{{time:YYYYMMDD}}.log")
        try:
            logger.add(
                sink=file_sink,
                level=level,  # Directly use the level argument
                format=format_ft,
                rotation=rotation,
                retention=retention,
                encoding="utf-8",
                enqueue=True,
                filter=filter_func,
                **kwargs_cleaned
            )
        except Exception as e:
            # 如果 logger.error 本身可能失败，则回退到打印以确保稳健性
            print(f"Error adding file logger for path '{file_sink}': {e}", file=sys.stderr)


def log(msg: str, level: str = "INFO"):
    logger.log(level, msg)