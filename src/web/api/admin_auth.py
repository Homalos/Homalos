#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : admin_auth.py
@Date       : 2025/11/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 管理员认证相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.core.database import get_db
from src.web.schemas.admin import (
    AdminCreate, AdminResponse, AdminLogin, AdminPasswordChange,
    AdminProfileUpdate, AdminVerificationRequest
)
from src.web.schemas.token import Token
from src.web.services.admin_auth_service import AdminAuthService
from src.web.models.admin import Admin

router = APIRouter(prefix="/admin/auth", tags=["管理员认证"])


@router.post("/register", response_model=AdminResponse, summary="管理员注册")
async def register_admin(
    admin: AdminCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> AdminResponse:
    """
    管理员注册（需要邀请码或超级管理员权限）
    
    - **username**: 管理员用户名（3-50字符）
    - **email**: 邮箱地址（必填）
    - **phone**: 手机号（可选）
    - **password**: 密码（至少12位，包含大小写字母、数字和特殊字符）
    - **confirm_password**: 确认密码
    - **full_name**: 真实姓名（可选）
    - **role**: 角色（normal/super）
    - **invitation_code**: 邀请码（创建超级管理员时需要）
    """
    auth_service = AdminAuthService(db)
    
    # 获取客户端IP和User-Agent
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    try:
        new_admin = await auth_service.register_admin(
            admin_data=admin,
            ip_address=client_ip,
            user_agent=user_agent
        )
        return AdminResponse.from_admin_model(new_admin)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token, summary="管理员登录")
async def login_admin(
    login_data: AdminLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    管理员登录
    
    - **username_or_email_or_phone**: 用户名、邮箱或手机号
    - **password**: 密码
    - **mfa_code**: MFA验证码（如果启用）
    
    返回JWT访问令牌
    """
    auth_service = AdminAuthService(db)
    
    # 获取客户端IP和User-Agent
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    result = await auth_service.authenticate_admin(
        username_or_email_or_phone=login_data.username_or_email_or_phone,
        password=login_data.password,
        ip_address=client_ip,
        user_agent=user_agent,
        mfa_code=login_data.mfa_code
    )
    
    if result["success"]:
        # TODO: 生成JWT token
        return Token(
            access_token="admin_jwt_token_here",
            token_type="bearer",
            expires_in=28800  # 8小时
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败"
        )


@router.post("/change-password", summary="修改管理员密码")
async def change_admin_password(
    password_data: AdminPasswordChange,
    request: Request,
    db: AsyncSession = Depends(get_db),
    # current_admin: Admin = Depends(get_current_admin)  # TODO: 实现管理员认证依赖
):
    """
    修改管理员密码
    
    - **old_password**: 旧密码
    - **new_password**: 新密码（至少12位，包含大小写字母、数字和特殊字符）
    - **confirm_password**: 确认新密码
    """
    auth_service = AdminAuthService(db)
    
    # 获取客户端IP和User-Agent
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    # TODO: 从认证中获取admin_id
    admin_id = 1  # 临时硬编码
    
    result = await auth_service.change_password(
        admin_id=admin_id,
        old_password=password_data.old_password,
        new_password=password_data.new_password,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return result


@router.post("/verify-email", summary="验证管理员邮箱")
async def verify_admin_email(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # current_admin: Admin = Depends(get_current_admin)  # TODO: 实现管理员认证依赖
):
    """
    验证管理员邮箱
    """
    auth_service = AdminAuthService(db)
    
    # 获取客户端IP和User-Agent
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    # TODO: 从认证中获取admin_id
    admin_id = 1  # 临时硬编码
    
    result = await auth_service.verify_email(
        admin_id=admin_id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return result


@router.post("/verify-phone", summary="验证管理员手机号")
async def verify_admin_phone(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # current_admin: Admin = Depends(get_current_admin)  # TODO: 实现管理员认证依赖
):
    """
    验证管理员手机号
    """
    auth_service = AdminAuthService(db)
    
    # 获取客户端IP和User-Agent
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    # TODO: 从认证中获取admin_id
    admin_id = 1  # 临时硬编码
    
    result = await auth_service.verify_phone(
        admin_id=admin_id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return result


@router.put("/profile", summary="更新管理员个人资料")
async def update_admin_profile(
    profile_data: AdminProfileUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    # current_admin: Admin = Depends(get_current_admin)  # TODO: 实现管理员认证依赖
):
    """
    更新管理员个人资料
    
    - **full_name**: 真实姓名
    - **timezone**: 时区
    - **locale**: 语言偏好
    - **avatar_url**: 头像URL
    """
    auth_service = AdminAuthService(db)
    
    # 获取客户端IP和User-Agent
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    # TODO: 从认证中获取admin_id
    admin_id = 1  # 临时硬编码
    
    result = await auth_service.update_profile(
        admin_id=admin_id,
        full_name=profile_data.full_name,
        timezone=profile_data.timezone,
        locale=profile_data.locale,
        avatar_url=profile_data.avatar_url,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return result


@router.get("/me", response_model=AdminResponse, summary="获取当前管理员信息")
async def get_current_admin_info(
    # current_admin: Admin = Depends(get_current_admin)  # TODO: 实现管理员认证依赖
):
    """
    获取当前登录管理员的信息
    
    需要在请求头中提供有效的JWT令牌：
    ```
    Authorization: Bearer <access_token>
    ```
    """
    # TODO: 实现获取当前管理员信息
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="功能开发中"
    )


@router.post("/logout", summary="管理员登出")
async def logout_admin(
    # current_admin: Admin = Depends(get_current_admin)  # TODO: 实现管理员认证依赖
):
    """
    管理员登出
    
    前端需要删除本地存储的token
    """
    return {"message": "登出成功"}
