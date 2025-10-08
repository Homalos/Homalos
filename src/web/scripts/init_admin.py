#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : init_admin.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 初始化管理员账户
"""
import asyncio
from sqlalchemy import select
from src.web.core.database import async_session_maker, init_db
from src.web.models.user import User
from src.web.core.security import get_password_hash
from src.utils.log import get_logger

logger = get_logger(__name__)


async def create_admin_user():
    """创建默认管理员账户"""
    # 先初始化数据库
    await init_db()
    
    async with async_session_maker() as session:
        # 检查是否已存在admin用户
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            logger.info("管理员账户已存在，无需创建")
            print("管理员账户已存在")
            print(f"  用户名: admin")
            return
        
        # 创建管理员账户
        admin_user = User(
            username="admin",
            email="admin@homalos.com",
            full_name="系统管理员",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )
        
        session.add(admin_user)
        await session.commit()
        
        logger.info("管理员账户创建成功")
        print("=" * 60)
        print("管理员账户创建成功！")
        print("=" * 60)
        print(f"  用户名: admin")
        print(f"  密码: admin123")
        print(f"  角色: 管理员")
        print("")
        print("请使用以上账户登录系统，并在首次登录后修改密码！")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(create_admin_user())

