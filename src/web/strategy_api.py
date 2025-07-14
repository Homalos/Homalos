#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : strategy_api
@Date       : 2025/1/20
@Author     : Assistant
@Description: 策略增强功能的REST API接口
"""

import asyncio
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

from src.core.logger import get_logger
from src.services.trading_engine import StrategyManager
from src.strategies.dependency_checker import DependencyChecker
from src.strategies.strategy_validator import StrategyValidator
from src.strategies.strategy_health_monitor import StrategyHealthMonitor

logger = get_logger("StrategyAPI")

# Pydantic模型定义
class StrategyValidationRequest(BaseModel):
    """策略验证请求"""
    strategy_path: str = Field(..., description="策略文件路径")
    validation_types: Optional[List[str]] = Field(default=None, description="验证类型列表")
    force_refresh: bool = Field(default=False, description="是否强制刷新缓存")

class DependencyCheckRequest(BaseModel):
    """依赖检查请求"""
    strategy_uuid: str = Field(..., description="策略UUID")
    check_types: Optional[List[str]] = Field(default=None, description="检查类型列表")
    force_refresh: bool = Field(default=False, description="是否强制刷新缓存")

class HealthCheckRequest(BaseModel):
    """健康检查请求"""
    strategy_uuid: str = Field(..., description="策略UUID")
    include_metrics: bool = Field(default=True, description="是否包含详细指标")
    include_anomalies: bool = Field(default=True, description="是否包含异常信息")

class StrategyRecoveryRequest(BaseModel):
    """策略恢复请求"""
    strategy_uuid: str = Field(..., description="策略UUID")
    recovery_type: Optional[str] = Field(default="auto", description="恢复类型")
    force_recovery: bool = Field(default=False, description="是否强制恢复")

class APIResponse(BaseModel):
    """API响应基类"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

# 创建API路由器
router = APIRouter(prefix="/api/v1/strategies", tags=["策略增强管理"])

# 依赖注入
async def get_strategy_manager() -> StrategyManager:
    """获取策略管理器实例"""
    # 这里应该从应用上下文中获取实例
    # 暂时返回None，实际使用时需要注入真实实例
    return None

async def get_dependency_checker() -> DependencyChecker:
    """获取依赖检查器实例"""
    return None

async def get_strategy_validator() -> StrategyValidator:
    """获取策略验证器实例"""
    return None

async def get_health_monitor() -> StrategyHealthMonitor:
    """获取健康监控器实例"""
    return None

@router.get("/{strategy_uuid}/health", response_model=APIResponse)
async def get_strategy_health(
    strategy_uuid: str,
    include_metrics: bool = True,
    include_anomalies: bool = True,
    strategy_manager: StrategyManager = Depends(get_strategy_manager)
):
    """获取策略健康状态"""
    try:
        if not strategy_manager:
            raise HTTPException(status_code=500, detail="策略管理器未初始化")
        
        # 检查策略是否存在
        strategy_status = strategy_manager.get_strategy_status(strategy_uuid)
        if not strategy_status:
            raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_uuid}")
        
        # 获取健康报告
        health_report = await strategy_manager.get_strategy_health_report(strategy_uuid)
        if not health_report:
            raise HTTPException(status_code=500, detail="无法获取策略健康报告")
        
        # 构建响应数据
        response_data = {
            "strategy_uuid": strategy_uuid,
            "strategy_name": strategy_status["strategy_name"],
            "health_status": health_report.get("status"),
            "last_check_time": health_report.get("timestamp")
        }
        
        if include_metrics:
            response_data["metrics"] = health_report.get("metrics", {})
        
        if include_anomalies:
            response_data["anomalies"] = health_report.get("anomalies", [])
        
        return APIResponse(
            success=True,
            message="获取策略健康状态成功",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

@router.get("/{strategy_uuid}/dependencies", response_model=APIResponse)
async def check_strategy_dependencies(
    strategy_uuid: str,
    check_types: Optional[str] = None,
    force_refresh: bool = False,
    dependency_checker: DependencyChecker = Depends(get_dependency_checker)
):
    """检查策略依赖"""
    try:
        if not dependency_checker:
            raise HTTPException(status_code=500, detail="依赖检查器未初始化")
        
        # 解析检查类型
        check_type_list = None
        if check_types:
            check_type_list = [t.strip() for t in check_types.split(",")]
        
        # 执行依赖检查
        check_result = await dependency_checker.run_all_checks(
            strategy_uuid=strategy_uuid,
            check_types=check_type_list,
            force_refresh=force_refresh
        )
        
        # 构建响应数据
        response_data = {
            "strategy_uuid": strategy_uuid,
            "overall_status": check_result.overall_status.value,
            "check_time": check_result.check_time.isoformat(),
            "total_checks": check_result.total_checks,
            "passed_checks": check_result.passed_checks,
            "failed_checks": check_result.failed_checks,
            "check_items": [
                {
                    "dependency_type": item.dependency_type.value,
                    "status": item.status.value,
                    "message": item.message,
                    "details": item.details,
                    "check_time": item.check_time.isoformat()
                }
                for item in check_result.check_items
            ]
        }
        
        return APIResponse(
            success=True,
            message="策略依赖检查完成",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"策略依赖检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

@router.post("/{strategy_uuid}/validate", response_model=APIResponse)
async def validate_strategy(
    strategy_uuid: str,
    request: StrategyValidationRequest,
    strategy_validator: StrategyValidator = Depends(get_strategy_validator),
    strategy_manager: StrategyManager = Depends(get_strategy_manager)
):
    """验证策略"""
    try:
        if not strategy_validator:
            raise HTTPException(status_code=500, detail="策略验证器未初始化")
        
        if not strategy_manager:
            raise HTTPException(status_code=500, detail="策略管理器未初始化")
        
        # 检查策略是否存在
        strategy_status = strategy_manager.get_strategy_status(strategy_uuid)
        if not strategy_status:
            raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_uuid}")
        
        # 执行策略验证
        validation_result = await strategy_validator.run_full_validation(
            strategy_path=request.strategy_path,
            validation_types=request.validation_types,
            force_refresh=request.force_refresh
        )
        
        # 构建响应数据
        response_data = {
            "strategy_uuid": strategy_uuid,
            "strategy_path": request.strategy_path,
            "overall_status": validation_result.overall_status.value,
            "validation_time": validation_result.validation_time.isoformat(),
            "total_validations": validation_result.total_validations,
            "passed_validations": validation_result.passed_validations,
            "failed_validations": validation_result.failed_validations,
            "issues": [
                {
                    "validation_type": issue.validation_type.value,
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "details": issue.details,
                    "line_number": issue.line_number,
                    "suggestions": issue.suggestions
                }
                for issue in validation_result.issues
            ]
        }
        
        return APIResponse(
            success=True,
            message="策略验证完成",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"策略验证失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

@router.post("/{strategy_uuid}/recover", response_model=APIResponse)
async def recover_strategy(
    strategy_uuid: str,
    request: StrategyRecoveryRequest,
    background_tasks: BackgroundTasks,
    strategy_manager: StrategyManager = Depends(get_strategy_manager)
):
    """恢复策略"""
    try:
        if not strategy_manager:
            raise HTTPException(status_code=500, detail="策略管理器未初始化")
        
        # 检查策略是否存在
        strategy_status = strategy_manager.get_strategy_status(strategy_uuid)
        if not strategy_status:
            raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_uuid}")
        
        # 检查策略状态
        if strategy_status["status"] == "running" and not request.force_recovery:
            return APIResponse(
                success=True,
                message="策略已在运行中，无需恢复",
                data={"strategy_uuid": strategy_uuid, "current_status": "running"}
            )
        
        # 异步执行恢复操作
        async def perform_recovery():
            try:
                await strategy_manager._attempt_strategy_recovery(
                    strategy_uuid, 
                    request.recovery_type or "manual"
                )
            except Exception as e:
                logger.error(f"策略恢复异步任务失败: {e}")
        
        background_tasks.add_task(perform_recovery)
        
        return APIResponse(
            success=True,
            message="策略恢复任务已启动",
            data={
                "strategy_uuid": strategy_uuid,
                "recovery_type": request.recovery_type,
                "status": "recovery_started"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"策略恢复失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

@router.get("/health/summary", response_model=APIResponse)
async def get_all_strategies_health_summary(
    strategy_manager: StrategyManager = Depends(get_strategy_manager)
):
    """获取所有策略健康状态摘要"""
    try:
        if not strategy_manager:
            raise HTTPException(status_code=500, detail="策略管理器未初始化")
        
        # 获取所有策略状态
        all_strategies = strategy_manager.get_all_strategies()
        
        # 获取健康状态摘要
        health_summary = {
            "total_strategies": len(all_strategies),
            "running_strategies": 0,
            "stopped_strategies": 0,
            "error_strategies": 0,
            "healthy_strategies": 0,
            "unhealthy_strategies": 0,
            "strategies": []
        }
        
        for strategy_uuid, strategy_info in all_strategies.items():
            status = strategy_info["status"]
            
            # 统计策略状态
            if status == "running":
                health_summary["running_strategies"] += 1
            elif status == "stopped":
                health_summary["stopped_strategies"] += 1
            elif status == "error":
                health_summary["error_strategies"] += 1
            
            # 获取健康状态（仅对运行中的策略）
            health_status = "unknown"
            if status == "running":
                try:
                    health_report = await strategy_manager.get_strategy_health_report(strategy_uuid)
                    if health_report:
                        health_status = health_report.get("status", "unknown")
                        if health_status == "healthy":
                            health_summary["healthy_strategies"] += 1
                        else:
                            health_summary["unhealthy_strategies"] += 1
                except Exception as e:
                    logger.warning(f"获取策略 {strategy_uuid} 健康状态失败: {e}")
            
            # 添加策略摘要信息
            health_summary["strategies"].append({
                "strategy_uuid": strategy_uuid,
                "strategy_name": strategy_info["strategy_name"],
                "status": status,
                "health_status": health_status,
                "start_time": strategy_info.get("start_time"),
                "error_message": strategy_info.get("error_message")
            })
        
        return APIResponse(
            success=True,
            message="获取策略健康状态摘要成功",
            data=health_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略健康状态摘要失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

@router.get("/events/{strategy_uuid}", response_model=APIResponse)
async def get_strategy_events(
    strategy_uuid: str,
    limit: int = 100,
    offset: int = 0,
    event_types: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    strategy_manager: StrategyManager = Depends(get_strategy_manager)
):
    """获取策略事件历史"""
    try:
        if not strategy_manager:
            raise HTTPException(status_code=500, detail="策略管理器未初始化")
        
        # 检查策略是否存在
        strategy_status = strategy_manager.get_strategy_status(strategy_uuid)
        if not strategy_status:
            raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_uuid}")
        
        # 解析事件类型过滤器
        event_type_list = None
        if event_types:
            event_type_list = [t.strip() for t in event_types.split(",")]
        
        # 获取事件历史（这里需要实现事件查询逻辑）
        # 暂时返回模拟数据
        events_data = {
            "strategy_uuid": strategy_uuid,
            "total_events": 0,
            "events": [],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": False
            }
        }
        
        return APIResponse(
            success=True,
            message="获取策略事件历史成功",
            data=events_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略事件历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")