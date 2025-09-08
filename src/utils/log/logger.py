#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : logger.py
@Date       : 2025/9/8 15:15
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 日志工具初始化配置
1. 外部配置文件 config/log_config.yaml
可配置 level, log_dir, rotation, retention。
方便开发/生产环境切换。
2. 上下文绑定 (logger.bind)
支持给日志增加 context（比如 "strategy", "engine", "datafeed"）。
打印时自动带上 context，便于过滤。
3. 异步环境支持
已经用 enqueue=True，高频 tick 日志写入不会阻塞主线程/事件循环。
"""
import os
import sys
from pathlib import Path

from loguru import logger

from src.utils.utility import load_config


def get_root_path() -> Path:

    """从当前文件往上获取项目根目录"""
    current_file = Path(__file__).resolve()

    # 从当前文件向上获取到项目根目录 /Homalos
    root_path: Path = current_file.parent.parent.parent.parent
    return root_path


def init_logger(config_path: str = "config/log_config.yaml") -> logger:
    """
    初始化全局日志配置
    """
    root_path = get_root_path()
    config_path = str(root_path / config_path)
    config = load_config(config_path)
    cfg = config.get("logging", {})
    log_filename = cfg.get("log_filename", "homalos.log")
    log_error_filename = cfg.get("log_error_filename", "homalos_error.log")
    log_dir_name = cfg.get("log_dir_name", "logs")
    level = cfg.get("level", "INFO")
    rotation = cfg.get("rotation", "10 MB")
    retention = cfg.get("retention", "7 days")

    colorize = cfg.get("colorize", True)
    enqueue = cfg.get("enqueue", True)
    backtrace = cfg.get("backtrace", True)
    diagnose = cfg.get("diagnose", True)

    log_dir_path = root_path / log_dir_name
    # 确保日志目录存在
    Path(log_dir_path).mkdir(parents=True, exist_ok=True)

    # 清理默认 logger 配置（避免重复打印）
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        level=level,
        colorize=colorize,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
               "<level>{level: <8}</level> "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
               "[context={extra[context]}] "
               "- <level>{message}</level>",
        backtrace=backtrace,
        diagnose=diagnose,
        enqueue=enqueue
    )

    # 文件输出（全量日志）
    logger.add(
        os.path.join(log_dir_path, log_filename),
        level=level,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        enqueue=enqueue,
        backtrace=backtrace,
        diagnose=diagnose,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
               "{name}:{function}:{line} [context={extra[context]}] - {message}"
    )

    # 错误日志单独保存
    logger.add(
        os.path.join(log_dir_path, log_error_filename),
        level="ERROR",
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        enqueue=enqueue,
        backtrace=backtrace,
        diagnose=diagnose,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
               "{name}:{function}:{line} [context={extra[context]}] - {message}"
    )

    # 默认 context = "global"
    return logger.bind(context="global")
