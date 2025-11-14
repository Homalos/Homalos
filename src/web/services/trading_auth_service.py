#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_auth_service.py
@Date       : 2025/10/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 资金账户认证服务
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.web.models.trading_account import TradingAccount
from src.web.core.security import verify_password, get_password_hash
from src.web.services.broker_service import BrokerService
from src.utils.log import get_logger

logger = get_logger(__name__)

# 安全配置
MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 15


class TradingAuthService:
    """资金账户认证服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def login(
        self, 
        user_id: int, 
        account_id: Optional[int], 
        broker_key: Optional[str],
        broker_id: Optional[str],
        account_number: Optional[str],
        password: str,
        remember: bool = False
    ) -> TradingAccount:
        """
        资金账户登录
        
        支持两种登录方式：
        1. 使用已有账户ID登录（account_id）
        2. 使用券商配置key+资金账号登录（broker_key + account_number）
           - 如果账户不存在，自动创建账户后登录
        
        Args:
            user_id: Web用户ID
            account_id: 已有账户ID（可选）
            broker_key: 券商配置key（新账户必填）
            broker_id: 券商ID（新账户可选，如果未提供则从broker_key查询）
            account_number: 资金账号（新账户必填）
            password: 密码
            
        Returns:
            TradingAccount: 登录成功的账户对象
            
        Raises:
            HTTPException: 登录失败
        """
        # 查询账户
        if account_id:
            # 使用已有账户ID登录
            account = await self._get_account_by_id(user_id, account_id)
            if not account:
                logger.warning(f"账户不存在: user_id={user_id}, account_id={account_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="账户不存在"
                )
        else:
            # 使用券商key和账号登录
            if not broker_key or not account_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="请提供券商配置和资金账号"
                )
            
            # 如果未提供broker_id，从BrokerService查询
            if not broker_id:
                broker_config = BrokerService.get_broker_config(broker_key)
                if not broker_config:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"未找到券商配置: {broker_key}"
                    )
                broker_id = broker_config.get('broker_id', '')
                if not broker_id:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"券商配置缺少broker_id: {broker_key}"
                    )
            
            account = await self._get_account_by_credentials(user_id, broker_id, account_number)
            
            # 如果账户不存在，自动创建
            if not account:
                logger.info(f"账户不存在，自动创建: user_id={user_id}, broker_key={broker_key}, account_id={account_number}")
                try:
                    account = await self.add_account(
                        user_id=user_id,
                        broker_key=broker_key,
                        broker_id=broker_id,
                        account_id=account_number,
                        password=password,
                        app_id=None,  # 使用默认值
                        auth_code=None,  # 使用默认值
                        display_name=f"{broker_key}_{broker_id}",
                        is_default=False
                    )
                    logger.info(f"账户创建成功，继续登录: account_id={account.id}")
                except HTTPException as e:
                    # 如果是账户已存在错误（可能是并发创建），重新查询
                    if e.status_code == 409:
                        account = await self._get_account_by_credentials(user_id, broker_id, account_number)
                        if account:
                            logger.warning(f"账户已存在（并发创建）: account_id={account.id}")
                        else:
                            logger.error("并发创建后仍无法找到账户")
                            raise e
                    else:
                        logger.error(f"创建账户失败: {e.detail}")
                        raise e
        
        # 检查账户状态
        if not account.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用"
            )
        
        # 检查锁定状态
        if account.locked_until and account.locked_until > datetime.now(timezone.utc):
            remaining = (account.locked_until - datetime.now(timezone.utc)).seconds // 60
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"账户已锁定，请在 {remaining} 分钟后重试"
            )
        
        # 验证密码
        # 检查密码是否为空
        password_is_empty = not password or password.strip() == ''
        
        # 如果密码为空但账户未记住密码，则报错
        if password_is_empty and not account.remember_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请输入密码"
            )
        
        # 如果账户已记住密码且未提供新密码，则跳过验证（免密登录）
        skip_password_verification = account.remember_password and password_is_empty
        
        if not skip_password_verification:
            # 需要验证密码
            if not verify_password(password, account.encrypted_password):  # type: ignore
                # 记录失败次数
                account.failed_attempts += 1  # type: ignore
                
                # 达到最大次数则锁定
                if account.failed_attempts >= MAX_FAILED_ATTEMPTS:
                    account.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCK_DURATION_MINUTES)  # type: ignore
                    await self.db.commit()
                    logger.warning(f"账户已锁定: {account.account_id}, 失败次数: {account.failed_attempts}")
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail=f"密码错误次数过多，账户已锁定 {LOCK_DURATION_MINUTES} 分钟"
                    )
                
                await self.db.commit()
                remaining_attempts = MAX_FAILED_ATTEMPTS - account.failed_attempts
                logger.warning(f"密码错误: {account.account_id}, 剩余尝试次数: {remaining_attempts}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"密码错误，剩余尝试次数: {remaining_attempts}"
                )
        else:
            logger.info(f"使用已记住密码登录: user_id={user_id}, account_id={account.id}")
        
        # 登录成功，重置失败次数
        account.failed_attempts = 0  # type: ignore
        account.locked_until = None  # type: ignore
        account.last_login = datetime.now(timezone.utc)  # type: ignore
        account.remember_password = remember  # type: ignore
        await self.db.commit()
        await self.db.refresh(account)
        
        logger.info(f"资金账户登录成功: user_id={user_id}, account_id={account.id}, remember={remember}")
        return account
    
    async def add_account(
        self,
        user_id: int,
        broker_key: str,
        broker_id: str,
        account_id: str,
        password: str,
        app_id: Optional[str] = None,
        auth_code: Optional[str] = None,
        display_name: Optional[str] = None,
        is_default: bool = False
    ) -> TradingAccount:
        """添加新账户"""
        # 添加详细日志
        logger.info(f"检查账户是否存在: user_id={user_id}, broker_id={broker_id}, account_id={account_id}")
        
        # 检查是否已存在
        existing = await self._get_account_by_credentials(user_id, broker_id, account_id)
        
        if existing:
            logger.warning(f"账户已存在: id={existing.id}, user_id={existing.user_id}, broker_id={existing.broker_id}, account_id={existing.account_id}")
        else:
            logger.info(f"账户不存在，可以创建")
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该账户已存在"
            )
        
        # 如果未提供app_id/auth_code，从BrokerService获取默认值
        if not app_id or not auth_code:
            broker_config = BrokerService.get_broker_config(broker_key)
            if not app_id:
                app_id = broker_config.get('app_id', '')
            if not auth_code:
                auth_code = broker_config.get('auth_code', '')
        
        # 如果设为默认，取消其他默认账户
        if is_default:
            await self._clear_default_accounts(user_id)
        
        # 创建账户
        account = TradingAccount(
            user_id=user_id,
            broker_key=broker_key,
            broker_id=broker_id,
            account_id=account_id,
            encrypted_password=get_password_hash(password),
            app_id=app_id,
            auth_code=auth_code,
            md_node_name=broker_key,  # 使用broker_key作为节点名称
            td_node_name=broker_key,  # 使用broker_key作为节点名称
            display_name=display_name or f"{broker_key}_{broker_id}",
            is_default=is_default
        )
        
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        
        logger.info(f"添加资金账户: user_id={user_id}, broker_key={broker_key}, account_id={account.id}")
        return account
    
    async def get_account_list(self, user_id: int) -> list[TradingAccount]:
        """获取用户的所有账户"""
        result = await self.db.execute(
            select(TradingAccount)
            .where(TradingAccount.user_id == user_id)
            .order_by(TradingAccount.is_default.desc(), TradingAccount.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def update_account(
        self,
        user_id: int,
        account_id: int,
        display_name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> TradingAccount:
        """更新账户信息"""
        account = await self._get_account_by_id(user_id, account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="账户不存在"
            )
        
        if display_name is not None:
            account.display_name = display_name  # type: ignore
        if is_active is not None:
            account.is_active = is_active  # type: ignore
        
        account.updated_at = datetime.now(timezone.utc)  # type: ignore
        await self.db.commit()
        await self.db.refresh(account)
        
        return account
    
    async def delete_account(
        self, 
        user_id: int, 
        account_id: int,
        current_account_id: Optional[int] = None
    ) -> None:
        """
        删除账户
        
        Args:
            user_id: 用户ID
            account_id: 要删除的账户ID
            current_account_id: 当前登录的账户ID（可选）
        
        Raises:
            HTTPException: 账户不存在或无法删除
        """
        account = await self._get_account_by_id(user_id, account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="账户不存在"
            )
        
        # 检查是否是当前登录的账户
        if current_account_id and account_id == current_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法删除当前登录的账户，请先切换到其他账户或退出登录"
            )
        
        await self.db.delete(account)
        await self.db.commit()
        logger.info(f"删除资金账户: user_id={user_id}, account_id={account_id}")
    
    async def switch_account(self, user_id: int, account_id: int) -> TradingAccount:
        """切换默认账户"""
        # 取消所有默认
        await self._clear_default_accounts(user_id)
        
        # 设置新默认
        account = await self._get_account_by_id(user_id, account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="账户不存在"
            )
        
        account.is_default = True  # type: ignore
        await self.db.commit()
        await self.db.refresh(account)
        
        logger.info(f"切换默认账户: user_id={user_id}, account_id={account_id}")
        return account
    
    async def change_password(
        self,
        user_id: int,
        account_id: int,
        old_password: str,
        new_password: str
    ) -> None:
        """修改密码"""
        account = await self._get_account_by_id(user_id, account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="账户不存在"
            )
        
        # 验证旧密码
        if not verify_password(old_password, account.encrypted_password):  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="旧密码错误"
            )
        
        # 更新密码
        account.encrypted_password = get_password_hash(new_password)  # type: ignore
        account.updated_at = datetime.now(timezone.utc)  # type: ignore
        await self.db.commit()
        
        logger.info(f"修改账户密码: user_id={user_id}, account_id={account_id}")
    
    # ===== 私有方法 =====
    
    async def _get_account_by_id(self, user_id: int, account_id: int) -> Optional[TradingAccount]:
        """通过ID查询账户"""
        result = await self.db.execute(
            select(TradingAccount).where(
                and_(
                    TradingAccount.id == account_id,
                    TradingAccount.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_account_by_credentials(
        self,
        user_id: int,
        broker_id: str,
        account_id: str
    ) -> Optional[TradingAccount]:
        """通过券商和账号查询"""
        result = await self.db.execute(
            select(TradingAccount).where(
                and_(
                    TradingAccount.user_id == user_id,
                    TradingAccount.broker_id == broker_id,
                    TradingAccount.account_id == account_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _clear_default_accounts(self, user_id: int) -> None:
        """清除所有默认账户标记"""
        result = await self.db.execute(
            select(TradingAccount).where(
                and_(
                    TradingAccount.user_id == user_id,
                    TradingAccount.is_default.is_(True)
                )
            )
        )
        accounts = result.scalars().all()
        for account in accounts:
            account.is_default = False  # type: ignore
        await self.db.commit()

