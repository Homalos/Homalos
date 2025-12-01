#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速同步策略到数据库
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from src.web.core.database import async_session_maker, init_db
from src.web.models.strategy import Strategy, StrategyStatus


async def quick_sync():
    """快速同步策略到数据库"""
    print("=" * 60)
    print("开始同步策略到数据库")
    print("=" * 60)
    
    # 初始化数据库
    await init_db()
    print("✓ 数据库初始化完成")
    
    # 读取策略注册表
    registry_path = Path("src/strategy/strategy_registry.json")
    if not registry_path.exists():
        print(f"✗ 策略注册表不存在: {registry_path}")
        return
    
    with open(registry_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    
    print(f"✓ 找到 {len(registry)} 个策略")
    print()
    
    # 获取数据库会话
    async with async_session_maker() as db:
        synced_count = 0
        skipped_count = 0
        
        for module_path, config in registry.items():
            try:
                # 检查策略是否已存在
                result = await db.execute(
                    select(Strategy).where(Strategy.module_path == module_path)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"  ⊙ 策略已存在: {config.get('name')} (ID: {existing.strategy_id})")
                    skipped_count += 1
                    continue
                
                # 创建新策略
                strategy = Strategy(
                    admin_id=1,  # 使用管理员ID=1
                    uuid=config.get('uuid'),
                    name=config.get('name', module_path.split('.')[-1]),
                    description=config.get('description', ''),
                    author=config.get('author', ''),
                    file_path=config.get('file', ''),
                    module_path=module_path,
                    class_name=config.get('class', 'Strategy'),
                    instruments=config.get('instruments', []),
                    parameters=config.get('params', {}),
                    status=StrategyStatus.ACTIVE,
                    enabled=config.get('enabled', True)
                )
                
                db.add(strategy)
                await db.commit()
                await db.refresh(strategy)
                
                print(f"  ✓ 策略已同步: {strategy.name} (ID: {strategy.strategy_id})")
                synced_count += 1
            
            except Exception as e:
                await db.rollback()
                print(f"  ✗ 同步失败: {config.get('name')} - {str(e)}")
        
        print()
        print("=" * 60)
        print("同步完成")
        print("=" * 60)
        print(f"新增策略: {synced_count}")
        print(f"已存在: {skipped_count}")
        print(f"总计: {synced_count + skipped_count}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(quick_sync())
