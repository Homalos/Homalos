#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : add_app_id_auth_code_to_trading_accounts.py
@Date       : 2025/10/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据库迁移：添加app_id和auth_code字段到trading_accounts表
"""
from sqlalchemy import text
from src.web.core.database import engine


async def upgrade():
    """升级数据库：添加app_id和auth_code字段"""
    async with engine.begin() as conn:
        # 添加app_id字段
        await conn.execute(text("""
            ALTER TABLE trading_accounts 
            ADD COLUMN app_id VARCHAR(100)
        """))
        
        # 添加auth_code字段
        await conn.execute(text("""
            ALTER TABLE trading_accounts 
            ADD COLUMN auth_code VARCHAR(100)
        """))
        
        print("✅ app_id 和 auth_code 字段添加成功")


async def downgrade():
    """降级数据库：删除app_id和auth_code字段"""
    async with engine.begin() as conn:
        # 注意：SQLite不支持DROP COLUMN，需要重建表
        # 这里仅作为示例，实际使用时需要根据数据库类型选择合适的方法
        await conn.execute(text("""
            ALTER TABLE trading_accounts 
            DROP COLUMN app_id
        """))
        
        await conn.execute(text("""
            ALTER TABLE trading_accounts 
            DROP COLUMN auth_code
        """))
        
        print("✅ app_id 和 auth_code 字段已删除")


if __name__ == "__main__":
    import asyncio
    asyncio.run(upgrade())

