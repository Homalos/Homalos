#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : users.py
@Date       : 2025/11/16
@Author     : Cascade AI
@Description: 用户管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.core.database import get_db
from src.web.core.security import get_current_user
from src.web.models.user import User
from src.web.models.admin import Admin, AdminRole
from src.web.schemas.user import (
    UserListResponse,
    UserListItem,
    UserDetailResponse,
    UserCreateByAdmin,
    UserUpdateByAdmin,
    UserStatusUpdate,
    UserRoleUpdate,
    UserPasswordReset
)
from src.web.services.user_service import UserService
from src.utils.log import get_logger

router = APIRouter(prefix="/users", tags=["用户管理"])
logger = get_logger(__name__)


def check_admin_permission(current_user):
    """检查管理员权限"""
    # 如果是Admin对象，直接允许
    if isinstance(current_user, Admin):
        return
    
    # 如果是User对象，检查is_admin属性
    if isinstance(current_user, User):
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            return
    
    # 否则拒绝访问
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="需要管理员权限才能管理用户"
    )


@router.get("", response_model=UserListResponse, summary="获取用户列表")
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str = Query(None, description="搜索关键词"),
    status: str = Query(None, description="状态筛选"),
    role: str = Query(None, description="角色筛选"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户列表
    
    - **需要管理员权限**
    - 支持分页、搜索、筛选
    - 搜索范围：用户名、邮箱、手机号、全名
    """
    check_admin_permission(current_user)
    
    try:
        users, total = await UserService.get_users_list(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            role=role
        )
        
        # 转换为响应格式
        user_items = []
        for user in users:
            user_items.append(UserListItem(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                phone=user.phone,
                full_name=user.full_name,
                status=user.status.name.lower(),
                role=user.role.name.lower(),
                email_verified=user.email_verified,
                phone_verified=user.phone_verified,
                created_at=user.created_at,
                last_login_at=user.last_login_at
            ))
        
        return UserListResponse(
            total=total,
            page=page,
            page_size=page_size,
            users=user_items
        )
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户列表失败: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserDetailResponse, summary="获取用户详情")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户详情
    
    - **需要管理员权限**
    """
    check_admin_permission(current_user)
    
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户不存在 (ID: {user_id})"
        )
    
    return UserDetailResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        timezone=user.timezone,
        locale=user.locale,
        status=user.status.name.lower(),
        role=user.role.name.lower(),
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        mfa_enabled=user.mfa_enabled,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        failed_login_attempts=user.failed_login_attempts,
        locked_until=user.locked_until,
        password_changed_at=user.password_changed_at
    )


@router.post("", response_model=UserDetailResponse, summary="创建用户")
async def create_user(
    user_data: UserCreateByAdmin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新用户
    
    - **需要管理员权限**
    """
    check_admin_permission(current_user)
    
    try:
        user = await UserService.create_user(db, user_data)
        
        return UserDetailResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            timezone=user.timezone,
            locale=user.locale,
            status=user.status.name.lower(),
            role=user.role.name.lower(),
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            mfa_enabled=user.mfa_enabled,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            password_changed_at=user.password_changed_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建用户失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建用户失败: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserDetailResponse, summary="更新用户信息")
async def update_user(
    user_id: int,
    user_data: UserUpdateByAdmin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户信息
    
    - **需要管理员权限**
    """
    check_admin_permission(current_user)
    
    try:
        user = await UserService.update_user(db, user_id, user_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户不存在 (ID: {user_id})"
            )
        
        return UserDetailResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            timezone=user.timezone,
            locale=user.locale,
            status=user.status.name.lower(),
            role=user.role.name.lower(),
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            mfa_enabled=user.mfa_enabled,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            password_changed_at=user.password_changed_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新用户失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户失败: {str(e)}"
        )


@router.put("/{user_id}/status", response_model=UserDetailResponse, summary="更新用户状态")
async def update_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户状态
    
    - **需要管理员权限**
    - 状态：inactive/active/frozen/disabled
    """
    check_admin_permission(current_user)
    
    try:
        user = await UserService.update_user_status(db, user_id, status_data.status)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户不存在 (ID: {user_id})"
            )
        
        return UserDetailResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            timezone=user.timezone,
            locale=user.locale,
            status=user.status.name.lower(),
            role=user.role.name.lower(),
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            mfa_enabled=user.mfa_enabled,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            password_changed_at=user.password_changed_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新用户状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户状态失败: {str(e)}"
        )


@router.put("/{user_id}/role", response_model=UserDetailResponse, summary="更新用户角色")
async def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户角色
    
    - **需要管理员权限**
    - 角色：normal/admin
    """
    check_admin_permission(current_user)
    
    try:
        user = await UserService.update_user_role(db, user_id, role_data.role)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户不存在 (ID: {user_id})"
            )
        
        return UserDetailResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            timezone=user.timezone,
            locale=user.locale,
            status=user.status.name.lower(),
            role=user.role.name.lower(),
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            mfa_enabled=user.mfa_enabled,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            password_changed_at=user.password_changed_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新用户角色失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户角色失败: {str(e)}"
        )


@router.put("/{user_id}/password", response_model=dict, summary="重置用户密码")
async def reset_user_password(
    user_id: int,
    password_data: UserPasswordReset,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    重置用户密码
    
    - **需要管理员权限**
    """
    check_admin_permission(current_user)
    
    try:
        user = await UserService.reset_user_password(db, user_id, password_data.new_password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户不存在 (ID: {user_id})"
            )
        
        return {
            "success": True,
            "message": f"用户 {user.username} 的密码已重置"
        }
        
    except Exception as e:
        logger.error(f"重置用户密码失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置用户密码失败: {str(e)}"
        )


@router.delete("/{user_id}", response_model=dict, summary="删除用户")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除用户
    
    - **需要管理员权限**
    - 注意：此操作不可逆
    """
    check_admin_permission(current_user)
    
    # 防止删除自己
    if isinstance(current_user, User) and current_user.user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )
    
    success = await UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户不存在 (ID: {user_id})"
        )
    
    return {
        "success": True,
        "message": f"用户已删除 (ID: {user_id})"
    }


@router.get("/all/list", summary="获取所有用户列表（含管理员）")
async def get_all_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str = Query(None, description="搜索关键词"),
    status: str = Query(None, description="状态筛选"),
    role: str = Query(None, description="角色筛选"),
    user_type: str = Query(None, description="用户类型筛选 (user/admin)"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有用户列表（合并users和admins表）
    
    - **仅超级管理员可用**
    - 合并显示普通用户和管理员用户
    - 支持按用户类型筛选
    """
    # 检查管理员权限
    check_admin_permission(current_user)
    
    # 检查是否为超级管理员
    if isinstance(current_user, Admin):
        if current_user.role != AdminRole.SUPER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有超级管理员才能查看所有用户"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有超级管理员才能查看所有用户"
        )
    
    try:
        users, total = await UserService.get_all_users_list(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            role=role,
            user_type=user_type
        )
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "users": users
        }
        
    except Exception as e:
        logger.error(f"获取所有用户列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取所有用户列表失败: {str(e)}"
        )
