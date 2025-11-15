#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : auth.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 认证相关API路由
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.core.database import get_db
from src.web.core.security import get_current_user
from src.web.schemas.user import UserCreate, UserResponse, PasswordResetRequest, PasswordResetConfirm
from src.web.schemas.token import Token
from src.web.services.auth_service import AuthService
from src.web.models.user import User
from src.utils.log import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    用户注册
    
    - **username**: 用户名（3-50字符）
    - **password**: 密码（6-50字符）
    - **email**: 邮箱（可选）
    - **full_name**: 全名（可选）
    """
    logger.info(f"收到注册请求: username={user.username}, email={user.email}")
    auth_service = AuthService(db)
    new_user = await auth_service.register(user)
    return UserResponse.model_validate(new_user)


@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    用户登录（OAuth2密码模式）
    
    - **username**: 用户名
    - **password**: 密码
    
    返回JWT访问令牌
    """
    auth_service = AuthService(db)
    return await auth_service.login(form_data.username, form_data.password)


@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户的信息
    
    需要在请求头中提供有效的JWT令牌：
    ```
    Authorization: Bearer <access_token>
    ```
    
    返回值根据用户类型而不同：
    - 普通用户: UserResponse
    - 管理员: AdminResponse
    """
    from src.web.models.admin import Admin
    from src.web.schemas.admin import AdminResponse
    
    # 如果是管理员，返回AdminResponse
    if isinstance(current_user, Admin):
        return AdminResponse.from_admin_model(current_user)
    
    # 否则返回UserResponse
    return UserResponse.model_validate(current_user)


@router.post("/logout", summary="用户登出")
async def logout(current_user: User = Depends(get_current_user)):
    """
    用户登出
    
    前端需要删除本地存储的token
    """
    return {"message": "登出成功"}


@router.post("/password-reset/verify", summary="验证密码重置凭据")
async def verify_password_reset(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    验证密码重置凭据（第一步：验证用户名和邮箱）
    
    - **username**: 用户名
    - **email**: 注册邮箱
    
    验证成功后，前端可进入第二步设置新密码
    """
    auth_service = AuthService(db)
    await auth_service.verify_reset_credentials(reset_request.username, reset_request.email)
    return {"message": "验证成功，请设置新密码"}


@router.post("/password-reset/confirm", summary="确认重置密码")
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    确认重置密码（第二步：设置新密码）
    
    - **username**: 用户名
    - **email**: 注册邮箱
    - **new_password**: 新密码（6-50字符）
    
    重置成功后，用户可使用新密码登录
    """
    auth_service = AuthService(db)
    await auth_service.reset_password(
        reset_confirm.username,
        reset_confirm.email,
        reset_confirm.new_password
    )
    return {"message": "密码重置成功，请使用新密码登录"}

