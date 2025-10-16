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
        
        # 创建告警相关表（使用原生SQL，因为告警表不使用SQLAlchemy ORM）
        await _create_alarm_tables()
        
        logger.info(f"数据库初始化成功: {DATABASE_URL}")
    except Exception as e:
        logger.exception(f"数据库初始化失败: {e}")
        raise


async def _create_alarm_tables():
    """创建告警相关表"""
    import aiosqlite
    
    db_path = get_path_ins.join_path("data", "homalos_web.db")
    
    async with aiosqlite.connect(db_path) as db:
        # 创建告警记录表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alarm_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alarm_id TEXT NOT NULL UNIQUE,
                alarm_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT,
                message TEXT NOT NULL,
                details TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)
        
        # 创建索引
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alarm_type ON alarm_records(alarm_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_severity ON alarm_records(severity)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON alarm_records(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_status ON alarm_records(status)")
        
        # 创建告警配置表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alarm_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 插入默认配置
        default_configs = [
            ("cpu_threshold", "80", "CPU使用率告警阈值（%）"),
            ("memory_threshold", "85", "内存使用率告警阈值（%）"),
            ("retention_days", "30", "告警历史保留天数"),
            ("email_enabled", "true", "是否启用邮件通知"),
        ]
        
        for key, value, desc in default_configs:
            await db.execute(
                """
                INSERT OR IGNORE INTO alarm_config (config_key, config_value, description)
                VALUES (?, ?, ?)
                """,
                (key, value, desc)
            )
        
        await db.commit()
        logger.info("告警表创建成功")


async def close_db() -> None:
    """
    关闭数据库连接
    """
    try:
        await engine.dispose()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.exception(f"关闭数据库连接失败: {e}")

