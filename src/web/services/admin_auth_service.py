#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : admin_auth_service.py
@Date       : 2025/11/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 管理员认证服务 - 独立的管理员认证逻辑
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from passlib.context import CryptContext

from src.web.models.admin import Admin, AdminStatus, AdminRole, AdminAuditLog
from src.web.schemas.admin import AdminCreate
from src.utils.log import get_logger

logger = get_logger(__name__)


class AdminAuthService:
    """管理员认证服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        
        # 安全策略配置
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 30
        self.password_max_age_days = 90
        self.session_timeout_hours = 8  # 管理员会话超时时间更短
        
        # 超级管理员邀请码（生产环境应从配置文件读取）
        self.super_admin_invitation_code = "HOMALOS_SUPER_ADMIN_2025"
    
    async def register_admin(
        self,
        admin_data: AdminCreate,
        ip_address: str,
        user_agent: str
    ) -> Admin:
        """
        管理员注册
        
        Args:
            admin_data: 管理员注册数据
            ip_address: 注册IP
            user_agent: 用户代理
            
        Returns:
            新创建的管理员对象
        """
        try:
            # 1. 验证邀请码（如果是超级管理员）
            if admin_data.role == "super":
                if not admin_data.invitation_code or admin_data.invitation_code != self.super_admin_invitation_code:
                    await self._log_admin_action(
                        None, "register_attempt", "admin_auth", False, "HIGH",
                        f"Invalid super admin invitation code: {admin_data.invitation_code}",
                        ip_address, user_agent, "无效的超级管理员邀请码"
                    )
                    raise ValueError("无效的超级管理员邀请码")
            
            # 2. 检查用户名是否已存在
            existing_admin = await self._get_admin_by_username_or_email_or_phone(admin_data.username)
            if existing_admin:
                await self._log_admin_action(
                    None, "register_attempt", "admin_auth", False, "MEDIUM",
                    f"Username already exists: {admin_data.username}",
                    ip_address, user_agent, "用户名已存在"
                )
                raise ValueError("用户名已存在")
            
            # 3. 检查邮箱是否已存在
            existing_admin = await self._get_admin_by_username_or_email_or_phone(admin_data.email)
            if existing_admin:
                await self._log_admin_action(
                    None, "register_attempt", "admin_auth", False, "MEDIUM",
                    f"Email already exists: {admin_data.email}",
                    ip_address, user_agent, "邮箱已存在"
                )
                raise ValueError("邮箱已存在")
            
            # 4. 检查手机号是否已存在（如果提供）
            if admin_data.phone:
                existing_admin = await self._get_admin_by_username_or_email_or_phone(admin_data.phone)
                if existing_admin:
                    await self._log_admin_action(
                        None, "register_attempt", "admin_auth", False, "MEDIUM",
                        f"Phone already exists: {admin_data.phone}",
                        ip_address, user_agent, "手机号已存在"
                    )
                    raise ValueError("手机号已存在")
            
            # 5. 创建管理员
            admin_role = AdminRole.SUPER if admin_data.role == "super" else AdminRole.NORMAL
            
            new_admin = Admin(
                username=admin_data.username,
                email=admin_data.email,
                phone=admin_data.phone,
                password_hash=self.pwd_context.hash(admin_data.password),
                role=admin_role,
                status=AdminStatus.ACTIVE,  # 管理员注册后直接激活
                full_name=admin_data.full_name,
                timezone=admin_data.timezone,
                locale=admin_data.locale,
                password_changed_at=datetime.utcnow(),
                mfa_enabled=False  # 初始不启用MFA，建议后续启用
            )
            
            self.db.add(new_admin)
            await self.db.commit()
            await self.db.refresh(new_admin)
            
            # 6. 记录注册成功日志
            await self._log_admin_action(
                new_admin.admin_id, "register", "admin_auth", True, "HIGH",
                f"Admin registered successfully: {new_admin.username} ({new_admin.role.value})",
                ip_address, user_agent
            )
            
            logger.info(f"管理员注册成功: {new_admin.username} ({new_admin.role.value}) from {ip_address}")
            
            return new_admin
            
        except ValueError:
            raise
        except Exception as e:
            error_message = f"管理员注册失败: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            await self._log_admin_action(
                None, "register_attempt", "admin_auth", False, "CRITICAL",
                error_message, ip_address, user_agent, str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="注册服务暂时不可用"
            )
    
    async def authenticate_admin(
        self, 
        username_or_email_or_phone: str, 
        password: str,
        ip_address: str,
        user_agent: str,
        mfa_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        管理员认证
        
        Args:
            username_or_email_or_phone: 用户名、邮箱或手机号
            password: 密码
            ip_address: 登录IP
            user_agent: 用户代理
            mfa_code: MFA验证码（如果启用）
            
        Returns:
            认证结果字典
        """
        admin = None
        success = False
        error_message = ""
        
        try:
            # 1. 查找管理员
            admin = await self._get_admin_by_username_or_email_or_phone(username_or_email_or_phone)
            
            if not admin:
                error_message = "管理员账户不存在"
                await self._log_admin_action(
                    None, "login_attempt", "admin_auth", False, "HIGH",
                    f"Login attempt with non-existent admin: {username_or_email_or_phone}",
                    ip_address, user_agent, error_message
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户名或密码错误"
                )
            
            # 2. 检查账户状态
            if not admin.is_active:
                error_message = f"账户状态异常: {admin.status.name}"
                await self._log_admin_action(
                    admin.admin_id, "login_attempt", "admin_auth", False, "HIGH",
                    f"Login attempt with inactive admin: {admin.status.name}",
                    ip_address, user_agent, error_message
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="账户已被禁用或冻结"
                )
            
            # 3. 检查账户锁定状态
            if admin.is_locked:
                error_message = "账户已被锁定"
                await self._log_admin_action(
                    admin.admin_id, "login_attempt", "admin_auth", False, "MEDIUM",
                    f"Login attempt on locked account until {admin.locked_until}",
                    ip_address, user_agent, error_message
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"账户已被锁定，请等待至 {admin.locked_until.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
            # 4. 验证密码
            if not self.pwd_context.verify(password, admin.password_hash):
                error_message = "密码错误"
                admin.record_failed_login()
                await self.db.commit()
                
                await self._log_admin_action(
                    admin.admin_id, "login_attempt", "admin_auth", False, "HIGH",
                    f"Failed login attempt {admin.failed_login_attempts}/5",
                    ip_address, user_agent, error_message
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户名或密码错误"
                )
            
            # 5. 检查密码是否过期
            if admin.password_expired:
                error_message = "密码已过期"
                await self._log_admin_action(
                    admin.admin_id, "login_attempt", "admin_auth", False, "MEDIUM",
                    "Login attempt with expired password",
                    ip_address, user_agent, error_message
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="密码已过期，请联系系统管理员重置密码"
                )
            
            # 6. 验证MFA（如果启用）
            if admin.requires_mfa:
                if not mfa_code:
                    await self._log_admin_action(
                        admin.admin_id, "login_attempt", "admin_auth", False, "MEDIUM",
                        "Login attempt without MFA code",
                        ip_address, user_agent, "需要MFA验证码"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="需要提供MFA验证码"
                    )
                
                # TODO: 实现MFA验证逻辑
                # if not self._verify_mfa_code(admin.mfa_secret, mfa_code):
                #     raise HTTPException(...)
            
            # 7. 登录成功
            admin.record_successful_login(ip_address)
            await self.db.commit()
            
            success = True
            
            # 记录成功登录
            await self._log_admin_action(
                admin.admin_id, "login", "admin_auth", True, "LOW",
                f"Successful admin login: {admin.username}",
                ip_address, user_agent
            )
            
            logger.info(f"管理员登录成功: {admin.username} from {ip_address}")
            
            return {
                "success": True,
                "admin": {
                    "admin_id": admin.admin_id,
                    "username": admin.username,
                    "email": admin.email,
                    "phone": admin.phone,
                    "full_name": admin.full_name,
                    "role": admin.role.value,
                    "is_super_admin": admin.is_super_admin,
                    "timezone": admin.timezone,
                    "locale": admin.locale,
                    "avatar_url": admin.avatar_url,
                    "email_verified": admin.is_verified,
                    "phone_verified": admin.phone_verified,
                    "mfa_enabled": admin.mfa_enabled,
                    "requires_mfa": admin.requires_mfa,
                    "password_expired": admin.password_expired,
                    "last_login_at": admin.last_login_at.isoformat() if admin.last_login_at else None
                },
                "message": "登录成功"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            error_message = f"认证过程发生错误: {str(e)}"
            logger.error(f"管理员认证失败: {error_message}", exc_info=True)
            
            if admin:
                await self._log_admin_action(
                    admin.admin_id, "login_attempt", "admin_auth", False, "CRITICAL",
                    error_message, ip_address, user_agent, str(e)
                )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="认证服务暂时不可用"
            )
    
    async def change_password(
        self, 
        admin_id: int, 
        old_password: str, 
        new_password: str,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """
        修改管理员密码
        
        Args:
            admin_id: 管理员ID
            old_password: 旧密码
            new_password: 新密码
            ip_address: 操作IP
            user_agent: 用户代理
            
        Returns:
            操作结果
        """
        admin = await self._get_admin_by_id(admin_id)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="管理员不存在"
            )
        
        # 验证旧密码
        if not self.pwd_context.verify(old_password, admin.password_hash):
            await self._log_admin_action(
                admin_id, "change_password", "admin_auth", False, "HIGH",
                "Failed password change: incorrect old password",
                ip_address, user_agent, "旧密码错误"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="旧密码错误"
            )
        
        # 验证新密码强度
        if not self._validate_password_strength(new_password):
            await self._log_admin_action(
                admin_id, "change_password", "admin_auth", False, "MEDIUM",
                "Failed password change: weak password",
                ip_address, user_agent, "密码强度不足"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码强度不足，请使用至少12位包含大小写字母、数字和特殊字符的密码"
            )
        
        # 更新密码
        admin.password_hash = self.pwd_context.hash(new_password)
        admin.password_changed_at = datetime.utcnow()
        
        await self.db.commit()
        
        # 记录密码修改
        await self._log_admin_action(
            admin_id, "change_password", "admin_auth", True, "MEDIUM",
            "Password changed successfully",
            ip_address, user_agent
        )
        
        logger.info(f"管理员密码修改成功: {admin.username}")
        
        return {
            "success": True,
            "message": "密码修改成功"
        }
    
    async def enable_mfa(
        self, 
        admin_id: int, 
        mfa_secret: str,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """启用MFA"""
        admin = await self._get_admin_by_id(admin_id)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="管理员不存在"
            )
        
        # TODO: 加密存储MFA密钥
        admin.mfa_secret = mfa_secret  # 应该加密存储
        admin.mfa_enabled = True
        
        await self.db.commit()
        
        await self._log_admin_action(
            admin_id, "enable_mfa", "admin_auth", True, "MEDIUM",
            "MFA enabled for admin account",
            ip_address, user_agent
        )
        
        return {
            "success": True,
            "message": "MFA启用成功"
        }
    
    async def verify_email(
        self, 
        admin_id: int,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """验证管理员邮箱"""
        admin = await self._get_admin_by_id(admin_id)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="管理员不存在"
            )
        
        admin.email_verified_at = datetime.utcnow()
        await self.db.commit()
        
        await self._log_admin_action(
            admin_id, "verify_email", "admin_auth", True, "MEDIUM",
            "Email verified successfully",
            ip_address, user_agent
        )
        
        return {
            "success": True,
            "message": "邮箱验证成功"
        }
    
    async def verify_phone(
        self, 
        admin_id: int,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """验证管理员手机号"""
        admin = await self._get_admin_by_id(admin_id)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="管理员不存在"
            )
        
        admin.phone_verified_at = datetime.utcnow()
        await self.db.commit()
        
        await self._log_admin_action(
            admin_id, "verify_phone", "admin_auth", True, "MEDIUM",
            "Phone verified successfully",
            ip_address, user_agent
        )
        
        return {
            "success": True,
            "message": "手机号验证成功"
        }
    
    async def update_profile(
        self,
        admin_id: int,
        full_name: Optional[str] = None,
        timezone: Optional[str] = None,
        locale: Optional[str] = None,
        avatar_url: Optional[str] = None,
        ip_address: str = "",
        user_agent: str = ""
    ) -> Dict[str, Any]:
        """更新管理员个人资料"""
        admin = await self._get_admin_by_id(admin_id)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="管理员不存在"
            )
        
        changes = []
        if full_name is not None:
            admin.full_name = full_name
            changes.append(f"full_name: {full_name}")
        
        if timezone is not None:
            admin.timezone = timezone
            changes.append(f"timezone: {timezone}")
        
        if locale is not None:
            admin.locale = locale
            changes.append(f"locale: {locale}")
        
        if avatar_url is not None:
            admin.avatar_url = avatar_url
            changes.append(f"avatar_url: {avatar_url}")
        
        await self.db.commit()
        
        await self._log_admin_action(
            admin_id, "update_profile", "admin_auth", True, "LOW",
            f"Profile updated: {', '.join(changes)}",
            ip_address, user_agent
        )
        
        return {
            "success": True,
            "message": "个人资料更新成功",
            "changes": changes
        }
    
    async def _get_admin_by_username_or_email_or_phone(self, username_or_email_or_phone: str) -> Optional[Admin]:
        """根据用户名、邮箱或手机号查找管理员"""
        result = await self.db.execute(
            select(Admin).where(
                (Admin.username == username_or_email_or_phone) | 
                (Admin.email == username_or_email_or_phone) |
                (Admin.phone == username_or_email_or_phone)
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_admin_by_id(self, admin_id: int) -> Optional[Admin]:
        """根据ID查找管理员"""
        result = await self.db.execute(
            select(Admin).where(Admin.admin_id == admin_id)
        )
        return result.scalar_one_or_none()
    
    def _validate_password_strength(self, password: str) -> bool:
        """验证密码强度"""
        if len(password) < 12:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return all([has_upper, has_lower, has_digit, has_special])
    
    async def _log_admin_action(
        self,
        admin_id: Optional[int],
        action: str,
        resource: str,
        success: bool,
        risk_level: str,
        details: str,
        ip_address: str,
        user_agent: str,
        error_message: Optional[str] = None
    ):
        """记录管理员操作日志"""
        try:
            log_entry = AdminAuditLog(
                admin_id=admin_id,
                action=action,
                resource=resource,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message,
                risk_level=risk_level,
                details=details
            )
            
            self.db.add(log_entry)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"记录管理员审计日志失败: {e}", exc_info=True)
    
    async def get_admin_audit_logs(
        self,
        admin_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """获取管理员审计日志"""
        query = select(AdminAuditLog)
        
        # 添加过滤条件
        if admin_id:
            query = query.where(AdminAuditLog.admin_id == admin_id)
        if action:
            query = query.where(AdminAuditLog.action == action)
        if start_date:
            query = query.where(AdminAuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AdminAuditLog.created_at <= end_date)
        
        # 排序和分页
        query = query.order_by(AdminAuditLog.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return {
            "logs": [log.to_dict() for log in logs],
            "total": len(logs),
            "offset": offset,
            "limit": limit
        }
