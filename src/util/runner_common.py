#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : runner_common.py
@Date       : 2025/6/2 21:36
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: Runner的公共方法
"""
import argparse
import sys
from argparse import Namespace

from src.util.i18n import _
from src.util.logger import logger, setup_logging


def runner_args(arg_desc: str) -> Namespace:
    """
    定义命令行参数解析器。

    Args:
        arg_desc (str): 命令行工具的描述。

    Returns:
        argparse.Namespace: 包含解析后的命令行参数的命名空间对象。

    """
    setup_logging(service_name=__name__)
    parser = argparse.ArgumentParser(description=arg_desc)
    parser.add_argument(
        "--ctp_env",  # Renamed from --env for clarity
        default="simnow",
        type=str,
        help="The CTP environment name defined in broker_config.json. Defaults to 'simnow'."
    )
    parser.add_argument(
        "--config_env",
        default=None,  # Changed from "dev" to None
        type=str,
        help="The configuration environment to load (e.g., 'dev', 'prod', 'backtest'). Overrides global_config.yaml."
    )
    parser.add_argument(
        "--log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the minimum logging level."
    )
    # +++ Add --lang argument for overriding config language +++
    parser.add_argument(
        "--lang",
        type=str,
        default=None,  # Default is None, will use config or i18n default
        help="Language code for i18n (e.g., en, ""). Overrides configuration file setting."
    )
    args = parser.parse_args()

    # 正在使用的日志环境(Log environments being used)
    if args.ctp_env == "simnow" and '--ctp_env' not in sys.argv:
        logger.info(_("未指定 --ctp_env，使用默认 CTP 环境：{}"), args.ctp_env)
    if args.config_env:
        logger.info(_("使用配置环境：'{}'"), args.config_env)
    else:
        logger.info(_("未指定 --config_env，仅使用基本 global_config.yaml。"))

    return args
