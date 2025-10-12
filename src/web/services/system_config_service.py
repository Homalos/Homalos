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
from pathlib import Path
from typing import Dict, Any

from ruamel.yaml import YAML

from src.utils.log import get_logger

logger = get_logger(__name__)


class SystemConfigService:
    """系统配置管理服务"""
    
    _CONFIG_FILE = Path("config") / "system.yaml"
    _EXTRA_DEV_FILE = Path("config") / "extra.dev.yaml"
    _EXTRA_PROD_FILE = Path("config") / "extra.prod.yaml"
    
    @classmethod
    def _get_yaml_handler(cls):
        """
        获取 YAML 处理器，配置为保留引号、缩进和字段顺序
        """
        yaml = YAML()
        yaml.preserve_quotes = True  # 保留引号风格
        yaml.default_flow_style = False  # 使用块风格
        yaml.width = 4096  # 避免自动换行
        return yaml
    
    @classmethod
    def get_system_info(cls) -> Dict[str, Any]:
        """
        获取系统基础信息
        
        Returns:
            系统信息字典
        """
        try:
            if not cls._CONFIG_FILE.exists():
                logger.error(f"配置文件不存在: {cls._CONFIG_FILE}")
                return {
                    "success": False,
                    "message": "配置文件不存在"
                }
            
            yaml = cls._get_yaml_handler()
            with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.load(f) or {}
            
            # 提取 base 配置
            base_config = config.get('base', {})
            
            return {
                "success": True,
                "info": {
                    "name": base_config.get('name', 'Homalos'),
                    "describe": base_config.get('describe', ''),
                    "version": base_config.get('version', '0.0.1'),
                    "author": base_config.get('author', 'Homalos Team'),
                    "copyright": base_config.get('copyright', ''),
                    "contact": base_config.get('contact', ''),
                    "technology_stack": base_config.get('technology_stack', []),
                    "timezone": base_config.get('timezone', 'Asia/Shanghai')
                }
            }
            
        except Exception as e:
            error_msg = f"读取系统信息失败: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }
    
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
            
            yaml = cls._get_yaml_handler()
            with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.load(f) or {}
            
            # 提取 base 配置
            base_config = config.get('base', {})
            dev_mode = base_config.get('dev_mode', True)
            
            # 从对应的 extra 配置文件读取 trading_hours.enable_check
            extra_config_file = cls._EXTRA_DEV_FILE if dev_mode else cls._EXTRA_PROD_FILE
            trading_hours_check = False  # 默认值
            
            try:
                if extra_config_file.exists():
                    with open(extra_config_file, 'r', encoding='utf-8') as f:
                        extra_config = yaml.load(f) or {}
                        trading_hours_check = extra_config.get('trading_hours', {}).get('enable_check', False)
            except Exception as e:
                logger.warning(f"读取 trading_hours.enable_check 失败: {e}")
            
            return {
                "success": True,
                "config": {
                    "dev_mode": dev_mode,
                    "dev_trading_hours_check": trading_hours_check
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
            yaml = cls._get_yaml_handler()
            
            # 1. 备份 system.yaml
            backup_file = cls._CONFIG_FILE.with_suffix('.yaml.bak')
            shutil.copy(cls._CONFIG_FILE, backup_file)
            logger.info(f"配置已备份到: {backup_file}")
            
            # 2. 读取 system.yaml
            with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                current_config = yaml.load(f) or {}
            
            # 3. 更新 base 配置项（只更新 dev_mode）
            if 'base' not in current_config:
                current_config['base'] = {}
            
            if 'dev_mode' in updates:
                current_config['base']['dev_mode'] = updates['dev_mode']
                logger.info(f"更新 dev_mode: {updates['dev_mode']}")
            
            # 4. 写入 system.yaml（保持格式）
            with open(cls._CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(current_config, f)
            
            # 5. 更新 extra 配置文件中的 trading_hours.enable_check（仅开发模式）
            if 'dev_trading_hours_check' in updates:
                dev_mode = current_config.get('base', {}).get('dev_mode', True)
                
                if dev_mode:
                    # 开发模式：更新 extra.dev.yaml
                    extra_config_file = cls._EXTRA_DEV_FILE
                    
                    # 备份 extra 配置文件
                    extra_backup_file = extra_config_file.with_suffix('.yaml.bak')
                    shutil.copy(extra_config_file, extra_backup_file)
                    logger.info(f"extra 配置已备份到: {extra_backup_file}")
                    
                    # 读取并更新
                    with open(extra_config_file, 'r', encoding='utf-8') as f:
                        extra_config = yaml.load(f) or {}
                    
                    if 'trading_hours' not in extra_config:
                        extra_config['trading_hours'] = {}
                    
                    extra_config['trading_hours']['enable_check'] = updates['dev_trading_hours_check']
                    logger.info(f"更新 extra.dev.yaml 的 trading_hours.enable_check: {updates['dev_trading_hours_check']}")
                    
                    # 写入 extra.dev.yaml（保持格式）
                    with open(extra_config_file, 'w', encoding='utf-8') as f:
                        yaml.dump(extra_config, f)
                else:
                    # 生产模式：不允许修改，extra.prod.yaml 的 enable_check 永远为 true
                    logger.warning("生产模式下不允许修改 trading_hours.enable_check，保持为 true")
            
            # 6. 记录审计日志
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
    
    @classmethod
    def _get_extra_config_file(cls) -> Path:
        """
        根据系统配置中的 dev_mode 确定使用哪个 extra 配置文件
        
        Returns:
            配置文件路径 (extra.dev.yaml 或 extra.prod.yaml)
        """
        try:
            # 读取 system.yaml 获取 dev_mode
            if cls._CONFIG_FILE.exists():
                yaml = cls._get_yaml_handler()
                with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = yaml.load(f) or {}
                    dev_mode = config.get('base', {}).get('dev_mode', True)
            else:
                dev_mode = True  # 默认开发模式
            
            # 根据 dev_mode 返回对应的配置文件
            return cls._EXTRA_DEV_FILE if dev_mode else cls._EXTRA_PROD_FILE
            
        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            return cls._EXTRA_DEV_FILE  # 出错时默认返回开发配置
    
    @classmethod
    def get_notification_config(cls) -> Dict[str, Any]:
        """
        获取通知配置
        
        Returns:
            通知配置字典，包含钉钉、企业微信、邮件配置
        """
        try:
            # 确定使用哪个配置文件
            config_file = cls._get_extra_config_file()
            
            if not config_file.exists():
                logger.error(f"配置文件不存在: {config_file}")
                return {
                    "success": False,
                    "message": f"配置文件不存在: {config_file}"
                }
            
            yaml = cls._get_yaml_handler()
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.load(f) or {}
            
            # 提取通知类型配置
            notify_type = config.get('notify_type', {})
            
            # 构建返回数据
            notification_config = {
                "dingtalk": {
                    "enabled": notify_type.get('dingding', False),
                    "name": config.get('ding_app_name', ''),
                    "id": config.get('ding_app_id', ''),
                    "webhookUrl": config.get('ding_address', '')
                },
                "wecom": {
                    "enabled": notify_type.get('weixin', False),
                    "name": config.get('wx_app_name', ''),
                    "corpId": config.get('wx_corp_id', ''),
                    "agentId": config.get('wx_agent_id', ''),
                    "appSecret": config.get('wx_secret', '')
                },
                "email": {
                    "enabled": notify_type.get('email', False),
                    "address": config.get('email_address', ''),
                    "smtpServer": config.get('smtp_server', '')
                }
            }
            
            logger.info(f"从 {config_file} 读取通知配置成功")
            
            return {
                "success": True,
                "config": notification_config
            }
            
        except Exception as e:
            error_msg = f"读取通知配置失败: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }
    
    @classmethod
    async def update_notification_config(cls, user_id: int, updates: Dict[str, Any], db) -> Dict[str, Any]:
        """
        更新通知配置
        
        Args:
            user_id: 操作用户ID
            updates: 要更新的通知配置
            db: 数据库会话（AsyncSession）
            
        Returns:
            {"success": True/False, "message": str, "backup": str}
        """
        try:
            # 确定使用哪个配置文件
            config_file = cls._get_extra_config_file()
            
            # 1. 备份原配置
            backup_file = config_file.with_suffix('.yaml.bak')
            shutil.copy(config_file, backup_file)
            logger.info(f"配置已备份到: {backup_file}")
            
            # 2. 读取现有配置
            yaml = cls._get_yaml_handler()
            with open(config_file, 'r', encoding='utf-8') as f:
                current_config = yaml.load(f) or {}
            
            # 3. 更新配置项
            if 'notify_type' not in current_config:
                current_config['notify_type'] = {}
            
            # 更新钉钉配置
            if 'dingtalk' in updates:
                dingtalk = updates['dingtalk']
                current_config['notify_type']['dingding'] = dingtalk.get('enabled', False)
                current_config['ding_app_name'] = dingtalk.get('name', '')
                current_config['ding_app_id'] = dingtalk.get('id', '')
                current_config['ding_address'] = dingtalk.get('webhookUrl', '')
                logger.info(f"更新钉钉配置: enabled={dingtalk.get('enabled')}")
            
            # 更新企业微信配置
            if 'wecom' in updates:
                wecom = updates['wecom']
                current_config['notify_type']['weixin'] = wecom.get('enabled', False)
                current_config['wx_app_name'] = wecom.get('name', '')
                current_config['wx_corp_id'] = wecom.get('corpId', '')
                current_config['wx_agent_id'] = wecom.get('agentId', '')
                current_config['wx_secret'] = wecom.get('appSecret', '')
                logger.info(f"更新企业微信配置: enabled={wecom.get('enabled')}")
            
            # 更新邮件配置
            if 'email' in updates:
                email = updates['email']
                current_config['notify_type']['email'] = email.get('enabled', False)
                current_config['email_address'] = email.get('address', '')
                current_config['smtp_server'] = email.get('smtpServer', '')
                logger.info(f"更新邮件配置: enabled={email.get('enabled')}")
            
            # 4. 写入新配置（保持格式）
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(current_config, f)
            
            # 5. 记录审计日志
            try:
                from src.web.services.datacenter_service import DataCenterService
                await DataCenterService._log_operation(
                    db=db,
                    user_id=user_id,
                    operation="notification_config_update",
                    target=str(config_file.name),
                    details=json.dumps(updates, ensure_ascii=False),
                    success=True
                )
            except Exception as log_error:
                logger.warning(f"审计日志记录失败: {log_error}")
            
            logger.info(f"通知配置已更新到: {config_file}")
            
            return {
                "success": True,
                "message": "通知配置已更新",
                "backup": str(backup_file)
            }
            
        except Exception as e:
            error_msg = f"更新通知配置失败: {e}"
            logger.error(error_msg, exc_info=True)
            
            # 记录失败的审计日志
            try:
                from src.web.services.datacenter_service import DataCenterService
                await DataCenterService._log_operation(
                    db=db,
                    user_id=user_id,
                    operation="notification_config_update",
                    target="notification",
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

