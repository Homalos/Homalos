#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_config2.py
@Date       : 2025/9/13 22:35
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 配置管理测试用例2，不使用event_bus和热更新
"""
from pathlib import Path

from src.utils.config_manager import ConfigManager
from src.utils.log import logger


def main():
    config_path = Path(__file__).resolve().parent.parent / "config"/ "extra.dev.yaml"
    logger.info(f"config_path: {config_path}")

    cfg = ConfigManager(str(config_path))

    # 读取配置
    data_dir = cfg.get("base.data_dir")
    logger.info(f"初始名称: {data_dir}")


if __name__ == "__main__":
    main()
