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
from src.web.core.security import (
    get_current_user,
    get_current_user_with_trading_account,
    create_access_token
)
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
from src.web.services.trading_core_service import TradingCoreService
from src.common import build_broker_config_from_account
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
    
    # 记录登录请求数据
    logger.info(f"登录请求数据: account_id={login_data.account_id}, broker_key={login_data.broker_key}, broker_id={login_data.broker_id}, account_number={login_data.account_number}")
    
    try:
        account = await service.login(
            user_id=current_user.id,  # type: ignore
            account_id=login_data.account_id,
            broker_key=login_data.broker_key,
            broker_id=login_data.broker_id,
            account_number=login_data.account_number,
            password=login_data.password,
            remember=login_data.remember
        )
        
        # 如果用户提供了密码，构建broker配置并设置到TradingCoreService
        logger.info(f"检查密码状态: password={'有密码' if login_data.password and login_data.password.strip() else '无密码或空密码'}")
        
        if login_data.password and login_data.password.strip():
            try:
                logger.info("开始构建broker配置...")
                
                account_data = {
                    "broker_id": account.broker_id,
                    "account_id": account.account_id,
                    "app_id": account.app_id,
                    "auth_code": account.auth_code,
                    "md_node_name": account.md_node_name,
                    "td_node_name": account.td_node_name,
                    "broker_key": account.broker_key
                }
                
                logger.info(f"账户数据: broker_id={account.broker_id}, account_id={account.account_id}, broker_key={account.broker_key}, app_id='{account.app_id}', auth_code='{account.auth_code}'")
                
                broker_config = build_broker_config_from_account(
                    account_data=account_data,
                    decrypted_password=login_data.password
                )
                
                logger.info(f"broker配置构建成功: broker_name={broker_config.get('broker_name')}")
                
                # 设置到TradingCoreService（用于后续连接网关）
                core_service = TradingCoreService.get_instance()
                core_service.set_account_broker_config(broker_config)
                
                # 验证设置结果
                has_config = core_service.has_broker_config()
                logger.info(f"已设置账户broker配置到TradingCoreService: account_id={account.id}, 验证结果={has_config}")
                
            except Exception as e:
                # 构建配置失败不影响登录，只记录警告
                logger.warning(f"构建broker配置失败（不影响登录）: {e}", exc_info=True)
        else:
            logger.info("免密登录，未构建broker配置（需要时用户需重新输入密码）")
        
        # 生成新Token（包含资金账户信息）
        # 处理role字段 - 可能是枚举或字符串
        role_value = current_user.role
        if hasattr(role_value, 'value'):
            # 如果是枚举，获取其值
            role_value = role_value.value
        
        token_data = {
            "sub": current_user.username,
            "role": role_value,
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
    user_data: tuple = Depends(get_current_user_with_trading_account),
    db: AsyncSession = Depends(get_db)
) -> TradingAccountStatus:
    """
    获取资金账户登录状态
    
    从Token中解析资金账户信息并验证有效性
    """
    current_user, trading_account_data = user_data
    
    # 如果JWT中没有资金账户信息，返回未登录状态
    if not trading_account_data:
        return TradingAccountStatus(
            is_logged_in=False,
            account_id=None,
            broker_id=None,
            account_number=None,
            display_name=None
        )
    
    try:
        # 验证资金账户是否仍然有效
        service = TradingAuthService(db)
        account = await service._get_account_by_id(
            current_user.id, 
            trading_account_data.get("id")
        )
        
        # 检查账户是否存在且激活
        if account and account.is_active:
            # 检查TradingCoreService是否有完整的broker配置
            from src.web.services.trading_core_service import TradingCoreService
            core_service = TradingCoreService.get_instance()
            has_broker_config = core_service.has_broker_config()
            
            return TradingAccountStatus(
                is_logged_in=True,
                account_id=account.id,  # type: ignore
                broker_id=account.broker_id,  # type: ignore
                account_number=account.account_id,  # type: ignore
                display_name=account.display_name,  # type: ignore
                has_broker_config=has_broker_config
            )
        else:
            # 账户不存在或已被禁用
            return TradingAccountStatus(
                is_logged_in=False,
                account_id=None,
                broker_id=None,
                account_number=None,
                display_name=None,
                has_broker_config=False
            )
            
    except Exception:
        # 发生错误时返回未登录状态
        return TradingAccountStatus(
            is_logged_in=False,
            account_id=None,
            broker_id=None,
            account_number=None,
            display_name=None,
            has_broker_config=False
        )


@router.get("/list", response_model=TradingAccountListResponse, summary="获取账户列表")
async def get_account_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TradingAccountListResponse:
    """
    获取当前用户的所有资金账户
    """
    # 处理管理员用户 - 管理员没有资金账户
    from src.web.models.admin import Admin
    if isinstance(current_user, Admin):
        return TradingAccountListResponse(
            accounts=[],
            total=0
        )
    
    service = TradingAuthService(db)
    accounts = await service.get_account_list(current_user.id)  # type: ignore
    
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
        user_id=current_user.id,  # type: ignore
        broker_key=account_data.broker_key,
        broker_id=account_data.broker_id,
        account_id=account_data.account_id,
        password=account_data.password,
        app_id=account_data.app_id,
        auth_code=account_data.auth_code,
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
        user_id=current_user.id,  # type: ignore
        account_id=account_id,
        display_name=account_data.display_name,
        is_active=account_data.is_active
    )
    
    return TradingAccountResponse.model_validate(account)


@router.delete("/{account_id}", summary="删除账户")
async def delete_account(
    account_id: int,
    user_data: tuple = Depends(get_current_user_with_trading_account),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    删除资金账户
    
    注意：
    - 无法删除当前登录的账户
    - 如果交易核心正在运行，建议先停止再删除
    """
    current_user, trading_account_data = user_data
    
    # 获取当前登录的资金账户ID
    current_account_id = None
    if trading_account_data:
        current_account_id = trading_account_data.get("id")
    
    service = TradingAuthService(db)
    await service.delete_account(
        current_user.id,  # type: ignore
        account_id,
        current_account_id=current_account_id
    )
    
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
    account = await service.switch_account(current_user.id, account_id)  # type: ignore
    
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
    await service.change_password(  # type: ignore
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

