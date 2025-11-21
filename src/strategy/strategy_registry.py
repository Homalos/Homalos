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

from src.utils.log import get_logger


class StrategyRegistry:
    """
    策略注册中心，JSON 配置，支持启停设置
    """
    def __init__(self, config_path: str):
        self.logger = get_logger(self.__class__.__name__)
        self.path = Path(config_path)
        if not self.path.exists():
            self.path.write_text("{}")
        self._load()
        self._build_uuid_index()

    def _load(self):
        try:
            self.strategies: dict[str, dict] = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except Exception as e:
            self.strategies = {}
            self.logger.exception(f"加载策略配置文件失败: {e}", exc_info=True)
    
    def _build_uuid_index(self):
        """构建UUID到策略ID的索引映射"""
        self.uuid_to_sid: dict[str, str] = {}
        for sid, config in self.strategies.items():
            if "uuid" in config:
                self.uuid_to_sid[config["uuid"]] = sid

    def save(self):
        self.path.write_text(json.dumps(self.strategies, indent=2, ensure_ascii=False), encoding="utf-8")
        self._build_uuid_index()  # 保存后重建索引

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

    def reload(self):
        """重新加载配置文件"""
        self._load()
        self._build_uuid_index()
        self.logger.info("策略配置已重新加载")
    
    def list_all(self):
        return self.strategies

    def list_enabled(self):
        return {k: v for k, v in self.strategies.items() if v.get("enabled", True)}
    
    def get_by_uuid(self, strategy_uuid: str) -> tuple[str, dict] | None:
        """
        通过UUID获取策略配置
        
        Args:
            strategy_uuid: 策略UUID
            
        Returns:
            tuple[str, dict] | None: (策略ID, 策略配置) 或 None
        """
        sid = self.uuid_to_sid.get(strategy_uuid)
        if sid and sid in self.strategies:
            return sid, self.strategies[sid]
        return None
