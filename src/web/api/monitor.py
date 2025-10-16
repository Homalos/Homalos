#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : monitor.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统监控相关API路由
"""
from fastapi import APIRouter, Depends

from src.web.core.security import get_current_user
from src.web.schemas.monitor import SystemStatsResponse
from src.web.services.monitor_service import MonitorService
from src.web.models.user import User

router = APIRouter(prefix="/monitor", tags=["系统监控"])


@router.get("/system", response_model=SystemStatsResponse, summary="获取系统监控数据")
async def get_system_stats(
    current_user: User = Depends(get_current_user)
) -> SystemStatsResponse:
    """
    获取系统监控数据（CPU、内存使用率）
    
    需要登录认证
    
    Returns:
        SystemStatsResponse: 系统监控数据
            - cpu_percent: CPU使用率（%）
            - memory_percent: 内存使用率（%）
            - timestamp: 数据采集时间（ISO格式）
    """
    stats = await MonitorService.get_system_stats()
    return SystemStatsResponse(**stats)

