#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : database.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据库连接管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger

logger = get_logger(__name__)

# 数据库文件路径
DATABASE_URL = f"sqlite+aiosqlite:///{get_path_ins.get_data_dir()}/homalos_web.db"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 生产环境设为False
    future=True
)

# 创建异步会话工厂
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    """
    获取数据库会话（依赖注入）
    
    Yields:
        AsyncSession: 数据库会话
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库（创建所有表）
    """
    try:
        from src.web.models.base import Base
        from src.web.models import user  # noqa: F401 导入所有模型以注册表

        async with engine.begin() as conn:
            # 创建所有表
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info(f"数据库初始化成功: {DATABASE_URL}")
    except Exception as e:
        logger.exception(f"数据库初始化失败: {e}")
        raise


async def close_db() -> None:
    """
    关闭数据库连接
    """
    try:
        await engine.dispose()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.exception(f"关闭数据库连接失败: {e}")

