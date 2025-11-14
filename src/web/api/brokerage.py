#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : brokerage.py
@Date       : 2025/11/14
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 用户券商账户API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from src.web.core.database import get_db
from src.web.core.security import get_current_user
from src.web.models.user import User
from src.web.models.brokerage import UserBrokerage
from src.web.schemas.trading_account import (
    UserBrokerageCreate,
    UserBrokerageUpdate,
    UserBrokerageResponse,
    UserBrokerageListResponse
)
from src.web.services.brokerage_service import BrokerageService
from src.utils.log import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/user-brokerages", tags=["用户券商账户"])


@router.post("", response_model=UserBrokerageResponse, summary="创建用户券商账户")
async def create_user_brokerage(
    brokerage_data: UserBrokerageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserBrokerageResponse:
    """
    创建用户券商账户
    
    Args:
        brokerage_data: 券商账户信息
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        UserBrokerageResponse: 创建的券商账户信息
    """
    try:
        service = BrokerageService(db)
        
        # 将Schema数据转换为字典，注意密码字段处理
        account_data = brokerage_data.model_dump()
        # password_encrypted字段在Schema中已经是加密后的，但Service需要明文password
        # 这里需要前端先传明文password，然后Service会自动加密
        # 暂时使用password_encrypted字段名来传递密码（需要前端配合）
        if 'password_encrypted' in account_data:
            account_data['password'] = account_data.pop('password_encrypted')
        
        # 使用服务层创建账户
        brokerage = await service.create_brokerage_account(
            user_id=current_user.id,
            user_type="USER",
            account_data=account_data
        )
        
        return UserBrokerageResponse.from_orm(brokerage)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建券商账户失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建券商账户失败"
        )


@router.get("", response_model=UserBrokerageListResponse, summary="获取用户券商账户列表")
async def get_user_brokerages(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserBrokerageListResponse:
    """
    获取用户的所有券商账户
    
    Args:
        include_inactive: 是否包含未激活账户
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        UserBrokerageListResponse: 券商账户列表
    """
    try:
        service = BrokerageService(db)
        
        brokerages = await service.get_user_brokerages(
            user_id=current_user.id,
            user_type="USER",
            include_inactive=include_inactive
        )
        
        return UserBrokerageListResponse(
            accounts=[UserBrokerageResponse.from_orm(b) for b in brokerages],
            total=len(brokerages)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取券商账户列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取券商账户列表失败"
        )


@router.get("/{brokerage_id}", response_model=UserBrokerageResponse, summary="获取单个券商账户")
async def get_user_brokerage(
    brokerage_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserBrokerageResponse:
    """
    获取单个券商账户详情
    
    Args:
        brokerage_id: 券商账户ID
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        UserBrokerageResponse: 券商账户信息
    """
    try:
        service = BrokerageService(db)
        
        brokerage = await service.get_brokerage_by_id(brokerage_id)
        
        if not brokerage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="券商账户不存在"
            )
        
        # 验证账户所有权
        if brokerage.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此账户"
            )
        
        return UserBrokerageResponse.from_orm(brokerage)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取券商账户失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取券商账户失败"
        )


@router.put("/{brokerage_id}", response_model=UserBrokerageResponse, summary="更新券商账户")
async def update_user_brokerage(
    brokerage_id: int,
    update_data: UserBrokerageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserBrokerageResponse:
    """
    更新券商账户信息
    
    Args:
        brokerage_id: 券商账户ID
        update_data: 更新数据
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        UserBrokerageResponse: 更新后的券商账户信息
    """
    try:
        service = BrokerageService(db)
        
        brokerage = await service.get_brokerage_by_id(brokerage_id)
        
        if not brokerage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="券商账户不存在"
            )
        
        # 验证账户所有权
        if brokerage.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此账户"
            )
        
        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(brokerage, key, value)
        
        # 如果设置为默认账户，使用服务层方法
        if update_data.is_default is True:
            await service.set_default_account(brokerage_id, current_user.id, "USER")
        
        await db.commit()
        await db.refresh(brokerage)
        
        logger.info(f"用户 {current_user.id} 更新了券商账户: {brokerage_id}")
        
        return UserBrokerageResponse.from_orm(brokerage)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新券商账户失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新券商账户失败"
        )


@router.delete("/{brokerage_id}", summary="删除券商账户")
async def delete_user_brokerage(
    brokerage_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    删除券商账户
    
    Args:
        brokerage_id: 券商账户ID
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        dict: 删除结果
    """
    try:
        service = BrokerageService(db)
        
        brokerage = await service.get_brokerage_by_id(brokerage_id)
        
        if not brokerage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="券商账户不存在"
            )
        
        # 验证账户所有权
        if brokerage.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此账户"
            )
        
        await db.delete(brokerage)
        await db.commit()
        
        logger.info(f"用户 {current_user.id} 删除了券商账户: {brokerage_id}")
        
        return {
            "success": True,
            "message": "券商账户已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除券商账户失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除券商账户失败"
        )
