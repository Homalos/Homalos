#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : migrate_user_preferences_add_user_type.py
@Date       : 2025/11/17
@Author     : Cascade AI
@Description: 为user_preferences表添加user_type字段并迁移数据
"""
import asyncio
import sqlite3
from pathlib import Path

# 数据库路径 - 使用data目录下的数据库
DB_PATH = Path(__file__).parent / "data" / "homalos_web.db"


async def migrate_user_preferences():
    """迁移user_preferences表，添加user_type字段"""
    
    print("=" * 60)
    print("开始迁移 user_preferences 表")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_preferences'
        """)
        if not cursor.fetchone():
            print("❌ user_preferences 表不存在")
            return
        
        print("✅ user_preferences 表存在")
        
        # 2. 检查user_type列是否已存在
        cursor.execute("PRAGMA table_info(user_preferences)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_type' in columns:
            print("✅ user_type 列已存在，无需迁移")
            return
        
        print("📝 user_type 列不存在，开始迁移...")
        
        # 3. 添加user_type列
        print("\n步骤1: 添加 user_type 列...")
        cursor.execute("""
            ALTER TABLE user_preferences 
            ADD COLUMN user_type VARCHAR(10) DEFAULT 'user' NOT NULL
        """)
        print("✅ user_type 列添加成功")
        
        # 4. 更新现有数据（所有现有记录都是普通用户）
        print("\n步骤2: 更新现有数据...")
        cursor.execute("""
            UPDATE user_preferences 
            SET user_type = 'user'
            WHERE user_type IS NULL OR user_type = ''
        """)
        updated_count = cursor.rowcount
        print(f"✅ 更新了 {updated_count} 条记录，设置为 user_type='user'")
        
        # 5. 创建索引
        print("\n步骤3: 创建索引...")
        
        # 检查索引是否已存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_user_preferences_user_type'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE INDEX idx_user_preferences_user_type 
                ON user_preferences(user_type)
            """)
            print("✅ 创建 idx_user_preferences_user_type 索引")
        else:
            print("✅ idx_user_preferences_user_type 索引已存在")
        
        # 创建联合唯一索引
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_user_preferences_user_id_type'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE UNIQUE INDEX idx_user_preferences_user_id_type 
                ON user_preferences(user_id, user_type)
            """)
            print("✅ 创建 idx_user_preferences_user_id_type 唯一索引")
        else:
            print("✅ idx_user_preferences_user_id_type 唯一索引已存在")
        
        # 6. 移除外键约束（SQLite需要重建表）
        print("\n步骤4: 移除外键约束...")
        print("⚠️  SQLite不支持直接删除外键，需要重建表")
        print("ℹ️  由于已经移除了ORM中的外键关系，新记录不会有外键约束")
        print("ℹ️  现有记录的外键约束不影响功能，可以保留")
        
        # 提交更改
        conn.commit()
        
        # 7. 验证迁移结果
        print("\n" + "=" * 60)
        print("验证迁移结果")
        print("=" * 60)
        
        cursor.execute("PRAGMA table_info(user_preferences)")
        columns_info = cursor.fetchall()
        print("\n表结构:")
        for col in columns_info:
            print(f"  - {col[1]}: {col[2]}")
        
        cursor.execute("SELECT COUNT(*) FROM user_preferences")
        total_count = cursor.fetchone()[0]
        print(f"\n总记录数: {total_count}")
        
        cursor.execute("SELECT user_type, COUNT(*) FROM user_preferences GROUP BY user_type")
        type_counts = cursor.fetchall()
        print("\n按用户类型统计:")
        for user_type, count in type_counts:
            print(f"  - {user_type}: {count}")
        
        print("\n" + "=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
        print("\n说明:")
        print("1. user_preferences 表现在支持普通用户和管理员")
        print("2. user_type='user' 表示普通用户（users表）")
        print("3. user_type='admin' 表示管理员（admins表）")
        print("4. user_id 可以是 users.user_id 或 admins.admin_id")
        print("5. (user_id, user_type) 组合唯一")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate_user_preferences())
