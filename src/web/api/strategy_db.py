#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_db.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略数据库API路由 - 策略的增删改查
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.core.database import get_db
from src.web.core.security import get_current_user
from src.web.models.admin import Admin
from src.web.services.strategy_db_service import StrategyDbService
from src.web.schemas.strategy_db import (
    StrategyCreate, StrategyUpdate, StrategyResponse, StrategyListResponse,
    StrategyStatusUpdate, StrategyEnableToggle
)
from src.utils.log import get_logger

router = APIRouter(prefix="/api/strategies-db", tags=["strategies-db"])
logger = get_logger(__name__)
strategy_service = StrategyDbService()


@router.post("", response_model=StrategyResponse)
async def create_strategy(
    strategy_data: StrategyCreate,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建策略
    
    - 只有管理员可以创建策略
    - 创建的策略只有创建者能查看和管理
    """
    try:
        result = await strategy_service.create_strategy(
            db,
            current_user.admin_id,
            strategy_data
        )
        return result
    except Exception as e:
        logger.error(f"创建策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建策略失败: {str(e)}")


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取策略详情
    
    - 只能查看自己创建的策略
    """
    try:
        result = await strategy_service.get_strategy_by_id(
            db,
            strategy_id,
            current_user.admin_id
        )
        if not result:
            raise HTTPException(status_code=404, detail="策略不存在或无权限")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略失败: {str(e)}")


@router.get("/uuid/{uuid}", response_model=StrategyResponse)
async def get_strategy_by_uuid(
    uuid: str,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    通过UUID获取策略
    
    - 只能查看自己创建的策略
    """
    try:
        result = await strategy_service.get_strategy_by_uuid(
            db,
            uuid,
            current_user.admin_id
        )
        if not result:
            raise HTTPException(status_code=404, detail="策略不存在或无权限")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略失败: {str(e)}")


@router.get("", response_model=StrategyListResponse)
async def list_strategies(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回的最大记录数"),
    status: str = Query(None, description="策略状态筛选"),
    enabled: bool = Query(None, description="是否启用筛选"),
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    列出管理员创建的所有策略
    
    - 只能查看自己创建的策略
    - 支持按状态和启用状态筛选
    """
    try:
        result = await strategy_service.list_strategies(
            db,
            current_user.admin_id,
            skip=skip,
            limit=limit,
            status=status,
            enabled=enabled
        )
        return result
    except Exception as e:
        logger.error(f"列出策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出策略失败: {str(e)}")


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    strategy_data: StrategyUpdate,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新策略
    
    - 只能更新自己创建的策略
    """
    try:
        result = await strategy_service.update_strategy(
            db,
            strategy_id,
            current_user.admin_id,
            strategy_data
        )
        if not result:
            raise HTTPException(status_code=404, detail="策略不存在或无权限")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新策略失败: {str(e)}")


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除策略
    
    - 只能删除自己创建的策略
    """
    try:
        success = await strategy_service.delete_strategy(
            db,
            strategy_id,
            current_user.admin_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="策略不存在或无权限")
        return {"message": "策略删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除策略失败: {str(e)}")


@router.put("/{strategy_id}/status", response_model=StrategyResponse)
async def update_strategy_status(
    strategy_id: int,
    status_data: StrategyStatusUpdate,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新策略状态"""
    try:
        result = await strategy_service.update_strategy(
            db,
            strategy_id,
            current_user.admin_id,
            StrategyUpdate(status=status_data.status)
        )
        if not result:
            raise HTTPException(status_code=404, detail="策略不存在或无权限")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新策略状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新策略状态失败: {str(e)}")


@router.put("/{strategy_id}/enabled", response_model=StrategyResponse)
async def toggle_strategy_enabled(
    strategy_id: int,
    toggle_data: StrategyEnableToggle,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """启用/禁用策略"""
    try:
        if toggle_data.enabled:
            result = await strategy_service.enable_strategy(
                db,
                strategy_id,
                current_user.admin_id
            )
        else:
            result = await strategy_service.disable_strategy(
                db,
                strategy_id,
                current_user.admin_id
            )
        
        if not result:
            raise HTTPException(status_code=404, detail="策略不存在或无权限")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换策略启用状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"切换策略启用状态失败: {str(e)}")
