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
from src.web.models.admin import Admin
from src.web.models.brokerage import UserBrokerage
from src.web.schemas.trading_account import (
    UserBrokerageCreate,
    UserBrokerageUpdate,
    UserBrokerageResponse,
    UserBrokerageListResponse,
    UserBrokerageLogin,
    UserBrokerageLoginResponse
)
from src.web.services.brokerage_service import BrokerageService
from src.utils.log import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/user-brokerages", tags=["用户券商账户"])


@router.post("", response_model=UserBrokerageResponse, summary="创建用户券商账户")
async def create_user_brokerage(
    brokerage_data: UserBrokerageCreate,
    current_user: User | Admin = Depends(get_current_user),
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
        
        # 根据用户类型设置user_type
        from src.web.models.admin import Admin
        if isinstance(current_user, Admin):
            user_type = "ADMIN"
            user_id = current_user.admin_id
        else:
            user_type = "USER"
            user_id = current_user.user_id
        
        # 使用服务层创建账户
        brokerage = await service.create_brokerage_account(
            user_id=user_id,
            user_type=user_type,
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
    current_user: User | Admin = Depends(get_current_user),
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
        
        # 根据用户类型设置参数
        from src.web.models.admin import Admin
        if isinstance(current_user, Admin):
            user_type = "ADMIN"
            user_id = current_user.admin_id
        else:
            user_type = "USER"
            user_id = current_user.user_id
        
        brokerages = await service.get_user_brokerages(
            user_id=user_id,
            user_type=user_type,
            include_inactive=include_inactive
        )
        
        return UserBrokerageListResponse(
            accounts=[UserBrokerageResponse.from_orm(b) for b in brokerages],
            total=len(brokerages)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取券商账户列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取券商账户失败"
        )


@router.get("/{brokerage_id}", response_model=UserBrokerageResponse, summary="获取单个券商账户")
async def get_user_brokerage(
    brokerage_id: int,
    current_user: User | Admin = Depends(get_current_user),
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
        
        # 验证账户所有权（支持Admin和User）
        from src.web.models.admin import Admin
        if isinstance(current_user, Admin):
            user_id = current_user.admin_id
            user_type = "ADMIN"
        else:
            user_id = current_user.user_id
            user_type = "USER"
        
        # 将枚举转换为字符串进行比较
        brokerage_user_type = brokerage.user_type.value if hasattr(brokerage.user_type, 'value') else str(brokerage.user_type)
        
        if brokerage.user_id != user_id or brokerage_user_type.lower() != user_type.lower():
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
    current_user: User | Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserBrokerageResponse:
    # 调试：打印原始数据
    logger.info(f"接收到更新请求，原始数据: {update_data}")
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
        
        # 验证账户所有权（支持Admin和User）
        from src.web.models.admin import Admin
        if isinstance(current_user, Admin):
            user_id = current_user.admin_id
            user_type = "ADMIN"
        else:
            user_id = current_user.user_id
            user_type = "USER"
        
        # 将枚举转换为字符串进行比较
        brokerage_user_type = brokerage.user_type.value if hasattr(brokerage.user_type, 'value') else str(brokerage.user_type)
        
        if brokerage.user_id != user_id or brokerage_user_type.lower() != user_type.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此账户"
            )
        
        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)
        logger.info(f"更新账户 {brokerage_id}，接收到的字段: {list(update_dict.keys())}")
        
        # 转换枚举字段为大写
        if 'account_type' in update_dict and update_dict['account_type']:
            update_dict['account_type'] = update_dict['account_type'].upper()
        if 'status' in update_dict and update_dict['status']:
            update_dict['status'] = update_dict['status'].upper()
        
        # 如果更新密码或敏感信息，需要加密
        # 注意：前端传入的是明文，需要加密后存储
        if 'password' in update_dict:
            if update_dict['password']:  # 如果有值才加密
                logger.info(f"更新账户 {brokerage_id} 的密码（加密后存储）")
                update_dict['password_encrypted'] = service.cipher.encrypt(update_dict['password'])
            del update_dict['password']  # 移除明文密码字段
        
        if 'auth_code' in update_dict:
            if update_dict['auth_code']:  # 如果有值才加密
                update_dict['auth_code'] = service.cipher.encrypt(update_dict['auth_code'])
            # auth_code字段名不变，直接加密覆盖
        
        if 'app_id' in update_dict:
            if update_dict['app_id']:  # 如果有值才加密
                update_dict['app_id'] = service.cipher.encrypt(update_dict['app_id'])
            # app_id字段名不变，直接加密覆盖
        
        for key, value in update_dict.items():
            setattr(brokerage, key, value)
        
        # 如果设置为默认账户，使用服务层方法
        if update_data.is_default is True:
            await service.set_default_account(brokerage_id, user_id, user_type)
        
        await db.commit()
        await db.refresh(brokerage)
        
        logger.info(f"用户 {user_id} ({user_type}) 更新了券商账户: {brokerage_id}")
        
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
    current_user: User | Admin = Depends(get_current_user),
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
        
        # 验证账户所有权（支持Admin和User）
        from src.web.models.admin import Admin
        if isinstance(current_user, Admin):
            user_id = current_user.admin_id
            user_type = "ADMIN"
        else:
            user_id = current_user.user_id
            user_type = "USER"
        
        # 将枚举转换为字符串进行比较
        brokerage_user_type = brokerage.user_type.value if hasattr(brokerage.user_type, 'value') else str(brokerage.user_type)
        
        logger.info(f"[DELETE] 删除账户权限验证: brokerage_id={brokerage_id}, "
                   f"brokerage.user_id={brokerage.user_id}, brokerage.user_type={brokerage_user_type}, "
                   f"current_user_id={user_id}, current_user_type={user_type}")
        
        if brokerage.user_id != user_id or brokerage_user_type.lower() != user_type.lower():
            logger.warning(f"[DELETE] 权限验证失败: 账户所有者({brokerage.user_id}, {brokerage.user_type}) != "
                          f"当前用户({user_id}, {user_type})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此账户"
            )
        
        await db.delete(brokerage)
        await db.commit()
        
        logger.info(f"用户 {user_id} ({user_type}) 删除了券商账户: {brokerage_id}")
        
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


@router.post("/login", response_model=UserBrokerageLoginResponse, summary="登录券商账户")
async def login_brokerage_account(
    login_data: UserBrokerageLogin,
    current_user: User | Admin = Depends(get_current_user),  # 支持User和Admin
    db: AsyncSession = Depends(get_db)
) -> UserBrokerageLoginResponse:
    """
    券商账户登录
    
    Args:
        login_data: 登录数据
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        UserBrokerageLoginResponse: 登录响应（包含账户信息和新token）
    """
    try:
        service = BrokerageService(db)
        
        # 根据用户类型获取正确的user_id和user_type
        from src.web.models.admin import Admin
        if isinstance(current_user, Admin):
            user_id = current_user.admin_id
            user_type = "ADMIN"
        else:
            user_id = current_user.user_id
            user_type = "USER"
        
        # 调用登录服务
        account = await service.login_brokerage_account(
            user_id=user_id,
            account_id=login_data.account_id,
            password=login_data.password,
            remember=login_data.remember,
            user_type=user_type
        )
        
        # 解密密码用于构建broker配置
        decrypted_password = None
        if account.password_encrypted:
            try:
                decrypted_password = service.cipher.decrypt(account.password_encrypted)
            except Exception as e:
                logger.warning(f"解密密码失败（不影响登录）: {e}")
        
        # 生成新的JWT token（包含账户信息）
        from src.web.core.security import create_access_token
        from src.web.models.admin import Admin
        
        # 处理role字段
        role_value = current_user.role
        if hasattr(role_value, 'value'):
            role_value = role_value.value
        
        # 构建token数据
        # 如果是管理员登录，需要使用admin_id；如果是普通用户，使用user_id
        token_data = {
            "sub": current_user.username,
            "role": role_value,
            "trading_account_id": account.id,
            "broker_id": account.broker_id,
            "account_id": account.account_id
        }
        
        # 根据用户类型添加对应的ID字段
        if isinstance(current_user, Admin):
            # 管理员使用admin_id
            token_data["admin_id"] = current_user.admin_id
            logger.info(f"管理员 {current_user.admin_id} 登录券商账户")
        else:
            # 普通用户使用user_id
            token_data["user_id"] = current_user.user_id
            logger.info(f"用户 {current_user.user_id} 登录券商账户")
        
        new_token = create_access_token(data=token_data)
        
        # 设置broker配置到TradingCoreService（使用用户输入的密码）
        if login_data.password:
            try:
                from src.web.services.trading_core_service import TradingCoreService
                from src.common import get_node_config
                from src.utils.config_manager import ConfigManager
                from src.system_config import Config
                import os
                
                # 根据账户的 broker_code 加载对应的服务器节点配置
                brokers_filepath = Config.brokers_filepath
                if not os.path.exists(brokers_filepath):
                    raise ValueError(f"brokers.yaml 配置文件不存在: {brokers_filepath}")
                
                cfg_manager = ConfigManager(str(brokers_filepath))
                
                # 使用 broker_code 作为节点名称查询配置
                node_config = get_node_config(cfg_manager, account.broker_code)
                if not node_config:
                    raise ValueError(f"节点配置不存在: {account.broker_code}")
                
                # 解密敏感信息
                decrypted_app_id = ""
                decrypted_auth_code = ""
                
                if account.app_id:
                    try:
                        decrypted_app_id = service.cipher.decrypt(account.app_id)
                    except Exception as e:
                        logger.warning(f"解密 app_id 失败: {e}")
                        decrypted_app_id = ""
                
                if account.auth_code:
                    try:
                        decrypted_auth_code = service.cipher.decrypt(account.auth_code)
                    except Exception as e:
                        logger.warning(f"解密 auth_code 失败: {e}")
                        decrypted_auth_code = ""
                
                # 构建broker配置（包含行情和交易地址）
                broker_config = {
                    "broker_id": account.broker_id,
                    "user_id": account.account_id,
                    "password": login_data.password,
                    "md_address": node_config.get("md_address"),
                    "td_address": node_config.get("td_address"),
                    "app_id": decrypted_app_id or node_config.get("app_id", ""),
                    "auth_code": decrypted_auth_code or node_config.get("auth_code", ""),
                    "product_info": node_config.get("product_info", ""),
                    "api_type": node_config.get("api_type", "ctp"),
                }
                
                # 构建完整配置
                full_config = {
                    "broker_name": account.broker_code,
                    "broker_config": broker_config
                }
                
                # 设置到TradingCoreService
                core_service = TradingCoreService.get_instance()
                core_service.set_account_broker_config(full_config)
                
                logger.info(f"已设置broker配置到TradingCoreService: broker_code={account.broker_code}, "
                           f"md_address={broker_config.get('md_address')}, "
                           f"td_address={broker_config.get('td_address')}, "
                           f"app_id={'有' if decrypted_app_id else '无'}, "
                           f"auth_code={'有' if decrypted_auth_code else '无'}")
            except Exception as e:
                logger.warning(f"设置broker配置失败（不影响登录）: {e}", exc_info=True)
        
        logger.info(f"用户 {current_user.id} 登录券商账户成功: {account.id}")
        
        return UserBrokerageLoginResponse(
            success=True,
            message="登录成功",
            account=UserBrokerageResponse.from_orm(account),
            token=new_token,
            decrypted_password=decrypted_password
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录券商账户失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )
