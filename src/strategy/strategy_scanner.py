#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_scanner.py
@Date       : 2025/10/22
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略扫描工具 - 自动发现和注册继承BaseStrategy的策略类
"""
import importlib.util
import inspect
import traceback
from pathlib import Path
from typing import Dict, Any, List

from src.strategy.base_strategy import BaseStrategy
from src.utils.log import get_logger

logger = get_logger(__name__)


class StrategyScanner:
    """策略扫描器 - 自动发现策略目录下的所有策略类"""
    
    def __init__(self, strategies_dir: str | Path):
        """
        初始化策略扫描器
        
        Args:
            strategies_dir: 策略文件目录路径
        """
        self.strategies_dir = Path(strategies_dir)
        self.logger = logger
    
    def scan_strategies(self) -> Dict[str, Any]:
        """
        扫描策略目录，自动识别继承BaseStrategy的类
        
        Returns:
            dict: 发现的策略配置字典，格式：
            {
                "strategy_id_1": {
                    "file": "src/strategy/strategies/xxx.py",
                    "module": "src.strategy.strategies.xxx",
                    "class": "ClassName",
                    "enabled": True,
                    "params": {}
                },
                ...
            }
        """
        discovered: Dict[str, Any] = {}
        scan_errors: List[Dict[str, str]] = []
        
        if not self.strategies_dir.exists():
            self.logger.error(f"策略目录不存在: {self.strategies_dir}")
            return discovered
        
        self.logger.info(f"开始扫描策略目录: {self.strategies_dir}")
        
        # 遍历所有Python文件
        for py_file in self.strategies_dir.glob("*.py"):
            # 跳过特殊文件
            if py_file.name.startswith("_") or py_file.name.startswith("."):
                continue
            
            try:
                # 扫描单个策略文件
                strategy_info = self._scan_file(py_file)
                if strategy_info:
                    strategy_id = strategy_info["strategy_id"]
                    discovered[strategy_id] = {
                        "file": strategy_info["file"],
                        "module": strategy_info["module"],
                        "class": strategy_info["class"],
                        "name": strategy_info["name"],  # 策略名称
                        "description": strategy_info["description"],  # 策略描述
                        "author": strategy_info["author"],  # 作者
                        "instruments": strategy_info["instruments"],  # 订阅的合约
                        "enabled": True,  # 默认启用
                        "params": {}
                    }
                    self.logger.info(
                        f"✓ 发现策略: {strategy_info['name']} "
                        f"(ID: {strategy_id[:8]}..., 类: {strategy_info['class']}, 文件: {py_file.name})"
                    )
            except Exception as e:
                error_msg = f"扫描文件 {py_file.name} 失败: {str(e)}"
                self.logger.warning(error_msg)
                scan_errors.append({
                    "file": py_file.name,
                    "error": str(e),
                    "trace": traceback.format_exc()
                })
        
        # 总结扫描结果
        self.logger.info(f"策略扫描完成: 发现 {len(discovered)} 个策略")
        if scan_errors:
            self.logger.warning(f"扫描过程中遇到 {len(scan_errors)} 个错误（已忽略）")
            for error in scan_errors:
                self.logger.debug(f"  - {error['file']}: {error['error']}")
        
        return discovered
    
    def _scan_file(self, py_file: Path) -> Dict[str, Any] | None:
        """
        扫描单个Python文件，查找继承BaseStrategy的类
        
        Args:
            py_file: Python文件路径
            
        Returns:
            dict | None: 策略信息，如果未找到则返回None
            {
                "strategy_id": "uuid生成的ID",
                "file": "相对路径",
                "module": "导入路径",
                "class": "类名",
                "name": "策略名称",
                "description": "策略描述",
                "author": "作者",
                "instruments": ["合约列表"]
            }
        """
        module_path = f"src.strategy.strategies.{py_file.stem}"
        
        try:
            # 动态导入模块（使用完整模块路径作为模块名）
            spec = importlib.util.spec_from_file_location(module_path, py_file)
            if not spec or not spec.loader:
                self.logger.warning(f"无法加载模块规范: {py_file}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 检查模块中的所有类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # 检查是否是BaseStrategy的子类（排除BaseStrategy本身）
                if self._is_strategy_class(obj, name):
                    # 实例化策略以获取策略元数据
                    try:
                        strategy_instance = obj()
                        
                        # 使用 module.class 作为唯一标识符（不使用动态UUID）
                        strategy_id = f"{module_path}.{name}"
                        
                        # 提取策略元数据
                        strategy_name = getattr(strategy_instance, 'strategy_name', name)
                        strategy_content = getattr(strategy_instance, 'strategy_content', '')
                        author = getattr(strategy_instance, 'author', '')
                        instruments = getattr(strategy_instance, 'instruments', [])
                        
                        return {
                            "strategy_id": strategy_id,
                            "file": str(py_file.relative_to(Path.cwd())).replace("\\", "/"),
                            "module": module_path,
                            "class": name,
                            "name": strategy_name,  # 策略名称
                            "description": strategy_content,  # 策略描述
                            "author": author,  # 作者
                            "instruments": instruments  # 订阅的合约
                        }
                    except Exception as e:
                        self.logger.warning(
                            f"实例化策略类 {name} 失败: {e}，跳过此策略"
                        )
                        continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"导入模块 {module_path} 失败: {e}")
            raise
    
    def _is_strategy_class(self, obj: type, name: str) -> bool:
        """
        检查类是否是有效的策略类
        
        Args:
            obj: 类对象
            name: 类名
            
        Returns:
            bool: 是否是有效的策略类
        """
        try:
            # 排除BaseStrategy本身
            if name == "BaseStrategy":
                return False
            
            # 检查是否继承自BaseStrategy
            if not issubclass(obj, BaseStrategy):
                return False
            
            # 确保不是抽象类
            if inspect.isabstract(obj):
                return False
            
            # 确保类定义在当前模块中（排除导入的类）
            module_name = obj.__module__
            if not module_name.startswith("src.strategy.strategies"):
                return False
            
            return True
            
        except Exception:
            return False
    
    def merge_with_existing(
        self, 
        discovered: Dict[str, Any], 
        existing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将扫描结果与现有配置合并
        
        合并规则：
        - 新发现的策略直接添加
        - 已存在的策略保留原有的enabled和params配置，更新其他字段（包括元数据）
        
        Args:
            discovered: 扫描发现的策略配置
            existing: 现有的策略配置
            
        Returns:
            dict: 合并后的策略配置
        """
        merged = existing.copy()
        
        for strategy_id, new_config in discovered.items():
            if strategy_id in merged:
                # 已存在：保留enabled和params，更新其他字段
                old_config = merged[strategy_id]
                merged[strategy_id] = {
                    "file": new_config["file"],
                    "module": new_config["module"],
                    "class": new_config["class"],
                    "name": new_config["name"],  # 更新策略名称
                    "description": new_config["description"],  # 更新策略描述
                    "author": new_config["author"],  # 更新作者
                    "instruments": new_config["instruments"],  # 更新订阅合约
                    "enabled": old_config.get("enabled", True),
                    "params": old_config.get("params", {})
                }
                self.logger.info(f"更新已存在的策略配置: {new_config['name']} ({strategy_id[:8]}...)")
            else:
                # 新策略：直接添加
                merged[strategy_id] = new_config
                self.logger.info(f"添加新策略: {new_config['name']} ({strategy_id[:8]}...)")
        
        return merged

