#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : reset_admin_password.py
@Date       : 2025/11/14
@Author     : Cascade
@Description: 重置管理员密码（admins表）
"""
import asyncio
import argparse
from sqlalchemy import select
from passlib.context import CryptContext
from src.web.core.database import async_session_maker, init_db
from src.web.models.admin import Admin, AdminStatus, AdminRole
from src.utils.log import get_logger

logger = get_logger(__name__)


async def reset_admin_password(username: str, new_password: str):
    """重置或创建管理员的密码"""
    # 先初始化数据库
    await init_db()
    
    # 创建密码哈希上下文（与AdminAuthService保持一致）
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

    async with async_session_maker() as session:
        # 检查管理员是否存在于 admins 表
        result = await session.execute(
            select(Admin).where(Admin.username == username)
        )
        admin = result.scalar_one_or_none()

        new_hashed_password = pwd_context.hash(new_password)

        if admin:
            # 如果管理员存在，更新密码
            admin.password_hash = new_hashed_password
            admin.status = AdminStatus.ACTIVE  # 确保账户是激活状态
            admin.failed_login_attempts = 0  # 重置失败次数
            admin.locked_until = None  # 解锁账户
            await session.commit()
            
            logger.info(f"管理员 '{username}' 的密码已成功重置。")
            print("=" * 60)
            print(f"管理员 '{username}' 的密码已成功更新！")
            print("=" * 60)
        else:
            # 如果管理员不存在，创建一个新的管理员账户
            new_admin = Admin(
                username=username,
                email=f"{username}@homalos.com",
                full_name="系统管理员",
                password_hash=new_hashed_password,
                role=AdminRole.SUPER,  # 默认创建超级管理员
                status=AdminStatus.ACTIVE  # 直接设置为激活状态
            )
            session.add(new_admin)
            await session.commit()
            
            logger.info(f"管理员 '{username}' 不存在，已创建为新的超级管理员账户。")
            print("=" * 60)
            print(f"超级管理员账户 '{username}' 创建成功！")
            print("=" * 60)

        print(f"  用户名: {username}")
        print(f"  新密码: {new_password}")
        print(f"  表名: admins")
        print("\n请使用新凭据登录管理后台。")
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="重置或创建管理员密码（admins表）")
    parser.add_argument("-u", "--username", type=str, required=True, help="要重置密码的管理员用户名")
    parser.add_argument("-p", "--password", type=str, required=True, help="管理员的新密码")
    args = parser.parse_args()

    asyncio.run(reset_admin_password(args.username, args.password))

