#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : add_trading_accounts.py
@Date       : 2025/10/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据库迁移：添加资金账户表
"""
from sqlalchemy import text
from src.web.core.database import engine


async def upgrade():
    """升级数据库"""
    async with engine.begin() as conn:
        # 创建trading_accounts表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trading_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                broker_id VARCHAR(50) NOT NULL,
                account_id VARCHAR(100) NOT NULL,
                encrypted_password VARCHAR(255) NOT NULL,
                display_name VARCHAR(100),
                is_active BOOLEAN DEFAULT 1 NOT NULL,
                is_default BOOLEAN DEFAULT 0 NOT NULL,
                failed_attempts INTEGER DEFAULT 0 NOT NULL,
                locked_until DATETIME,
                last_login DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (user_id, broker_id, account_id)
            )
        """))
        
        # 创建索引
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_trading_accounts_user_id 
            ON trading_accounts(user_id)
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_trading_accounts_is_default 
            ON trading_accounts(user_id, is_default)
        """))
        
        print("✅ 资金账户表创建成功")


async def downgrade():
    """降级数据库"""
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS trading_accounts"))
        print("✅ 资金账户表已删除")


if __name__ == "__main__":
    import asyncio
    asyncio.run(upgrade())

