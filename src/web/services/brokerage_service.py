#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : brokerage_service.py
@Date       : 2025/11/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 期货券商账户服务 - 包含加密功能
"""
import base64
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from fastapi import HTTPException, status
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.web.models.brokerage import (
    UserBrokerage, BrokerageAccountSnapshot,
    AccountType, AccountStatus, Environment, ConnectionStatus, UserType
)
from src.utils.log import get_logger

logger = get_logger(__name__)


class AESCipher:
    """AES加密解密工具类"""
    
    def __init__(self, encryption_key: str):
        """
        初始化加密器
        
        Args:
            encryption_key: 加密密钥
        """
        # 使用PBKDF2从密钥派生Fernet密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'homalos_brokerage_salt',  # 生产环境应使用随机盐
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串
        
        Args:
            plaintext: 明文
            
        Returns:
            加密后的字符串（Base64编码）
        """
        if not plaintext:
            return ""
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密字符串
        
        Args:
            ciphertext: 密文（Base64编码）
            
        Returns:
            解密后的明文
        """
        if not ciphertext:
            return ""
        
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise ValueError("解密失败")


class BrokerageService:
    """期货券商账户服务"""
    
    def __init__(self, db: AsyncSession, encryption_key: Optional[str] = None):
        """
        初始化服务
        
        Args:
            db: 数据库会话
            encryption_key: 加密密钥
        """
        self.db = db
        
        # 初始化加密器
        if encryption_key is None:
            # 从环境变量获取加密密钥，生产环境必须设置
            encryption_key = os.getenv('BROKERAGE_ENCRYPTION_KEY', 'default_key_for_development')
            if encryption_key == 'default_key_for_development':
                logger.warning("使用默认加密密钥，生产环境请设置 BROKERAGE_ENCRYPTION_KEY 环境变量")
        
        self.cipher = AESCipher(encryption_key)
    
    async def create_brokerage_account(
        self,
        user_id: int,
        user_type: str,
        account_data: Dict[str, Any]
    ) -> UserBrokerage:
        """
        创建券商账户
        
        Args:
            user_id: 用户ID
            user_type: 用户类型 (user/admin)
            account_data: 账户数据
            
        Returns:
            UserBrokerage: 创建的券商账户
        """
        # 验证文件已加载
        logger.info(f"===== CREATE BROKERAGE START ===== user_type={user_type}")
        logger.info(f"===== account_data keys: {list(account_data.keys())}")
        
        try:
            logger.info("===== STEP 1: 检查账户是否存在")
            # 检查是否已存在相同的资金账号
            existing_account = await self.db.execute(
                select(UserBrokerage).where(
                    and_(
                        UserBrokerage.user_id == user_id,
                        UserBrokerage.account_id == account_data['account_id'],
                        UserBrokerage.broker_code == account_data['broker_code']
                    )
                )
            )
            
            if existing_account.scalar_one_or_none():
                raise ValueError(f"该券商的资金账号 {account_data['account_id']} 已存在")
            
            # 检查是否已存在相同的投资者ID
            existing_investor = await self.db.execute(
                select(UserBrokerage).where(
                    and_(
                        UserBrokerage.user_id == user_id,
                        UserBrokerage.investor_id == account_data['investor_id'],
                        UserBrokerage.broker_code == account_data['broker_code']
                    )
                )
            )
            
            logger.info("===== STEP 2: 检查结果")
            if existing_investor.scalar_one_or_none():
                raise ValueError(f"该券商的投资者ID {account_data['investor_id']} 已存在")
            
            logger.info("===== STEP 3: 处理默认账户")
            # 如果设置为默认账户，先取消其他默认账户
            if account_data.get('is_default', False):
                await self._clear_default_accounts(user_id, user_type)
            
            # 调试：打印 account_data
            logger.info(f"DEBUG - account_data keys: {account_data.keys()}")
            logger.info(f"DEBUG - account_data.get('user_type'): {account_data.get('user_type')}")
            
            # 加密敏感信息
            encrypted_data = account_data.copy()
            
            # 强制移除可能存在的 user_type（防止前端或Schema传递）
            encrypted_data.pop('user_type', None)
            encrypted_data['password_encrypted'] = self.cipher.encrypt(account_data['password'])
            
            if account_data.get('auth_code'):
                encrypted_data['auth_code'] = self.cipher.encrypt(account_data['auth_code'])
            
            if account_data.get('app_id'):
                encrypted_data['app_id'] = self.cipher.encrypt(account_data['app_id'])
            
            # 移除明文密码
            encrypted_data.pop('password', None)
            
            # 设置用户信息
            encrypted_data['user_id'] = user_id
            encrypted_data['user_type'] = user_type
            
            # 转换枚举字段为大写（匹配数据库枚举定义）
            if 'account_type' in encrypted_data and encrypted_data['account_type']:
                encrypted_data['account_type'] = encrypted_data['account_type'].upper()
            if 'status' in encrypted_data and encrypted_data['status']:
                encrypted_data['status'] = encrypted_data['status'].upper()
            
            # 调试：打印最终的 encrypted_data
            logger.info(f"DEBUG - Final user_type: {encrypted_data['user_type']}")
            logger.info(f"DEBUG - user_type parameter: {user_type}")
            logger.info("===== STEP 4: 准备创建 UserBrokerage 对象")
            
            # 创建账户
            logger.info(f"===== CREATING UserBrokerage with user_type={encrypted_data.get('user_type')}")
            brokerage = UserBrokerage(**encrypted_data)
            logger.info("===== UserBrokerage 对象创建成功")
            self.db.add(brokerage)
            await self.db.commit()
            await self.db.refresh(brokerage)
            
            logger.info(f"创建券商账户成功: user_id={user_id}, account_name={brokerage.account_name}")
            
            return brokerage
            
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建券商账户失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建券商账户失败"
            )
    
    async def get_user_brokerages(
        self,
        user_id: int,
        user_type: str = "USER",
        include_inactive: bool = False
    ) -> List[UserBrokerage]:
        """
        获取用户的券商账户列表
        
        Args:
            user_id: 用户ID
            user_type: 用户类型
            include_inactive: 是否包含未激活账户
            
        Returns:
            券商账户列表
        """
        try:
            query = select(UserBrokerage).where(
                and_(
                    UserBrokerage.user_id == user_id,
                    UserBrokerage.user_type == user_type
                )
            )
            
            if not include_inactive:
                query = query.where(UserBrokerage.status == AccountStatus.ACTIVE)
            
            query = query.order_by(UserBrokerage.is_default.desc(), UserBrokerage.created_at.desc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"获取用户券商账户失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取券商账户失败"
            )
    
    async def get_brokerage_by_id(self, brokerage_id: int) -> Optional[UserBrokerage]:
        """
        根据ID获取券商账户
        
        Args:
            brokerage_id: 券商账户ID
            
        Returns:
            券商账户对象或None
        """
        try:
            result = await self.db.execute(
                select(UserBrokerage).where(UserBrokerage.id == brokerage_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取券商账户失败: {e}")
            return None
    
    async def get_decrypted_password(self, brokerage_id: int) -> str:
        """
        获取解密后的交易密码
        
        Args:
            brokerage_id: 券商账户ID
            
        Returns:
            解密后的密码
        """
        brokerage = await self.get_brokerage_by_id(brokerage_id)
        if not brokerage:
            raise ValueError("券商账户不存在")
        
        return self.cipher.decrypt(brokerage.password_encrypted)
    
    async def get_decrypted_auth_code(self, brokerage_id: int) -> Optional[str]:
        """
        获取解密后的认证码
        
        Args:
            brokerage_id: 券商账户ID
            
        Returns:
            解密后的认证码
        """
        brokerage = await self.get_brokerage_by_id(brokerage_id)
        if not brokerage or not brokerage.auth_code:
            return None
        
        return self.cipher.decrypt(brokerage.auth_code)
    
    async def get_decrypted_app_id(self, brokerage_id: int) -> Optional[str]:
        """
        获取解密后的应用ID
        
        Args:
            brokerage_id: 券商账户ID
            
        Returns:
            解密后的应用ID
        """
        brokerage = await self.get_brokerage_by_id(brokerage_id)
        if not brokerage or not brokerage.app_id:
            return None
        
        return self.cipher.decrypt(brokerage.app_id)
    
    async def update_connection_status(
        self,
        brokerage_id: int,
        status: ConnectionStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新连接状态
        
        Args:
            brokerage_id: 券商账户ID
            status: 连接状态
            error_message: 错误信息
            
        Returns:
            是否更新成功
        """
        try:
            update_data = {
                'connection_status': status,
                'updated_at': datetime.utcnow()
            }
            
            if status == ConnectionStatus.CONNECTED:
                update_data['last_connected_at'] = datetime.utcnow()
                update_data['last_error'] = None
            elif status == ConnectionStatus.DISCONNECTED:
                update_data['last_disconnected_at'] = datetime.utcnow()
            elif status == ConnectionStatus.ERROR:
                update_data['last_error'] = error_message
                update_data['last_disconnected_at'] = datetime.utcnow()
            
            await self.db.execute(
                update(UserBrokerage)
                .where(UserBrokerage.id == brokerage_id)
                .values(**update_data)
            )
            
            await self.db.commit()
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新连接状态失败: {e}")
            return False
    
    async def create_account_snapshot(
        self,
        brokerage_id: int,
        snapshot_data: Dict[str, Any]
    ) -> BrokerageAccountSnapshot:
        """
        创建账户资金快照
        
        Args:
            brokerage_id: 券商账户ID
            snapshot_data: 快照数据
            
        Returns:
            创建的快照对象
        """
        try:
            # 检查券商账户是否存在
            brokerage = await self.get_brokerage_by_id(brokerage_id)
            if not brokerage:
                raise ValueError("券商账户不存在")
            
            # 设置快照时间
            if 'snapshot_timestamp' not in snapshot_data:
                snapshot_data['snapshot_timestamp'] = datetime.utcnow()
            
            snapshot_data['user_brokerage_id'] = brokerage_id
            
            # 创建快照
            snapshot = BrokerageAccountSnapshot(**snapshot_data)
            self.db.add(snapshot)
            await self.db.commit()
            await self.db.refresh(snapshot)
            
            logger.info(f"创建资金快照成功: brokerage_id={brokerage_id}, balance={snapshot.balance}")
            
            return snapshot
            
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建资金快照失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建资金快照失败"
            )
    
    async def get_latest_snapshot(self, brokerage_id: int) -> Optional[BrokerageAccountSnapshot]:
        """
        获取最新的资金快照
        
        Args:
            brokerage_id: 券商账户ID
            
        Returns:
            最新的快照对象或None
        """
        try:
            result = await self.db.execute(
                select(BrokerageAccountSnapshot)
                .where(BrokerageAccountSnapshot.user_brokerage_id == brokerage_id)
                .order_by(BrokerageAccountSnapshot.snapshot_timestamp.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取最新资金快照失败: {e}")
            return None
    
    async def _clear_default_accounts(self, user_id: int, user_type: str):
        """
        清除用户的其他默认账户
        
        Args:
            user_id: 用户ID
            user_type: 用户类型
        """
        await self.db.execute(
            update(UserBrokerage)
            .where(
                and_(
                    UserBrokerage.user_id == user_id,
                    UserBrokerage.user_type == user_type,
                    UserBrokerage.is_default == True
                )
            )
            .values(is_default=False, updated_at=datetime.utcnow())
        )
    
    async def set_default_account(self, brokerage_id: int, user_id: int, user_type: str) -> bool:
        """
        设置默认账户
        
        Args:
            brokerage_id: 券商账户ID
            user_id: 用户ID
            user_type: 用户类型
            
        Returns:
            是否设置成功
        """
        try:
            # 先清除其他默认账户
            await self._clear_default_accounts(user_id, user_type)
            
            # 设置新的默认账户
            await self.db.execute(
                update(UserBrokerage)
                .where(UserBrokerage.id == brokerage_id)
                .values(is_default=True, updated_at=datetime.utcnow())
            )
            
            await self.db.commit()
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"设置默认账户失败: {e}")
            return False
    
    async def login_brokerage_account(
        self,
        user_id: int,
        account_id: int,
        password: Optional[str] = None,
        remember: bool = False,
        user_type: str = "USER"
    ) -> UserBrokerage:
        """
        登录券商账户
        
        Args:
            user_id: 用户ID
            account_id: 券商账户ID
            password: 密码（可选，如果账户已记住密码）
            remember: 是否记住密码
            
        Returns:
            UserBrokerage: 登录成功的账户对象
            
        Raises:
            HTTPException: 登录失败
        """
        try:
            # 查询账户（需要同时匹配user_id和user_type）
            result = await self.db.execute(
                select(UserBrokerage).where(
                    and_(
                        UserBrokerage.id == account_id,
                        UserBrokerage.user_id == user_id
                    )
                )
            )
            account = result.scalar_one_or_none()
            
            if not account:
                logger.warning(f"账户不存在或无权访问: user_id={user_id}, user_type={user_type}, account_id={account_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="账户不存在或无权访问"
                )
            
            # 检查账户状态（大小写不敏感）
            logger.info(f"账户状态类型: {type(account.status)}, 值: {account.status}")
            
            # account.status 可能是枚举对象或字符串
            if hasattr(account.status, 'value'):
                account_status = account.status.value.upper()
                logger.info(f"枚举对象，提取值: {account_status}")
            elif isinstance(account.status, str):
                account_status = account.status.upper()
                logger.info(f"字符串类型，转大写: {account_status}")
            else:
                # 可能是枚举类型本身
                account_status = str(account.status).upper()
                logger.info(f"其他类型，转字符串: {account_status}")
            
            target_status = AccountStatus.ACTIVE.value.upper()
            logger.info(f"比较状态: {account_status} vs {target_status}")
            
            if account_status != target_status:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="账户未激活，请先激活账户"
                )
            
            # 检查密码
            password_provided = password and password.strip()
            has_saved_password = account.password_encrypted and account.password_encrypted.strip()
            
            if password_provided:
                # 用户提供了密码，验证密码
                if not has_saved_password:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="账户未设置密码"
                    )
                
                try:
                    decrypted_password = self.cipher.decrypt(account.password_encrypted)
                    if decrypted_password != password:
                        logger.warning(f"密码错误: account_id={account_id}")
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="密码错误"
                        )
                except ValueError:
                    logger.error(f"密码解密失败: account_id={account_id}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="密码验证失败"
                    )
                
                # 如果用户选择记住密码，更新字段
                if remember and not account.remember_password:
                    account.remember_password = True
                    account.updated_at = datetime.utcnow()
                    await self.db.commit()
                    await self.db.refresh(account)
            else:
                # 用户未提供密码
                if not has_saved_password:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="请输入密码"
                    )
                
                if not account.remember_password:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="请输入密码"
                    )
                
                # 免密登录
                logger.info(f"使用已记住密码登录: user_id={user_id}, account_id={account_id}")
            
            # 更新最后连接时间
            account.last_connected_at = datetime.utcnow()
            account.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(account)
            
            logger.info(f"券商账户登录成功: user_id={user_id}, account_id={account_id}")
            return account
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"登录券商账户失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="登录失败"
            )
