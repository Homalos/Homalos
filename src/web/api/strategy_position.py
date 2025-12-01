#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_position.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略持仓API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.core.database import get_db
from src.web.core.security import get_current_user
from src.web.models.admin import Admin
from src.web.models.strategy import Strategy
from src.web.services.strategy_position_service import StrategyPositionService
from src.web.schemas.strategy_position import StrategyPositionListResponse, StrategyTradeListResponse
from src.utils.log import get_logger
from sqlalchemy import select

router = APIRouter(prefix="/api/strategies-db", tags=["strategy-positions"])
logger = get_logger(__name__)
position_service = StrategyPositionService()


async def get_strategy_by_sid(
    sid: str,
    db: AsyncSession
) -> Strategy:
    """
    根据策略标识查询策略（支持 UUID、SID、整数ID）
    
    Args:
        sid: 策略标识，可以是：
            - UUID: 615d3c18-2005-4116-a47d-dcf587d12a33
            - SID: src.strategy.strategies.strategy1.Strategy1
            - 整数ID: 1
        db: 数据库会话
        
    Returns:
        Strategy: 策略对象，如果不存在返回 None
    """
    logger.info(f"[get_strategy_by_sid] 开始查询策略: {sid}")
    
    # 尝试按整数 ID 查询
    try:
        strategy_id_int = int(sid)
        logger.info(f"[get_strategy_by_sid] 尝试按整数 ID 查询: {strategy_id_int}")
        query = select(Strategy).where(Strategy.strategy_id == strategy_id_int)
        result = await db.execute(query)
        strategy = result.scalar_one_or_none()
        if strategy:
            logger.info(f"[get_strategy_by_sid] 按整数 ID 找到策略: {strategy.name}")
            return strategy
    except ValueError:
        pass
    
    # 尝试按 UUID 查询
    logger.info(f"[get_strategy_by_sid] 尝试按 UUID 查询: {sid}")
    query = select(Strategy).where(Strategy.uuid == sid)
    result = await db.execute(query)
    strategy = result.scalar_one_or_none()
    if strategy:
        logger.info(f"[get_strategy_by_sid] 按 UUID 找到策略: {strategy.name}")
        return strategy
    
    # 尝试按 module_path（SID）查询
    logger.info(f"[get_strategy_by_sid] 尝试按 module_path 查询: {sid}")
    query = select(Strategy).where(Strategy.module_path == sid)
    result = await db.execute(query)
    strategy = result.scalar_one_or_none()
    if strategy:
        logger.info(f"[get_strategy_by_sid] 按 module_path 找到策略: {strategy.name}")
    else:
        logger.warning(f"[get_strategy_by_sid] 未找到策略: {sid}")
    return strategy


async def verify_strategy_ownership(
    strategy_id: int,
    current_user: Admin,
    db: AsyncSession
) -> Strategy:
    """
    验证策略所有权
    
    Args:
        strategy_id: 策略ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        Strategy: 策略对象
        
    Raises:
        HTTPException: 如果策略不存在或无权限
    """
    from src.web.models.admin import AdminRole
    
    # 超级管理员可以查看所有策略
    if current_user.role == AdminRole.SUPER:
        query = select(Strategy).where(Strategy.strategy_id == strategy_id)
    else:
        # 普通管理员只能查看自己创建的策略
        query = select(Strategy).where(
            Strategy.strategy_id == strategy_id,
            Strategy.admin_id == current_user.admin_id
        )
    
    result = await db.execute(query)
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在或无权限")
    
    return strategy


@router.get("/{strategy_id}/positions", response_model=StrategyPositionListResponse)
async def get_strategy_current_positions(
    strategy_id: str,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取策略当前持仓
    
    - strategy_id 可以是整数 ID 或字符串 SID
    - 只能查看自己创建的策略的持仓
    - 返回未平仓的持仓列表
    """
    try:
        # 将 strategy_id 转换为整数（如果是数字字符串）
        strategy_id_int = None
        try:
            strategy_id_int = int(strategy_id)
            logger.info(f"策略ID为整数: {strategy_id_int}")
        except ValueError:
            # 如果不是数字，尝试从数据库查询
            logger.info(f"策略ID为字符串，尝试查询: {strategy_id}")
            strategy = await get_strategy_by_sid(strategy_id, db)
            if not strategy:
                logger.warning(f"策略不存在: {strategy_id}")
                raise HTTPException(status_code=404, detail="策略不存在")
            strategy_id_int = strategy.strategy_id
            logger.info(f"查询到策略: {strategy_id_int}")
        
        # 验证策略所有权
        await verify_strategy_ownership(strategy_id_int, current_user, db)
        
        # 获取当前持仓
        result = await position_service.get_current_positions(db, strategy_id_int)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取策略持仓失败: " + str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="获取策略持仓失败: " + str(e))


@router.get("/{strategy_id}/positions/history", response_model=StrategyPositionListResponse)
async def get_strategy_position_history(
    strategy_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取策略历史持仓
    
    - strategy_id 可以是整数 ID 或字符串 SID
    - 只能查看自己创建的策略的持仓
    - 返回已平仓的持仓列表
    - 按平仓时间倒序排列
    """
    try:
        # 将 strategy_id 转换为整数（如果是数字字符串）
        try:
            strategy_id_int = int(strategy_id)
        except ValueError:
            # 如果不是数字，尝试从数据库查询
            strategy = await get_strategy_by_sid(strategy_id, db)
            if not strategy:
                raise HTTPException(status_code=404, detail="策略不存在")
            strategy_id_int = strategy.strategy_id
        
        # 验证策略所有权
        await verify_strategy_ownership(strategy_id_int, current_user, db)
        
        # 获取历史持仓
        result = await position_service.get_position_history(db, strategy_id_int, limit)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取历史持仓失败: " + str(e))
        raise HTTPException(status_code=500, detail="获取历史持仓失败: " + str(e))


@router.get("/{strategy_id}/trades", response_model=StrategyTradeListResponse)
async def get_strategy_trades(
    strategy_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取策略成交记录
    
    - strategy_id 可以是整数 ID 或字符串 SID
    - 只能查看自己创建的策略的成交记录
    - 按成交时间倒序排列
    """
    try:
        # 将 strategy_id 转换为整数（如果是数字字符串）
        try:
            strategy_id_int = int(strategy_id)
        except ValueError:
            # 如果不是数字，尝试从数据库查询
            strategy = await get_strategy_by_sid(strategy_id, db)
            if not strategy:
                raise HTTPException(status_code=404, detail="策略不存在")
            strategy_id_int = strategy.strategy_id
        
        # 验证策略所有权
        await verify_strategy_ownership(strategy_id_int, current_user, db)
        
        # 获取成交记录
        result = await position_service.get_trades(db, strategy_id_int, limit)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取成交记录失败: " + str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="获取成交记录失败: " + str(e))
