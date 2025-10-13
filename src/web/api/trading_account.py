#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_account.py
@Date       : 2025/10/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 资金账户API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.core.database import get_db
from src.web.core.security import get_current_user, create_access_token
from src.web.models.user import User
from src.web.schemas.trading_account import (
    TradingAccountCreate,
    TradingAccountUpdate,
    TradingAccountPasswordUpdate,
    TradingAccountLogin,
    TradingAccountResponse,
    TradingAccountStatus,
    TradingAccountListResponse,
    BrokerInfo
)
from src.web.services.trading_auth_service import TradingAuthService
from src.web.services.broker_service import BrokerService
from src.utils.log import get_logger
from datetime import timedelta

logger = get_logger(__name__)

router = APIRouter(prefix="/trading-account", tags=["资金账户"])


@router.post("/login", summary="登录资金账户")
async def login_trading_account(
    login_data: TradingAccountLogin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    资金账户登录
    
    两种登录方式：
    1. 使用已有账户ID登录（account_id）
    2. 使用券商ID+资金账号登录（broker_id + account_number）
       - 如果账户不存在，自动创建账户后登录
    
    Returns:
        {
            "success": True,
            "message": "登录成功",
            "account": TradingAccountResponse,
            "token": "new_jwt_token"  # 包含资金账户信息的新Token
        }
    """
    service = TradingAuthService(db)
    
    try:
        account = await service.login(
            user_id=current_user.id,
            account_id=login_data.account_id,
            broker_key=login_data.broker_key,
            broker_id=login_data.broker_id,
            account_number=login_data.account_number,
            password=login_data.password
        )
        
        # 生成新Token（包含资金账户信息）
        token_data = {
            "sub": current_user.username,
            "role": current_user.role,
            "trading_account": {
                "id": account.id,
                "broker_key": account.broker_key,
                "broker_id": account.broker_id,
                "account_id": account.account_id,
                "display_name": account.display_name
            }
        }
        
        access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(hours=24)
        )
        
        return {
            "success": True,
            "message": "登录成功",
            "account": TradingAccountResponse.model_validate(account),
            "token": access_token
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"资金账户登录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )


@router.post("/logout", summary="登出资金账户")
async def logout_trading_account(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    登出资金账户
    
    清除Token中的资金账户信息，返回新Token
    """
    # 生成新Token（不包含资金账户信息）
    token_data = {
        "sub": current_user.username,
        "role": current_user.role
    }
    
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(hours=24)
    )
    
    return {
        "success": True,
        "message": "已退出资金账户",
        "token": access_token
    }


@router.get("/status", response_model=TradingAccountStatus, summary="获取登录状态")
async def get_trading_account_status(
    current_user: User = Depends(get_current_user)
) -> TradingAccountStatus:
    """
    获取资金账户登录状态
    
    从Token中解析资金账户信息
    """
    # 这里需要从request中获取Token并解析
    # 简化处理：返回未登录状态
    return TradingAccountStatus(is_logged_in=False)


@router.get("/list", response_model=TradingAccountListResponse, summary="获取账户列表")
async def get_account_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TradingAccountListResponse:
    """
    获取当前用户的所有资金账户
    """
    service = TradingAuthService(db)
    accounts = await service.get_account_list(current_user.id)
    
    return TradingAccountListResponse(
        accounts=[TradingAccountResponse.model_validate(acc) for acc in accounts],
        total=len(accounts)
    )


@router.post("", response_model=TradingAccountResponse, summary="添加资金账户")
async def add_account(
    account_data: TradingAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TradingAccountResponse:
    """
    添加新的资金账户
    """
    service = TradingAuthService(db)
    account = await service.add_account(
        user_id=current_user.id,
        broker_key=account_data.broker_key,
        broker_id=account_data.broker_id,
        account_id=account_data.account_id,
        password=account_data.password,
        display_name=account_data.display_name,
        is_default=account_data.is_default
    )
    
    return TradingAccountResponse.model_validate(account)


@router.put("/{account_id}", response_model=TradingAccountResponse, summary="更新账户信息")
async def update_account(
    account_id: int,
    account_data: TradingAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TradingAccountResponse:
    """
    更新资金账户信息
    """
    service = TradingAuthService(db)
    account = await service.update_account(
        user_id=current_user.id,
        account_id=account_id,
        display_name=account_data.display_name,
        is_active=account_data.is_active
    )
    
    return TradingAccountResponse.model_validate(account)


@router.delete("/{account_id}", summary="删除账户")
async def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    删除资金账户
    """
    service = TradingAuthService(db)
    await service.delete_account(current_user.id, account_id)
    
    return {
        "success": True,
        "message": "账户已删除"
    }


@router.post("/{account_id}/switch", response_model=TradingAccountResponse, summary="切换账户")
async def switch_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TradingAccountResponse:
    """
    切换默认账户
    """
    service = TradingAuthService(db)
    account = await service.switch_account(current_user.id, account_id)
    
    return TradingAccountResponse.model_validate(account)


@router.put("/{account_id}/password", summary="修改密码")
async def change_password(
    account_id: int,
    password_data: TradingAccountPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    修改资金账户密码
    """
    service = TradingAuthService(db)
    await service.change_password(
        user_id=current_user.id,
        account_id=account_id,
        old_password=password_data.old_password,
        new_password=password_data.new_password
    )
    
    return {
        "success": True,
        "message": "密码修改成功"
    }


@router.get("/brokers", response_model=list[BrokerInfo], summary="获取券商列表")
async def get_brokers(
    current_user: User = Depends(get_current_user)
) -> list[BrokerInfo]:
    """
    获取可用的券商列表
    
    从 brokers.yaml 配置文件读取
    """
    brokers = BrokerService.get_broker_list()
    return [BrokerInfo(**broker) for broker in brokers]

