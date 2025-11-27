#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_position_service.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略持仓服务层
"""
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.web.models.strategy_position import StrategyPosition
from src.web.schemas.strategy_position import (
    StrategyPositionResponse, StrategyPositionListResponse,
    StrategyPositionUpdate, StrategyPositionCreate
)
from src.utils.log import get_logger


class StrategyPositionService:
    """策略持仓服务"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    async def get_current_positions(
        self,
        db: AsyncSession,
        strategy_id: int
    ) -> StrategyPositionListResponse:
        """
        获取策略当前持仓
        
        Args:
            db: 数据库会话
            strategy_id: 策略ID
            
        Returns:
            StrategyPositionListResponse: 当前持仓列表
        """
        try:
            # 查询未平仓的持仓
            query = select(StrategyPosition).where(
                and_(
                    StrategyPosition.strategy_id == strategy_id,
                    StrategyPosition.is_closed == False
                )
            )
            result = await db.execute(query)
            positions = result.scalars().all()
            
            position_list = [StrategyPositionResponse.from_orm(p) for p in positions]
            
            self.logger.info("查询策略 {} 的当前持仓: 共 {} 个".format(strategy_id, len(position_list)))
            
            return StrategyPositionListResponse(
                total=len(position_list),
                positions=position_list
            )
        
        except Exception as e:
            self.logger.error("获取当前持仓失败: " + str(e), exc_info=True)
            raise

    async def get_position_history(
        self,
        db: AsyncSession,
        strategy_id: int,
        limit: int = 100
    ) -> StrategyPositionListResponse:
        """
        获取策略历史持仓
        
        Args:
            db: 数据库会话
            strategy_id: 策略ID
            limit: 返回的最大记录数
            
        Returns:
            StrategyPositionListResponse: 历史持仓列表
        """
        try:
            # 查询已平仓的持仓
            query = select(StrategyPosition).where(
                and_(
                    StrategyPosition.strategy_id == strategy_id,
                    StrategyPosition.is_closed == True
                )
            ).order_by(StrategyPosition.close_time.desc()).limit(limit)
            
            result = await db.execute(query)
            positions = result.scalars().all()
            
            position_list = [StrategyPositionResponse.from_orm(p) for p in positions]
            
            self.logger.info("查询策略 {} 的历史持仓: 共 {} 个".format(strategy_id, len(position_list)))
            
            return StrategyPositionListResponse(
                total=len(position_list),
                positions=position_list
            )
        
        except Exception as e:
            self.logger.error("获取历史持仓失败: " + str(e), exc_info=True)
            raise

    async def create_or_update_position(
        self,
        db: AsyncSession,
        position_data: StrategyPositionCreate
    ) -> StrategyPositionResponse:
        """
        创建或更新持仓
        
        Args:
            db: 数据库会话
            position_data: 持仓数据
            
        Returns:
            StrategyPositionResponse: 持仓信息
        """
        try:
            # 查找是否存在相同合约和方向的持仓
            query = select(StrategyPosition).where(
                and_(
                    StrategyPosition.strategy_id == position_data.strategy_id,
                    StrategyPosition.symbol == position_data.symbol,
                    StrategyPosition.direction == position_data.direction,
                    StrategyPosition.is_closed == False
                )
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                # 更新现有持仓
                total_volume = existing.volume + position_data.volume
                existing.avg_price = (
                    (existing.avg_price * existing.volume + position_data.avg_price * position_data.volume) 
                    / total_volume
                )
                existing.volume = total_volume
                existing.updated_at = datetime.utcnow()
                
                await db.commit()
                await db.refresh(existing)
                
                self.logger.info("更新持仓: {} {} {}".format(
                    position_data.symbol, position_data.direction, total_volume
                ))
                
                return StrategyPositionResponse.from_orm(existing)
            else:
                # 创建新持仓
                position = StrategyPosition(
                    strategy_id=position_data.strategy_id,
                    symbol=position_data.symbol,
                    exchange=position_data.exchange,
                    direction=position_data.direction,
                    volume=position_data.volume,
                    avg_price=position_data.avg_price,
                    open_time=datetime.utcnow()
                )
                
                db.add(position)
                await db.commit()
                await db.refresh(position)
                
                self.logger.info("创建持仓: {} {} {}".format(
                    position_data.symbol, position_data.direction, position_data.volume
                ))
                
                return StrategyPositionResponse.from_orm(position)
        
        except Exception as e:
            await db.rollback()
            self.logger.error("创建或更新持仓失败: " + str(e), exc_info=True)
            raise

    async def close_position(
        self,
        db: AsyncSession,
        strategy_id: int,
        symbol: str,
        direction: str,
        close_volume: int,
        close_price: float
    ) -> Optional[StrategyPositionResponse]:
        """
        平仓
        
        Args:
            db: 数据库会话
            strategy_id: 策略ID
            symbol: 合约代码
            direction: 持仓方向
            close_volume: 平仓数量
            close_price: 平仓价格
            
        Returns:
            StrategyPositionResponse: 更新后的持仓信息
        """
        try:
            # 查找持仓
            query = select(StrategyPosition).where(
                and_(
                    StrategyPosition.strategy_id == strategy_id,
                    StrategyPosition.symbol == symbol,
                    StrategyPosition.direction == direction,
                    StrategyPosition.is_closed == False
                )
            )
            result = await db.execute(query)
            position = result.scalar_one_or_none()
            
            if not position:
                self.logger.warning("未找到持仓: {} {} {}".format(strategy_id, symbol, direction))
                return None
            
            # 计算平仓盈亏
            if direction == "LONG":
                pnl = (close_price - position.avg_price) * close_volume
            else:  # SHORT
                pnl = (position.avg_price - close_price) * close_volume
            
            position.close_pnl += pnl
            
            # 减少持仓数量
            position.volume -= close_volume
            
            # 如果全部平仓，标记为已平仓
            if position.volume <= 0:
                position.is_closed = True
                position.close_time = datetime.utcnow()
                self.logger.info("全部平仓: {} {} 盈亏: {}".format(symbol, direction, position.close_pnl))
            else:
                self.logger.info("部分平仓: {} {} 剩余: {}".format(symbol, direction, position.volume))
            
            position.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(position)
            
            return StrategyPositionResponse.from_orm(position)
        
        except Exception as e:
            await db.rollback()
            self.logger.error("平仓失败: " + str(e), exc_info=True)
            raise
