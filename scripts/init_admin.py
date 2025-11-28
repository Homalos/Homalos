#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : init_admin_migration.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 初始化迁移管理员账户
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from sqlalchemy import select
from passlib.context import CryptContext
from src.web.core.database import async_session_maker, init_db
from src.web.models.admin import Admin, AdminStatus, AdminRole
from src.utils.log import get_logger

logger = get_logger(__name__)

# 密码上下文
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


async def init_admin_migration():
    """初始化或重置管理员账户"""
    try:
        # 初始化数据库
        await init_db()
        logger.info("数据库初始化完成")
        
        # 获取数据库会话
        async with async_session_maker() as db:
            # 查询是否存在 admin 账户
            result = await db.execute(
                select(Admin).where(Admin.username == "admin")
            )
            admin = result.scalar_one_or_none()
            
            if admin:
                # 重置密码和角色
                logger.info("找到 admin 账户，重置密码和角色...")
                admin.password_hash = pwd_context.hash("Admin@123456")
                admin.password_changed_at = datetime.utcnow()  # 重置密码修改时间
                admin.status = AdminStatus.ACTIVE
                admin.role = AdminRole.SUPER
                admin.failed_login_attempts = 0
                admin.locked_until = None
                await db.commit()
                logger.info("✅ admin 账户已更新为超级管理员，密码: Admin@123456")
            else:
                # 创建新账户
                logger.info("admin 账户不存在，创建新账户...")
                new_admin = Admin(
                    username="admin",
                    email="admin@homalos.com",
                    password_hash=pwd_context.hash("Admin@123456"),
                    password_changed_at=datetime.utcnow(),  # 设置密码修改时间
                    role=AdminRole.SUPER,
                    status=AdminStatus.ACTIVE,
                    full_name="系统管理员",
                    timezone="Asia/Shanghai",
                    locale="zh-CN",
                    mfa_enabled=False
                )
                db.add(new_admin)
                await db.commit()
                logger.info("✅ admin 账户已创建为超级管理员，密码: Admin@123456")
        
        logger.info("=" * 60)
        logger.info("管理员账户初始化完成")
        logger.info("=" * 60)
        logger.info("账户信息:")
        logger.info("  用户名: admin")
        logger.info("  密码: Admin@123456")
        logger.info("  邮箱: admin@homalos.com")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("初始化管理员账户失败: " + str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_admin_migration())
