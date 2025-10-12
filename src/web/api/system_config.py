#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : system_config.py
@Date       : 2025/10/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统配置相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.core.security import get_current_user
from src.web.core.database import get_db
from src.web.schemas.system_config import SystemConfigResponse, SystemConfigUpdate, SystemInfoResponse
from src.web.services.system_config_service import SystemConfigService
from src.web.models.user import User
from src.utils.log import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/system-config", tags=["系统配置"])


@router.get("/info", response_model=SystemInfoResponse, summary="获取系统基础信息")
async def get_system_info() -> SystemInfoResponse:
    """
    获取系统基础信息
    
    无需登录认证，公开访问
    
    Returns:
        SystemInfoResponse: 系统基础信息
            - name: 系统名称
            - describe: 系统描述
            - version: 版本号
            - author: 作者
            - copyright: 版权信息
            - contact: 联系方式
            - technology_stack: 技术栈列表
            - timezone: 时区
    """
    result = SystemConfigService.get_system_info()
    
    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('message', '获取系统信息失败'))
    
    info = result.get('info', {})
    return SystemInfoResponse(**info)


@router.get("", response_model=SystemConfigResponse, summary="获取系统配置")
async def get_system_config(
    current_user: User = Depends(get_current_user)
) -> SystemConfigResponse:
    """
    获取系统配置
    
    需要登录认证
    
    Returns:
        SystemConfigResponse: 系统配置数据
            - dev_mode: 开发模式
            - dev_trading_hours_check: 交易时间检查
    """
    result = SystemConfigService.get_config()
    
    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('message', '获取配置失败'))
    
    config = result.get('config', {})
    return SystemConfigResponse(**config)


@router.put("", summary="更新系统配置")
async def update_system_config(
    config_update: SystemConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    更新系统配置
    
    需要登录认证
    
    Args:
        config_update: 要更新的配置项
        
    Returns:
        更新结果
    """
    # 只更新提供的字段
    updates = config_update.model_dump(exclude_unset=True)
    
    if not updates:
        raise HTTPException(status_code=400, detail="没有提供要更新的配置")
    
    logger.info(f"用户 {current_user.username} 请求更新系统配置: {updates}")
    
    result = await SystemConfigService.update_config(
        user_id=current_user.id,
        updates=updates,
        db=db
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('message', '更新配置失败'))
    
    return {
        "success": True,
        "message": result.get('message'),
        "backup": result.get('backup')
    }

