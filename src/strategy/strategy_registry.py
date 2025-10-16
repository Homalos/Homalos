#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_registry.py
@Date       : 2025/10/16 11:27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略注册中心，JSON 配置，支持启停设置

- 负责管理系统中有哪些策略、是否启用、参数配置。
- 可以来源于 JSON 文件、数据库或 REST API。
"""
import json
from pathlib import Path
from typing import Dict


class StrategyRegistry:
    def __init__(self, config_path: str):
        self.path = Path(config_path)
        if not self.path.exists():
            self.path.write_text("{}")
        self._load()

    def _load(self):
        try:
            self.strategies: Dict[str, dict] = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except Exception:
            self.strategies = {}

    def save(self):
        self.path.write_text(json.dumps(self.strategies, indent=2, ensure_ascii=False), encoding="utf-8")

    def add(self, sid: str, file: str, module: str = None, clazz: str = "Strategy", enabled: bool = True, params: dict = None):
        self.strategies[sid] = {
            "file": file,
            "module": module or Path(file).stem,
            "class": clazz,
            "enabled": enabled,
            "params": params or {}
        }
        self.save()

    def remove(self, sid: str):
        self.strategies.pop(sid, None)
        self.save()

    def list_all(self):
        return self.strategies

    def list_enabled(self):
        return {k: v for k, v in self.strategies.items() if v.get("enabled", True)}