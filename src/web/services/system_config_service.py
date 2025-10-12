#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : system_config_service.py
@Date       : 2025/10/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统配置管理服务
"""
import json
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any

from src.utils.log import get_logger

logger = get_logger(__name__)


class SystemConfigService:
    """系统配置管理服务"""
    
    _CONFIG_FILE = Path("config") / "system.yaml"
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        获取系统配置
        
        Returns:
            配置字典，包含 dev_mode 和 dev_trading_hours_check
        """
        try:
            if not cls._CONFIG_FILE.exists():
                logger.error(f"配置文件不存在: {cls._CONFIG_FILE}")
                return {
                    "success": False,
                    "message": "配置文件不存在"
                }
            
            with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 提取 base 配置
            base_config = config.get('base', {})
            
            return {
                "success": True,
                "config": {
                    "dev_mode": base_config.get('dev_mode', True),
                    "dev_trading_hours_check": base_config.get('dev_trading_hours_check', False)
                }
            }
            
        except Exception as e:
            error_msg = f"读取系统配置失败: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }
    
    @classmethod
    async def update_config(cls, user_id: int, updates: Dict[str, Any], db) -> Dict[str, Any]:
        """
        更新系统配置
        
        Args:
            user_id: 操作用户ID
            updates: 要更新的配置项 (dev_mode, dev_trading_hours_check)
            db: 数据库会话（AsyncSession）
            
        Returns:
            {"success": True/False, "message": str, "backup": str}
        """
        try:
            # 1. 备份原配置
            backup_file = cls._CONFIG_FILE.with_suffix('.yaml.bak')
            shutil.copy(cls._CONFIG_FILE, backup_file)
            logger.info(f"配置已备份到: {backup_file}")
            
            # 2. 读取现有配置
            with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                current_config = yaml.safe_load(f) or {}
            
            # 3. 更新 base 配置项
            if 'base' not in current_config:
                current_config['base'] = {}
            
            if 'dev_mode' in updates:
                current_config['base']['dev_mode'] = updates['dev_mode']
                logger.info(f"更新 dev_mode: {updates['dev_mode']}")
            
            if 'dev_trading_hours_check' in updates:
                current_config['base']['dev_trading_hours_check'] = updates['dev_trading_hours_check']
                logger.info(f"更新 dev_trading_hours_check: {updates['dev_trading_hours_check']}")
            
            # 4. 写入新配置（保持格式和注释）
            with open(cls._CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    current_config,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            
            # 5. 记录审计日志
            try:
                from src.web.services.datacenter_service import DataCenterService
                await DataCenterService._log_operation(
                    db=db,
                    user_id=user_id,
                    operation="system_config_update",
                    target="system",
                    details=json.dumps(updates, ensure_ascii=False),
                    success=True
                )
            except Exception as log_error:
                logger.warning(f"审计日志记录失败: {log_error}")
            
            logger.info(f"系统配置已更新: {list(updates.keys())}")
            
            return {
                "success": True,
                "message": "系统配置已更新",
                "backup": str(backup_file)
            }
            
        except Exception as e:
            error_msg = f"更新系统配置失败: {e}"
            logger.error(error_msg, exc_info=True)
            
            # 记录失败的审计日志
            try:
                from src.web.services.datacenter_service import DataCenterService
                await DataCenterService._log_operation(
                    db=db,
                    user_id=user_id,
                    operation="system_config_update",
                    target="system",
                    details=json.dumps({"error": str(e)}, ensure_ascii=False),
                    success=False,
                    error_message=error_msg
                )
            except Exception as log_error:
                logger.warning(f"审计日志记录失败: {log_error}")
            
            return {
                "success": False,
                "message": error_msg
            }

