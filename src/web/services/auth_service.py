#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : auth_service.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 认证业务逻辑服务
"""
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.web.models.user import User
from src.web.schemas.user import UserCreate
from src.web.schemas.token import Token
from src.web.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from src.utils.log import get_logger

logger = get_logger(__name__)


class AuthService:
    """认证服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, user_data: UserCreate) -> User:
        """
        用户注册
        
        Args:
            user_data: 用户创建数据
            
        Returns:
            User: 创建的用户对象
            
        Raises:
            HTTPException: 用户名或邮箱已存在
        """
        # 检查用户名是否存在
        result = await self.db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )

        # 检查邮箱是否存在
        if user_data.email:
            result = await self.db.execute(
                select(User).where(User.email == user_data.email)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被使用"
                )

        # 创建新用户
        user = User(
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            full_name=user_data.full_name,
            password_hash=get_password_hash(user_data.password),
            timezone=user_data.timezone,
            locale=user_data.locale,
            avatar_url=user_data.avatar_url
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"新用户注册成功: {user.username}")
        return user

    async def login(self, username: str, password: str) -> Token:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Token: 访问令牌
            
        Raises:
            HTTPException: 用户名或密码错误
        """
        # 查询用户
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        # 验证用户和密码
        if not user or not verify_password(password, user.password_hash):
            logger.warning(f"登录失败: 用户名或密码错误 - {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查用户是否被禁用
        if not user.is_active:
            logger.warning(f"登录失败: 用户已被禁用 - {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )

        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        await self.db.commit()

        # 生成访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )

        logger.info(f"用户登录成功: {username}")
        return Token(access_token=access_token, token_type="bearer")

    async def verify_reset_credentials(self, username: str, email: str) -> bool:
        """
        验证密码重置凭据（用户名和邮箱匹配）
        
        Args:
            username: 用户名
            email: 注册邮箱
            
        Returns:
            bool: 验证是否成功
            
        Raises:
            HTTPException: 验证失败
        """
        # 查询用户
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        # 用户不存在或未绑定邮箱
        if not user:
            logger.warning(f"密码重置失败: 用户不存在 - {username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名或邮箱不匹配"
            )
        
        if not user.email:
            logger.warning(f"密码重置失败: 用户未绑定邮箱 - {username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该账户未绑定邮箱，请联系管理员重置密码"
            )

        # 验证邮箱是否匹配
        if user.email.lower() != email.lower():
            logger.warning(f"密码重置失败: 邮箱不匹配 - {username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名或邮箱不匹配"
            )

        # 检查用户是否被禁用
        if not user.is_active:
            logger.warning(f"密码重置失败: 用户已被禁用 - {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用，无法重置密码"
            )

        logger.info(f"密码重置验证成功: {username}")
        return True

    async def reset_password(self, username: str, email: str, new_password: str) -> None:
        """
        重置用户密码
        
        Args:
            username: 用户名
            email: 注册邮箱
            new_password: 新密码
            
        Raises:
            HTTPException: 重置失败
        """
        # 再次验证凭据（安全考虑）
        await self.verify_reset_credentials(username, email)

        # 查询用户
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名或邮箱不匹配"
            )

        # 更新密码
        user.hashed_password = get_password_hash(new_password)
        await self.db.commit()

        logger.info(f"密码重置成功: {username}")


