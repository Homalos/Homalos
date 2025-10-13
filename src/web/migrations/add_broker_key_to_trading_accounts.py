#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : add_broker_key_to_trading_accounts.py
@Date       : 2025/10/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据库迁移：添加broker_key字段到trading_accounts表
"""
from sqlalchemy import text
from src.web.core.database import engine


async def upgrade():
    """升级数据库：添加broker_key字段"""
    async with engine.begin() as conn:
        # 添加broker_key字段（设置默认值为空字符串）
        await conn.execute(text("""
            ALTER TABLE trading_accounts 
            ADD COLUMN broker_key VARCHAR(50) NOT NULL DEFAULT ''
        """))
        
        print("✅ broker_key字段添加成功")


async def downgrade():
    """降级数据库：删除broker_key字段"""
    async with engine.begin() as conn:
        # 注意：SQLite不支持DROP COLUMN，需要重建表
        # 这里仅作为示例，实际使用时需要根据数据库类型选择合适的方法
        await conn.execute(text("""
            ALTER TABLE trading_accounts 
            DROP COLUMN broker_key
        """))
        
        print("✅ broker_key字段已删除")


if __name__ == "__main__":
    import asyncio
    asyncio.run(upgrade())

