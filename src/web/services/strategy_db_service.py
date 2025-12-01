#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_db_service.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略数据库服务层 - 处理策略的数据库操作
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.web.models.strategy import Strategy, StrategyStatus
from src.web.models.admin import Admin
from src.web.schemas.strategy_db import (
    StrategyCreate, StrategyUpdate, StrategyResponse, StrategyListResponse
)
from src.utils.log import get_logger


class StrategyDbService:
    """策略数据库服务"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    async def _build_strategy_response(
        self,
        db: AsyncSession,
        strategy: Strategy
    ) -> StrategyResponse:
        """
        构建策略响应，包含创建者信息
        
        Args:
            db: 数据库会话
            strategy: 策略对象
            
        Returns:
            StrategyResponse: 包含创建者信息的策略响应
        """
        # 获取创建者信息
        admin_username = None
        if strategy.admin_id:
            result = await db.execute(
                select(Admin).where(Admin.admin_id == strategy.admin_id)
            )
            admin = result.scalar_one_or_none()
            if admin:
                admin_username = admin.username
        
        # 构建响应
        response = StrategyResponse.from_orm(strategy)
        response.admin_username = admin_username
        return response

    async def create_strategy(
        self,
        db: AsyncSession,
        admin_id: int,
        strategy_data: StrategyCreate
    ) -> StrategyResponse:
        """
        创建策略
        
        Args:
            db: 数据库会话
            admin_id: 创建者管理员ID
            strategy_data: 策略创建数据
            
        Returns:
            StrategyResponse: 创建的策略信息
        """
        try:
            # 创建策略记录
            strategy = Strategy(
                admin_id=admin_id,
                name=strategy_data.name,
                description=strategy_data.description,
                author=strategy_data.author,
                file_path=strategy_data.file_path,
                module_path=strategy_data.module_path,
                class_name=strategy_data.class_name,
                instruments=strategy_data.instruments or [],
                parameters=strategy_data.parameters or {},
                status=strategy_data.status or StrategyStatus.DRAFT,
                enabled=strategy_data.enabled if strategy_data.enabled is not None else True
            )
            
            db.add(strategy)
            await db.commit()
            await db.refresh(strategy)
            
            self.logger.info(f"策略创建成功: {strategy.name} (ID: {strategy.strategy_id}, 创建者: {admin_id})")
            
            return await self._build_strategy_response(db, strategy)
        
        except Exception as e:
            await db.rollback()
            self.logger.error(f"创建策略失败: {e}", exc_info=True)
            raise

    async def get_strategy_by_id(
        self,
        db: AsyncSession,
        strategy_id: int,
        admin_id: Optional[int] = None
    ) -> Optional[StrategyResponse]:
        """
        获取策略详情
        
        Args:
            db: 数据库会话
            strategy_id: 策略ID
            admin_id: 管理员ID（如果提供，则只能查看自己创建的策略）
            
        Returns:
            StrategyResponse: 策略信息，如果不存在或无权限则返回None
        """
        try:
            query = select(Strategy).where(Strategy.strategy_id == strategy_id)
            
            # 如果提供了admin_id，则只能查看自己创建的策略
            if admin_id is not None:
                query = query.where(Strategy.admin_id == admin_id)
            
            result = await db.execute(query)
            strategy = result.scalar_one_or_none()
            
            if strategy:
                return await self._build_strategy_response(db, strategy)
            return None
        
        except Exception as e:
            self.logger.error(f"获取策略失败: {e}", exc_info=True)
            raise

    async def get_strategy_by_uuid(
        self,
        db: AsyncSession,
        uuid: str,
        admin_id: Optional[int] = None
    ) -> Optional[StrategyResponse]:
        """
        通过UUID获取策略
        
        Args:
            db: 数据库会话
            uuid: 策略UUID
            admin_id: 管理员ID（如果提供，则只能查看自己创建的策略）
            
        Returns:
            StrategyResponse: 策略信息
        """
        try:
            query = select(Strategy).where(Strategy.uuid == uuid)
            
            if admin_id is not None:
                query = query.where(Strategy.admin_id == admin_id)
            
            result = await db.execute(query)
            strategy = result.scalar_one_or_none()
            
            if strategy:
                return await self._build_strategy_response(db, strategy)
            return None
        
        except Exception as e:
            self.logger.error(f"通过UUID获取策略失败: {e}", exc_info=True)
            raise

    async def list_strategies(
        self,
        db: AsyncSession,
        admin_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> StrategyListResponse:
        """
        列出管理员创建的所有策略
        
        Args:
            db: 数据库会话
            admin_id: 管理员ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            status: 策略状态筛选
            enabled: 是否启用筛选
            
        Returns:
            StrategyListResponse: 策略列表
        """
        try:
            # 构建查询条件
            conditions = [Strategy.admin_id == admin_id]
            
            if status:
                conditions.append(Strategy.status == StrategyStatus[status.upper()])
            
            if enabled is not None:
                conditions.append(Strategy.enabled == enabled)
            
            # 查询总数
            count_query = select(Strategy).where(and_(*conditions))
            count_result = await db.execute(count_query)
            total = len(count_result.all())
            
            # 查询分页数据
            query = select(Strategy).where(and_(*conditions)).offset(skip).limit(limit)
            result = await db.execute(query)
            strategies = result.scalars().all()
            
            # 构建包含创建者信息的策略列表
            strategy_list = []
            for s in strategies:
                response = await self._build_strategy_response(db, s)
                strategy_list.append(response)
            
            self.logger.info(f"查询管理员 {admin_id} 的策略列表: 共 {total} 个，返回 {len(strategy_list)} 个")
            
            return StrategyListResponse(
                total=total,
                skip=skip,
                limit=limit,
                strategies=strategy_list
            )
        
        except Exception as e:
            self.logger.error(f"列出策略失败: {e}", exc_info=True)
            raise

    async def update_strategy(
        self,
        db: AsyncSession,
        strategy_id: int,
        admin_id: int,
        strategy_data: StrategyUpdate
    ) -> Optional[StrategyResponse]:
        """
        更新策略
        
        Args:
            db: 数据库会话
            strategy_id: 策略ID
            admin_id: 管理员ID（验证权限）
            strategy_data: 策略更新数据
            
        Returns:
            StrategyResponse: 更新后的策略信息，如果不存在或无权限则返回None
        """
        try:
            # 查询策略
            query = select(Strategy).where(
                and_(
                    Strategy.strategy_id == strategy_id,
                    Strategy.admin_id == admin_id
                )
            )
            result = await db.execute(query)
            strategy = result.scalar_one_or_none()
            
            if not strategy:
                self.logger.warning(f"策略不存在或无权限: ID={strategy_id}, 管理员={admin_id}")
                return None
            
            # 更新字段
            update_data = strategy_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if value is not None:
                    setattr(strategy, field, value)
            
            await db.commit()
            await db.refresh(strategy)
            
            self.logger.info(f"策略更新成功: {strategy.name} (ID: {strategy.strategy_id})")
            
            return StrategyResponse.from_orm(strategy)
        
        except Exception as e:
            await db.rollback()
            self.logger.error(f"更新策略失败: {e}", exc_info=True)
            raise

    async def delete_strategy(
        self,
        db: AsyncSession,
        strategy_id: int,
        admin_id: int
    ) -> bool:
        """
        删除策略
        
        Args:
            db: 数据库会话
            strategy_id: 策略ID
            admin_id: 管理员ID（验证权限）
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 查询策略
            query = select(Strategy).where(
                and_(
                    Strategy.strategy_id == strategy_id,
                    Strategy.admin_id == admin_id
                )
            )
            result = await db.execute(query)
            strategy = result.scalar_one_or_none()
            
            if not strategy:
                self.logger.warning(f"策略不存在或无权限: ID={strategy_id}, 管理员={admin_id}")
                return False
            
            # 删除策略
            await db.delete(strategy)
            await db.commit()
            
            self.logger.info(f"策略删除成功: {strategy.name} (ID: {strategy.strategy_id})")
            
            return True
        
        except Exception as e:
            await db.rollback()
            self.logger.error(f"删除策略失败: {e}", exc_info=True)
            raise

    async def enable_strategy(
        self,
        db: AsyncSession,
        strategy_id: int,
        admin_id: int
    ) -> Optional[StrategyResponse]:
        """启用策略"""
        return await self.update_strategy(
            db,
            strategy_id,
            admin_id,
            StrategyUpdate(enabled=True)
        )

    async def disable_strategy(
        self,
        db: AsyncSession,
        strategy_id: int,
        admin_id: int
    ) -> Optional[StrategyResponse]:
        """禁用策略"""
        return await self.update_strategy(
            db,
            strategy_id,
            admin_id,
            StrategyUpdate(enabled=False)
        )
