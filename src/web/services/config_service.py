#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : config_service.py
@Date       : 2025/10/10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据中心配置管理服务
"""
import json
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any

from src.utils.log import get_logger
from src.constants import DATA_CENTER_CONFIG_FILENAME

logger = get_logger(__name__)


class ConfigService:
    """数据中心配置管理服务"""
    
    _CONFIG_FILE = Path("config") / DATA_CENTER_CONFIG_FILENAME
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            配置字典
        """
        try:
            if not cls._CONFIG_FILE.exists():
                return {"error": "配置文件不存在"}
            
            with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            return {"success": True, "config": config}
            
        except Exception as e:
            error_msg = f"读取配置失败: {e}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg}
    
    @classmethod
    async def update_config(cls, user_id: int, config: Dict[str, Any], db) -> Dict[str, Any]:
        """
        更新配置
        注意：需要重启数据中心才能生效
        
        Args:
            user_id: 操作用户ID
            config: 新配置字典
            db: 数据库会话（AsyncSession）
            
        Returns:
            {"success": True/False, "message": str, "backup": str}
        """
        try:
            # 1. 备份原配置
            backup_file = cls._CONFIG_FILE.with_suffix('.yaml.bak')
            shutil.copy(cls._CONFIG_FILE, backup_file)
            logger.info(f"配置已备份到: {backup_file}")
            
            # 2. 读取现有配置并更新
            with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                current_config = yaml.safe_load(f) or {}
            
            # 更新配置项
            current_config.update(config)
            
            # 写入新配置
            with open(cls._CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.safe_dump(current_config, f, allow_unicode=True, default_flow_style=False)
            
            # 3. 审计日志
            from src.web.services.datacenter_service import DataCenterService
            await DataCenterService._log_operation(
                db=db,
                user_id=user_id,
                operation="config_update",
                target="datacenter",
                details=json.dumps({"keys": list(config.keys())}),
                success=True
            )
            
            logger.info(f"配置已更新: {list(config.keys())}")
            
            return {
                "success": True,
                "message": "配置已更新，需要重启数据中心生效",
                "backup": str(backup_file)
            }
        except Exception as e:
            error_msg = f"更新配置失败: {e}"
            logger.error(error_msg, exc_info=True)
            
            # 记录失败的审计日志
            from src.web.services.datacenter_service import DataCenterService
            await DataCenterService._log_operation(
                db=db,
                user_id=user_id,
                operation="config_update",
                target="datacenter",
                details=json.dumps({"error": str(e)}),
                success=False,
                error_message=error_msg
            )
            
            return {"success": False, "message": error_msg}

