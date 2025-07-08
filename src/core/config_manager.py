#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : config_manager
@Date       : 2025/7/6 20:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 简化的配置管理器，支持热重载和监听
"""
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from src.core.logger import get_logger

logger = get_logger("ConfigManager")


class ConfigManager:
    """简化的配置管理，支持热重载"""
    
    def __init__(self, config_file: str):
        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = {}
        self.watchers: Dict[str, List[Callable]] = defaultdict(list)
        self.last_modified = 0.0
        
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                self.last_modified = self.config_file.stat().st_mtime
                logger.info(f"配置文件已加载: {self.config_file}")
            else:
                logger.warning(f"配置文件不存在: {self.config_file}")
                self.config = {}
        except Exception as e:
            logger.error(f"加载配置文件失败 {self.config_file}: {e}")
            self.config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的路径"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        
        # 导航到父级字典
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置最终值
        old_value = config.get(keys[-1])
        config[keys[-1]] = value
        
        # 触发变更通知
        self._notify_change(key, old_value, value)
        
        logger.info(f"配置已更新: {key} = {value}")
    
    def watch(self, key_pattern: str, callback: Callable[[str, Any, Any], None]) -> None:
        """监听配置变更
        
        Args:
            key_pattern: 配置键模式（支持通配符*）
            callback: 回调函数，接收(key, old_value, new_value)参数
        """
        self.watchers[key_pattern].append(callback)
        logger.info(f"已注册配置监听器: {key_pattern}")
    
    def reload(self) -> bool:
        """热重载配置"""
        if not self.config_file.exists():
            return False
            
        current_modified = self.config_file.stat().st_mtime
        if current_modified <= self.last_modified:
            return False
        
        old_config = self.config.copy()
        self.load_config()
        
        # 通知所有变更
        self._notify_changes(old_config, self.config)
        
        logger.info("配置文件已热重载")
        return True
    
    def save(self) -> None:
        """保存配置到文件"""
        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False, 
                             allow_unicode=True, indent=2)
            
            self.last_modified = self.config_file.stat().st_mtime
            logger.info(f"配置已保存: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def _notify_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """通知单个配置变更"""
        for pattern, callbacks in self.watchers.items():
            if self._match_pattern(key, pattern):
                for callback in callbacks:
                    try:
                        callback(key, old_value, new_value)
                    except Exception as e:
                        logger.error(f"配置变更回调执行失败 {pattern}: {e}")
    
    def _notify_changes(self, old_config: dict, new_config: dict, prefix: str = "") -> None:
        """递归通知配置变更"""
        all_keys = set(old_config.keys()) | set(new_config.keys())
        
        for key in all_keys:
            full_key = f"{prefix}.{key}" if prefix else key
            old_val = old_config.get(key)
            new_val = new_config.get(key)
            
            if old_val != new_val:
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    # 递归检查嵌套配置
                    self._notify_changes(old_val, new_val, full_key)
                else:
                    # 直接值变更
                    self._notify_change(full_key, old_val, new_val)
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """简单的通配符匹配"""
        if pattern == "*":
            return True
        if "*" not in pattern:
            return key == pattern
        
        # 简单的前缀匹配
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        
        return key == pattern
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.config.copy()
    
    def has_key(self, key: str) -> bool:
        """检查配置键是否存在"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return False
        return True


# 全局配置管理器实例（单例模式）
_global_config: Optional[ConfigManager] = None

def get_config_manager(config_file: str = "config/system.yaml") -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager(config_file)
    return _global_config

def get_config(key: str, default: Any = None) -> Any:
    """快捷方式：获取配置值"""
    return get_config_manager().get(key, default)

def set_config(key: str, value: Any) -> None:
    """快捷方式：设置配置值"""
    get_config_manager().set(key, value)

def watch_config(key_pattern: str, callback: Callable[[str, Any, Any], None]) -> None:
    """快捷方式：监听配置变更"""
    get_config_manager().watch(key_pattern, callback) 