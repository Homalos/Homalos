#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : security.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 安全认证模块（JWT、密码加密）
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.core.database import get_db
from src.web.models.user import User
from src.web.models.admin import Admin

# JWT配置
SECRET_KEY = "homalos-secret-key-change-in-production-2025"  # 生产环境必须更改
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# 密码加密上下文 (使用argon2替代bcrypt以避免Windows兼容性问题)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2认证方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 加密后的密码
        
    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    获取密码哈希值
    
    Args:
        password: 明文密码
        
    Returns:
        str: 加密后的密码
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        
    Returns:
        str: JWT令牌
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User | Admin:
    """
    获取当前用户或管理员（支持两种认证）
    
    Args:
        token: JWT令牌
        db: 数据库会话
        
    Returns:
        User | Admin: 当前用户或管理员对象
        
    Raises:
        HTTPException: 认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 解码JWT令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        admin_id: int = payload.get("admin_id")
        
        if username is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # 如果token中包含admin_id，则查询管理员
    if admin_id:
        result = await db.execute(
            select(Admin).where(Admin.admin_id == admin_id)
        )
        admin = result.scalar_one_or_none()
        
        if admin is None:
            raise credentials_exception
        
        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="管理员账户已被禁用"
            )
        
        return admin
    
    # 否则查询普通用户
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    return user


async def get_current_user_with_trading_account(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, Optional[dict]]:
    """
    获取当前用户和资金账户信息（依赖注入）
    
    Args:
        token: JWT令牌
        db: 数据库会话
        
    Returns:
        tuple: (用户对象, 资金账户信息字典或None)
        
    Raises:
        HTTPException: 认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 解码JWT令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
        # 获取资金账户信息（如果存在）
        trading_account_data = payload.get("trading_account")
            
    except JWTError:
        raise credentials_exception
    
    # 从数据库查询用户
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    return user, trading_account_data


async def get_current_active_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前管理员用户（依赖注入）
    
    Args:
        current_user: 当前用户
        
    Returns:
        User: 管理员用户对象
        
    Raises:
        HTTPException: 权限不足
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    
    return current_user

