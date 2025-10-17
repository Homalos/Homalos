#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : config_manager.py
@Date       : 2025/9/13 22:30
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 配置管理工具类

1. 启动程序 → 自动加载配置文件，例如 config.yaml。
2. 修改配置文件（比如改交易标的、风控参数）→ 自动触发 reload()。
3. EventBus 发布 CONFIG_UPDATED → 各个模块收到更新事件。
4. 支持多实例的配置管理

如果只想单纯加载 yaml 文件后直接返回 dict 数据，可以用 utils/utility.py 中 load_yaml()
"""
import asyncio

import yaml
from pathlib import Path
from typing import Any

from watchfiles import awatch

from src.core.event_bus import EventBus, Event
from src.utils.log.logger import get_logger


class ConfigManager(object):
    """
    支持多实例的配置管理器，每个实例可以监控不同的配置文件
    """
    def __init__(self, config_path: str, event_bus: EventBus | None = None):
        self.logger = get_logger(self.__class__.__name__)
        self._config_path = Path(config_path)
        self._data: dict[str, Any] = {}
        self._event_bus = event_bus
        self._watch_task: asyncio.Task | None = None
        self.reload()

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置，支持 a.b.c 的层级查询

        Args:
            key: 键
            default: 值

        Returns:
            Any: value
        """
        parts = key.split(".")
        value = self._data
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def reload(self) -> None:
        """
        重新加载配置

        Returns:
            None
        """
        if not self._config_path.exists():
            self.logger.warning(f"配置文件 {self._config_path} 不存在，使用空配置")
            self._data = {}
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
            self.logger.info(f"配置文件 {self._config_path} 已加载")

            # 发布事件：配置更新
            if self._event_bus:
                self._event_bus.publish(Event("CONFIG_UPDATED", payload=self._data))
                self.logger.info("已发布 CONFIG_UPDATED 事件")
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")

    async def _watch_loop(self) -> None:
        """
        后台协程：监听配置文件变化

        Returns:
            None
        """
        self.logger.info(f"开始监听 {self._config_path}")
        async for changes in awatch(self._config_path.parent):
            for change, path in changes:
                if Path(path) == self._config_path:
                    self.logger.info(f"检测到配置文件变化: {path}，重新加载...")
                    self.reload()

    def start_watch(self) -> None:
        """
        启动文件监听（需要在 asyncio 环境中）

        Returns:
            None
        """
        if self._watch_task is None:
            loop = asyncio.get_running_loop()
            self._watch_task = loop.create_task(self._watch_loop())

    def stop_watch(self) -> None:
        """
        停止文件监听

        Returns:
            None
        """
        if self._watch_task and not self._watch_task.done():
            self._watch_task.cancel()
            self.logger.info("停止监听配置文件")
