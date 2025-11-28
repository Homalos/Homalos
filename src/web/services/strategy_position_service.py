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
from src.web.models.strategy_trade import StrategyTrade
from src.web.schemas.strategy_position import (
    StrategyPositionResponse, StrategyPositionListResponse,
    StrategyPositionUpdate, StrategyPositionCreate,
    StrategyTradeResponse, StrategyTradeListResponse
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

    async def get_trades(
        self,
        db: AsyncSession,
        strategy_id: int,
        limit: int = 100
    ) -> StrategyTradeListResponse:
        """
        获取策略成交记录
        
        Args:
            db: 数据库会话
            strategy_id: 策略ID
            limit: 返回的最大记录数
            
        Returns:
            StrategyTradeListResponse: 成交记录列表
        """
        try:
            # 查询成交记录，按成交时间倒序排列
            query = select(StrategyTrade).where(
                StrategyTrade.strategy_id == strategy_id
            ).order_by(StrategyTrade.trade_time.desc()).limit(limit)
            
            result = await db.execute(query)
            trades = result.scalars().all()
            
            trade_list = [StrategyTradeResponse.from_orm(t) for t in trades]
            
            self.logger.info("查询策略 {} 的成交记录: 共 {} 个".format(strategy_id, len(trade_list)))
            
            return StrategyTradeListResponse(
                total=len(trade_list),
                trades=trade_list
            )
        
        except Exception as e:
            self.logger.error("获取成交记录失败: " + str(e), exc_info=True)
            raise

    async def create_trade(
        self,
        db: AsyncSession,
        strategy_id: int,
        symbol: str,
        exchange: str,
        direction: str,
        offset_type: str,
        trade_price: float,
        trade_volume: int,
        commission: float = 0.0,
        order_id: str = None,
        pnl: float = 0.0,
        trade_time: datetime = None
    ) -> StrategyTradeResponse:
        """
        创建成交记录
        
        Args:
            db: 数据库会话
            strategy_id: 策略ID
            symbol: 合约代码
            exchange: 交易所代码
            direction: 成交方向 (LONG/SHORT)
            offset_type: 开平类型 (OPEN/CLOSE)
            trade_price: 成交价格
            trade_volume: 成交数量
            commission: 手续费
            order_id: 订单编号
            pnl: 成交盈亏
            trade_time: 成交时间（如果为None则使用当前时间）
            
        Returns:
            StrategyTradeResponse: 成交记录
        """
        try:
            if trade_time is None:
                trade_time = datetime.utcnow()
            
            trade = StrategyTrade(
                strategy_id=strategy_id,
                symbol=symbol,
                exchange=exchange,
                direction=direction,
                offset_type=offset_type,
                trade_price=trade_price,
                trade_volume=trade_volume,
                commission=commission,
                order_id=order_id,
                pnl=pnl,
                trade_time=trade_time
            )
            
            db.add(trade)
            await db.commit()
            await db.refresh(trade)
            
            self.logger.info("创建成交记录: {} {} {} {}手 @ {} 手续费: {}".format(
                symbol, direction, offset_type, trade_volume, trade_price, commission
            ))
            
            return StrategyTradeResponse.from_orm(trade)
        
        except Exception as e:
            await db.rollback()
            self.logger.error("创建成交记录失败: " + str(e), exc_info=True)
            raise
