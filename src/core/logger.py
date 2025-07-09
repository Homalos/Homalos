#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : logger
@Date       : 2025/6/27 17:16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 日志模块，包含日志配置和日志记录器
"""
import functools
import sys
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Callable, Dict, TypeVar, cast

from loguru import logger

from src.config.global_config import config_settings
from src.config.path import GlobalPath


__all__ = [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "get_logger",
    "logger"
]


def _get_log_format(record: Any) -> str:
    """动态获取日志格式，根据是否有网关名决定格式"""
    # 检查是否有有效的网关名
    has_gateway = "gateway_name" in record["extra"] and record["extra"]["gateway_name"]

    if has_gateway:
        # 带网关名的格式
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level}</level> | "
            "<magenta>{extra[gateway_name]}</magenta> | "
            "<cyan>{extra[module_name]}</cyan> | "
            "<cyan>{function}:{line}</cyan> | "
            "<level>{message}</level>\n"
        )
    else:
        # 不带网关名的格式
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level}</level> | "
            "<cyan>{extra[module_name]}</cyan> | "
            "<cyan>{function}:{line}</cyan> | "
            "<level>{message}</level>\n"
        )


class Logger:
    """
    项目全局日志工具（支持模块名和网关名）

    功能：
    1. 添加模块名作为日志输出的一部分
    2. 添加网关名(gateway_name)作为可选日志参数
    3. 在日志格式中显示网关信息
    4. 支持按网关名过滤日志
    5. 提供模块化的日志获取方式
    6. 网关名与模块名组合标识
    7. 支持动态设置日志级别
    """

    def __init__(self) -> None:
        self.logger = logger
        # 从全局设置中读取日志设置
        self.log_settings: dict = config_settings.get("log", {})
        # 输出的最低日志级别（例如，"DEBUG"、"INFO"）。
        self.level: str = self.log_settings.get("level", "INFO")
        self.log_rotation: str = "100 MB"  # 当文件超过 100MB 时(Rotate when file exceeds 100MB)
        self.log_retention: str = "7 days"  # 保留日志 7 天(Keep logs for 7 days)
        self.module_name: str = "homalos"  # 用于日志文件命名模式的名称，默认项目名称
        self._configure_logger()
        self.module_loggers: Dict[str, Dict[str, Any]] = {}
        self.gateway_loggers: Dict[str, Dict[str, Any]] = {}

    def _configure_logger(self) -> None:
        """配置基础日志器"""
        # 清除默认配置
        self.logger.remove()

        # 创建日志目录
        log_dir: Path = GlobalPath.log_dir_path
        log_dir.mkdir(parents=True, exist_ok=True)

        # 控制台日志配置
        if self.log_settings.get("console", True):
            self.logger.add(
                sink=sys.stdout,
                level=self.level,
                format=_get_log_format,
                colorize=True,
                filter=self._log_filter  # 添加过滤器
            )
        # 文件日志配置
        if self.log_settings.get("file", False):
            # 获取当前日期用于日志文件名
            current_date = datetime.now().strftime("%Y%m%d")
            log_path: Path = GlobalPath.log_dir_path
            file_sink = log_path.joinpath(f"{self.module_name}_{current_date}.log")
            # 信息日志（按天轮转）
            logger.add(
                sink=file_sink,
                level=self.level,
                format=_get_log_format,
                rotation=self.log_settings.get("log_rotation", "100 MB"),
                retention=self.log_settings.get("log_retention", "7 days"),
                encoding="utf-8",
                enqueue=True,
                filter=self._log_filter
            )

    def _log_filter(self, record: Any) -> bool:
        """日志过滤器，根据模块设置日志级别"""
        # 如果没有设置模块和网关，使用默认级别
        if "module_name" not in record["extra"] and "gateway_name" not in record["extra"]:
            return True

        # 检查是否有模块特定的日志级别设置
        module_name = record["extra"].get("module_name", "")
        if module_name in self.module_loggers:
            min_level = self.module_loggers[module_name]["level_no"]
            if record["level"].no < min_level:
                return False

        # 检查是否有网关特定的日志级别设置
        gateway_name = record["extra"].get("gateway_name", "")
        if gateway_name in self.gateway_loggers:
            min_level = self.gateway_loggers[gateway_name]["level_no"]
            if record["level"].no < min_level:
                return False

        return True

    def get_custom_logger(
            self,
            module_name: str = "",
            gateway_name: Optional[str] = None,
            level: str = "INFO"
    ) -> Any:
        """
        获取模块特定的日志器
        :param module_name: 模块名称（建议使用__name__）
        :param gateway_name: 可选，网关/入口名称
        :param level: 可选，为该模块设置特定日志级别
        :return: 绑定模块名和网关名的日志器
        """
        # 创建绑定参数的日志器
        extra = {"module_name": module_name}
        if gateway_name:
            extra["gateway_name"] = gateway_name

        custom_logger = self.logger.bind(**extra)

        # 设置模块特定日志级别
        if level:
            level = level.upper()
            if level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                # 如果有网关名，优先设置网关级别
                if gateway_name:
                    self.gateway_loggers[gateway_name] = {
                        "level": level,
                        "level_no": logger.level(level).no
                    }
                else:
                    self.module_loggers[module_name] = {
                        "level": level,
                        "level_no": logger.level(level).no
                    }

        return custom_logger

    def set_log_level(
            self,
            identifier: str = "",
            level: str = "INFO",
            is_gateway: bool = False
    ) -> None:
        """
        设置特定模块或网关的日志级别
        :param identifier: 模块名或网关名
        :param level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        :param is_gateway: 是否为网关级别
        """
        level = level.upper()
        if level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            return

        level_no = logger.level(level).no

        if is_gateway:
            self.gateway_loggers[identifier] = {
                "level": level,
                "level_no": level_no
            }
        else:
            self.module_loggers[identifier] = {
                "level": level,
                "level_no": level_no
            }

    def get_gateway_logger(self, gateway_name: str, level: Optional[str] = None) -> Any:
        """
        获取网关专用日志器
        :param gateway_name: 网关名称
        :param level: 可选，网关特定日志级别
        :return: 绑定网关名的日志器
        """
        return self.get_custom_logger(
            module_name="Gateway",
            gateway_name=gateway_name,
            level=level or "INFO"
        )

    def get_default_logger(self) -> Any:
        """获取默认日志器（不带模块名）"""
        return self.logger


# 创建全局日志实例
project_logger = Logger()

# 默认日志器（不带模块名）
default_logger = project_logger.get_default_logger()


# 网关日志获取函数
def get_gateway_logger(gateway_name: str, level: Optional[str] = None) -> Any:
    """
    获取网关日志器（简化函数）
    :param gateway_name: 网关名称
    :param level: 可选，网关特定日志级别
    :return: 绑定网关名的日志器
    """
    return project_logger.get_gateway_logger(gateway_name, level)


# 模块日志获取函数
def get_module_logger(module_name: str = "", level: str = "INFO") -> Any:
    """
    获取模块日志器（简化函数）
    :param module_name: 模块名称（默认""）
    :param level: 可选，模块特定日志级别
    :return: 绑定模块名的日志器
    """
    return project_logger.get_custom_logger(module_name, gateway_name=None, level=level)


# 组合日志获取函数
def get_logger(
        module_name: str = "",
        gateway_name: Optional[str] = None,
        level: str = "INFO"
) -> Any:
    """
    获取模块日志器（简化函数）
    :param module_name: 模块名称（默认""）
    :param gateway_name: 可选，网关名称
    :param level: 可选，模块特定日志级别
    :return: 绑定模块名的日志器
    """
    return project_logger.get_custom_logger(module_name=module_name, gateway_name=gateway_name, level=level)


# 定义类型变量，表示函数的参数和返回值类型
T = TypeVar('T')

# 异常捕获装饰器（带模块名支持）
def log_exceptions(module_name: Optional[str] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    自动记录函数异常的装饰器（支持模块名）
    :param module_name: 模块名称，用于日志标识
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # 获取模块名（如果未提供则使用函数所在模块）
        mod_name = module_name or (cast(Any, func).__module__ if hasattr(func, '__module__') else None)
        if mod_name is None:
            raise ValueError("Unable to determine module name for the decorated function.")

        # 创建模块日志器
        mod_logger = get_logger(mod_name)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                mod_logger.opt(exception=True).error(
                    f"Exception in {func.__name__} (args={args}, kwargs={kwargs}): {str(e)}"
                )
                raise

        return wrapper

    return decorator


def log(*args: Any, **kwargs: Any) -> Any:
    return default_logger.log(*args, **kwargs)
