#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : user_service.py
@Date       : 2025/11/16
@Author     : Cascade AI
@Description: 用户管理服务
"""
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from src.web.models.user import User, UserStatus, UserRole
from src.web.models.admin import Admin, AdminStatus, AdminRole
from src.web.models.user_preference import UserPreference
from src.web.schemas.user import UserCreateByAdmin, UserUpdateByAdmin
from src.utils.log import get_logger

logger = get_logger(__name__)

# 密码加密上下文 (使用argon2替代bcrypt以避免Windows兼容性问题)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class UserService:
    """用户管理服务"""
    
    @staticmethod
    async def get_users_list(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        role: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """
        获取用户列表（分页、搜索、筛选）
        
        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            search: 搜索关键词（用户名、邮箱、手机号）
            status: 状态筛选
            role: 角色筛选
            
        Returns:
            (用户列表, 总数)
        """
        # 构建查询
        query = select(User)
        
        # 搜索条件
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.username.like(search_pattern),
                    User.email.like(search_pattern),
                    User.phone.like(search_pattern),
                    User.full_name.like(search_pattern)
                )
            )
        
        # 状态筛选
        if status:
            try:
                status_enum = UserStatus[status.upper()]
                query = query.where(User.status == status_enum)
            except KeyError:
                logger.warning(f"无效的状态值: {status}")
        
        # 角色筛选
        if role:
            try:
                role_enum = UserRole[role.upper()]
                query = query.where(User.role == role_enum)
            except KeyError:
                logger.warning(f"无效的角色值: {role}")
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar()
        
        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # 排序
        query = query.order_by(User.created_at.desc())
        
        # 执行查询
        result = await db.execute(query)
        users = result.scalars().all()
        
        return list(users), total
    
    @staticmethod
    async def get_all_users_list(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        role: Optional[str] = None,
        user_type: Optional[str] = None
    ) -> Tuple[List[dict], int]:
        """
        获取所有用户列表（合并users和admins表）
        
        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            search: 搜索关键词
            status: 状态筛选
            role: 角色筛选
            user_type: 用户类型筛选 (user/admin)
            
        Returns:
            (用户列表, 总数)
        """
        all_users = []
        
        # 查询普通用户
        if not user_type or user_type == 'user':
            users_query = select(User)
            
            if search:
                search_pattern = f"%{search}%"
                users_query = users_query.where(
                    or_(
                        User.username.like(search_pattern),
                        User.email.like(search_pattern),
                        User.phone.like(search_pattern),
                        User.full_name.like(search_pattern)
                    )
                )
            
            if status:
                try:
                    status_enum = UserStatus[status.upper()]
                    users_query = users_query.where(User.status == status_enum)
                except KeyError:
                    pass
            
            if role:
                try:
                    role_enum = UserRole[role.upper()]
                    users_query = users_query.where(User.role == role_enum)
                except KeyError:
                    pass
            
            users_query = users_query.order_by(User.created_at.desc())
            result = await db.execute(users_query)
            users = result.scalars().all()
            
            for user in users:
                all_users.append({
                    'id': user.user_id,
                    'user_type': 'user',
                    'username': user.username,
                    'email': user.email,
                    'phone': user.phone,
                    'full_name': user.full_name,
                    'status': user.status.name.lower() if user.status else None,
                    'role': user.role.name.lower() if user.role else None,
                    'created_at': user.created_at,
                    'last_login_at': user.last_login_at,
                    'avatar_url': user.avatar_url
                })
        
        # 查询管理员用户
        if not user_type or user_type == 'admin':
            admins_query = select(Admin)
            
            if search:
                search_pattern = f"%{search}%"
                admins_query = admins_query.where(
                    or_(
                        Admin.username.like(search_pattern),
                        Admin.email.like(search_pattern),
                        Admin.phone.like(search_pattern),
                        Admin.full_name.like(search_pattern)
                    )
                )
            
            if status:
                try:
                    status_enum = AdminStatus[status.upper()]
                    admins_query = admins_query.where(Admin.status == status_enum)
                except KeyError:
                    pass
            
            if role:
                try:
                    role_enum = AdminRole[role.upper()]
                    admins_query = admins_query.where(Admin.role == role_enum)
                except KeyError:
                    pass
            
            admins_query = admins_query.order_by(Admin.created_at.desc())
            result = await db.execute(admins_query)
            admins = result.scalars().all()
            
            for admin in admins:
                all_users.append({
                    'id': admin.admin_id,
                    'user_type': 'admin',
                    'username': admin.username,
                    'email': admin.email,
                    'phone': admin.phone,
                    'full_name': admin.full_name,
                    'status': admin.status.name.lower() if admin.status else None,
                    'role': admin.role.name.lower() if admin.role else None,
                    'created_at': admin.created_at,
                    'last_login_at': admin.last_login_at,
                    'avatar_url': admin.avatar_url
                })
        
        # 按创建时间排序
        all_users.sort(key=lambda x: x['created_at'] if x['created_at'] else '', reverse=True)
        
        # 总数
        total = len(all_users)
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        paginated_users = all_users[start:end]
        
        return paginated_users, total
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        result = await db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreateByAdmin):
        """
        创建用户或管理员
        
        Args:
            db: 数据库会话
            user_data: 用户数据
            
        Returns:
            创建的用户或管理员对象
            
        Raises:
            ValueError: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在（在users和admins表中都检查）
        existing_user = await UserService.get_user_by_username(db, user_data.username)
        if existing_user:
            raise ValueError(f"用户名 '{user_data.username}' 已存在")
        
        # 检查admins表中是否存在
        result = await db.execute(select(Admin).where(Admin.username == user_data.username))
        existing_admin = result.scalar_one_or_none()
        if existing_admin:
            raise ValueError(f"用户名 '{user_data.username}' 已存在")
        
        # 检查邮箱是否已存在（在users和admins表中都检查）
        existing_email = await UserService.get_user_by_email(db, user_data.email)
        if existing_email:
            raise ValueError(f"邮箱 '{user_data.email}' 已被使用")
        
        result = await db.execute(select(Admin).where(Admin.email == user_data.email))
        existing_admin_email = result.scalar_one_or_none()
        if existing_admin_email:
            raise ValueError(f"邮箱 '{user_data.email}' 已被使用")
        
        # 加密密码
        password_hash = pwd_context.hash(user_data.password)
        
        # 判断角色，如果是admin则创建到admins表
        if user_data.role.upper() == 'ADMIN':
            # 创建管理员（普通管理员，不是超级管理员）
            try:
                status_enum = AdminStatus[user_data.status.upper()]
            except KeyError:
                status_enum = AdminStatus.ACTIVE
            
            admin = Admin(
                username=user_data.username,
                email=user_data.email,
                password_hash=password_hash,
                phone=user_data.phone,
                full_name=user_data.full_name,
                status=status_enum,
                role=AdminRole.NORMAL,  # 固定为普通管理员
                timezone=user_data.timezone,
                locale=user_data.locale,
                mfa_enabled=False
            )
            
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            
            # 为管理员创建默认的偏好设置
            admin_preference = UserPreference(
                user_id=admin.admin_id,
                user_type='admin',  # 标识为管理员
                theme='light',
                language=user_data.locale if user_data.locale else 'zh-CN',
                default_order_type='limit',
                default_time_in_force='GTC'
            )
            db.add(admin_preference)
            await db.commit()
            
            logger.info(f"创建普通管理员成功: {admin.username} (ID: {admin.admin_id}), 已创建默认偏好设置")
            return admin
        
        else:
            # 创建普通用户
            try:
                status_enum = UserStatus[user_data.status.upper()]
            except KeyError:
                status_enum = UserStatus.ACTIVE
            
            user = User(
                username=user_data.username,
                email=user_data.email,
                password_hash=password_hash,
                phone=user_data.phone,
                full_name=user_data.full_name,
                status=status_enum,
                role=UserRole.NORMAL,  # 固定为普通用户
                timezone=user_data.timezone,
                locale=user_data.locale
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # 自动创建默认的用户偏好设置
            user_preference = UserPreference(
                user_id=user.user_id,
                user_type='user',  # 标识为普通用户
                theme='light',
                language=user_data.locale if user_data.locale else 'zh-CN',
                default_order_type='limit',
                default_time_in_force='GTC'
            )
            db.add(user_preference)
            await db.commit()
            
            logger.info(f"创建用户成功: {user.username} (ID: {user.user_id}), 已创建默认偏好设置")
            
            return user
    
    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: int,
        user_data: UserUpdateByAdmin
    ) -> Optional[User]:
        """
        更新用户信息
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            user_data: 更新数据
            
        Returns:
            更新后的用户对象，如果用户不存在则返回None
            
        Raises:
            ValueError: 邮箱已被其他用户使用
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None
        
        # 检查邮箱是否被其他用户使用
        if user_data.email and user_data.email != user.email:
            existing_email = await UserService.get_user_by_email(db, user_data.email)
            if existing_email and existing_email.user_id != user_id:
                raise ValueError(f"邮箱 '{user_data.email}' 已被其他用户使用")
        
        # 更新字段
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"更新用户信息: {user.username} (ID: {user.user_id})")
        
        return user
    
    @staticmethod
    async def update_user_status(
        db: AsyncSession,
        user_id: int,
        status: str
    ) -> Optional[User]:
        """
        更新用户状态
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            status: 新状态
            
        Returns:
            更新后的用户对象
            
        Raises:
            ValueError: 无效的状态值
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None
        
        try:
            status_enum = UserStatus[status.upper()]
        except KeyError:
            raise ValueError(f"无效的状态值: {status}")
        
        user.status = status_enum
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"更新用户状态: {user.username} -> {status}")
        
        return user
    
    @staticmethod
    async def update_user_role(
        db: AsyncSession,
        user_id: int,
        role: str
    ) -> Optional[User]:
        """
        更新用户角色
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            role: 新角色
            
        Returns:
            更新后的用户对象
            
        Raises:
            ValueError: 无效的角色值
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None
        
        try:
            role_enum = UserRole[role.upper()]
        except KeyError:
            raise ValueError(f"无效的角色值: {role}")
        
        user.role = role_enum
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"更新用户角色: {user.username} -> {role}")
        
        return user
    
    @staticmethod
    async def reset_user_password(
        db: AsyncSession,
        user_id: int,
        new_password: str
    ) -> Optional[User]:
        """
        重置用户密码
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            new_password: 新密码
            
        Returns:
            更新后的用户对象
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None
        
        # 加密新密码
        password_hash = pwd_context.hash(new_password)
        user.password_hash = password_hash
        
        # 更新密码修改时间
        from datetime import datetime
        user.password_changed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"重置用户密码: {user.username} (ID: {user.user_id})")
        
        return user
    
    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> bool:
        """
        删除用户
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            是否删除成功
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return False
        
        username = user.username
        
        await db.delete(user)
        await db.commit()
        
        logger.info(f"删除用户: {username} (ID: {user_id})")
        
        return True
