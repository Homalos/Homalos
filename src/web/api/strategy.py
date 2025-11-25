#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy.py
@Date       : 2025/10/16
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略管理 API Router

提供以下接口:
- GET `/` - 列出所有注册策略
- POST `/{sid}/start` - 启动策略
- POST `/{sid}/stop` - 停止策略
- POST `/{sid}/enable` - 启用策略
- POST `/{sid}/disable` - 禁用策略
- GET `/status` - 查看策略运行状态
- WebSocket `/ws` - 实时接收策略消息（支持 ?filter=sid 查询参数）

注意：策略热重载功能已禁用（出于安全考虑）。请使用"停止-修改-启动"流程修改策略。
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Optional, Any

from src.core.constants import Interval
from src.web.services.strategy_service import strategy_service
from src.web.schemas.strategy import (
    StrategyListResponse,
    StrategyStatusResponse,
    OperationResponse
)
from pydantic import BaseModel, Field
from src.utils.log import get_logger

logger = get_logger(__name__)


class ScanSingleRequest(BaseModel):
    """扫描单个策略文件请求"""
    filename: str = Field(..., description="策略文件名，如 strategy2.py")


def serialize_message(msg: dict[str, Any]) -> dict[str, Any]:
    """
    序列化消息，将 Interval 枚举对象转换为字符串
    
    Args:
        msg: 原始消息字典
        
    Returns:
        序列化后的消息字典
    """
    def convert_value(value):
        """递归转换值"""
        if isinstance(value, Interval):
            return value.value  # 枚举转为字符串值
        elif isinstance(value, list):
            return [convert_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: convert_value(v) for k, v in value.items()}
        else:
            return value
    
    return {k: convert_value(v) for k, v in msg.items()}

# 创建路由器
router = APIRouter(prefix="/strategies", tags=["策略管理"])


@router.get("/", response_model=StrategyListResponse, summary="获取策略列表")
async def list_strategies():
    """
    获取所有注册的策略配置
    
    Returns:
        StrategyListResponse: 包含所有策略配置的字典
    """
    try:
        strategies = strategy_service.list_strategies()
        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取策略列表失败: {str(e)}")


@router.get("/uuid/{strategy_uuid}", summary="通过UUID获取策略信息")
async def get_strategy_by_uuid(strategy_uuid: str):
    """
    通过UUID获取策略配置信息
    
    Args:
        strategy_uuid: 策略UUID
        
    Returns:
        dict: 包含策略ID和配置信息
    """
    try:
        result = strategy_service.get_strategy_by_uuid(strategy_uuid)
        if result is None:
            raise HTTPException(status_code=404, detail=f"策略UUID {strategy_uuid} 不存在")
        
        sid, config = result
        return {
            "sid": sid,
            "uuid": strategy_uuid,
            "config": config
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"通过UUID获取策略失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取策略失败: {str(e)}")


@router.post("/reload-config", summary="重新加载策略配置")
async def reload_strategy_config():
    """
    重新加载策略注册表配置文件
    用于在配置文件被外部修改后刷新内存中的配置
    """
    try:
        manager = strategy_service.get_manager()
        manager.registry.reload()
        strategies = manager.registry.list_all()
        return {
            "success": True,
            "message": "策略配置已重新加载",
            "total": len(strategies)
        }
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新加载配置失败: {str(e)}")


@router.post("/{sid}/start", response_model=OperationResponse, summary="启动策略")
async def start_strategy(sid: str):
    """
    启动指定的策略
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        await strategy_service.start_strategy(sid)
        return {
            "status": "started",
            "sid": sid,
            "message": f"策略 {sid} 已成功启动"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"启动策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动策略失败: {str(e)}")


@router.post("/{sid}/stop", response_model=OperationResponse, summary="停止策略")
async def stop_strategy(sid: str):
    """
    停止指定的策略
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        await strategy_service.stop_strategy(sid)
        return {
            "status": "stopped",
            "sid": sid,
            "message": f"策略 {sid} 已停止"
        }
    except Exception as e:
        logger.error(f"停止策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"停止策略失败: {str(e)}")


# 策略热重载端点已删除（出于安全考虑）
# @router.post("/{sid}/reload", ...)
# 请使用"停止-修改-启动"流程修改策略


@router.post("/{sid}/enable", response_model=OperationResponse, summary="启用策略")
async def enable_strategy(sid: str):
    """
    在注册中心启用策略（下次启动时自动加载）
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        strategy_service.enable_strategy(sid)
        return {
            "status": "enabled",
            "sid": sid,
            "message": f"策略 {sid} 已启用"
        }
    except Exception as e:
        logger.error(f"启用策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启用策略失败: {str(e)}")


@router.post("/{sid}/disable", response_model=OperationResponse, summary="禁用策略")
async def disable_strategy(sid: str):
    """
    在注册中心禁用策略（下次启动时不自动加载）
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        strategy_service.disable_strategy(sid)
        return {
            "status": "disabled",
            "sid": sid,
            "message": f"策略 {sid} 已禁用"
        }
    except Exception as e:
        logger.error(f"禁用策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"禁用策略失败: {str(e)}")


@router.post("/scan", summary="扫描并加载全部策略")
async def scan_strategies():
    """
    扫描策略目录，自动发现并注册所有继承BaseStrategy的策略类
    
    功能：
    - 扫描 src/strategy/strategies/ 目录下的所有.py文件
    - 识别继承BaseStrategy的策略类
    - 自动生成/更新 strategy_registry.json
    - 使用策略实例的UUID作为策略ID（避免冲突）
    
    Returns:
        dict: 扫描结果统计
    """
    try:
        result = strategy_service.scan_and_load_strategies()
        return {
            "success": True,
            "message": f"扫描完成: 发现 {result['total_discovered']} 个策略, "
                      f"新增 {result['newly_added']} 个, 更新 {result['updated']} 个",
            "data": result
        }
    except Exception as e:
        logger.error(f"扫描策略失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"扫描策略失败: {str(e)}")


@router.get("/available-files", summary="获取可用的策略文件列表")
async def get_available_strategy_files():
    """
    获取所有可用的策略文件列表
    
    功能：
    - 列出 src/strategy/strategies/ 目录下的所有.py策略文件
    - 显示每个文件的加载状态（已加载/未加载）
    - 显示策略名称和类名
    
    Returns:
        dict: 策略文件列表及加载状态
    """
    try:
        result = strategy_service.get_available_strategy_files()
        return result
    except Exception as e:
        logger.error(f"获取策略文件列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取策略文件列表失败: {str(e)}")


@router.post("/scan-single", summary="扫描并加载单个策略文件")
async def scan_single_strategy(request: ScanSingleRequest):
    """
    扫描并加载单个策略文件
    
    功能：
    - 扫描指定的策略文件
    - 如果策略ID已存在，更新元数据（保留enabled和params）
    - 如果策略ID不存在，添加到注册表（enabled=true）
    - 不自动启动策略运行
    
    Args:
        request: 包含文件名的请求体
    
    Returns:
        dict: 加载结果
    """
    try:
        result = strategy_service.scan_single_strategy(request.filename)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"加载策略文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"加载策略文件失败: {str(e)}")


@router.delete("/{sid}/unload", response_model=OperationResponse, summary="卸载策略")
async def unload_strategy(sid: str):
    """
    卸载指定的策略（停止运行并从管理器中移除）
    
    Args:
        sid: 策略ID
        
    Returns:
        OperationResponse: 操作结果
    """
    try:
        strategy_service.unload_strategy(sid)
        return {
            "status": "unloaded",
            "sid": sid,
            "message": f"策略 {sid} 已卸载"
        }
    except Exception as e:
        logger.error(f"卸载策略 {sid} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"卸载策略失败: {str(e)}")


# 以下调试端点已删除（与热重载功能相关）：
# - GET /debug/reloading - 获取正在reload的策略
# - POST /debug/clear-lock/{sid} - 清除reload锁


# ========== 状态持久化相关端点 ==========

@router.post("/{sid}/state/save", summary="手动保存策略状态")
async def save_strategy_state(sid: str):
    """
    手动保存指定策略的当前状态到文件
    
    Args:
        sid: 策略ID
        
    Returns:
        操作结果
    """
    try:
        success = await strategy_service.save_strategy_state(sid)
        if success:
            return {
                "status": "saved",
                "sid": sid,
                "message": f"策略 {sid} 的状态已保存"
            }
        else:
            return {
                "status": "failed",
                "sid": sid,
                "message": f"策略 {sid} 的状态保存失败"
            }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"保存策略 {sid} 状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存状态失败: {str(e)}")


@router.get("/{sid}/state", summary="获取策略状态")
async def get_strategy_state(
    sid: str,
    timestamp: Optional[str] = Query(None, description="可选：指定时间戳（格式：20251016_143000）")
):
    """
    获取策略的保存状态
    
    Args:
        sid: 策略ID
        timestamp: 可选，指定时间戳获取历史状态
        
    Returns:
        策略状态数据
    """
    try:
        state = await strategy_service.load_strategy_state(sid, timestamp or "")
        if state is None:
            raise HTTPException(status_code=404, detail=f"策略 {sid} 没有保存的状态")
        
        return {
            "sid": sid,
            "timestamp": timestamp or "latest",
            "state": state
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略 {sid} 状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/{sid}/state/history", summary="获取状态历史列表")
async def get_state_history(
    sid: str,
    limit: int = Query(10, ge=1, le=100, description="返回最近N条记录")
):
    """
    获取策略的状态历史列表（不包含状态数据，只有元信息）
    
    Args:
        sid: 策略ID
        limit: 返回最近N条记录
        
    Returns:
        历史记录列表
    """
    try:
        history = await strategy_service.get_state_history(sid, limit)
        return {
            "sid": sid,
            "count": len(history),
            "history": history
        }
    except Exception as e:
        logger.error(f"获取策略 {sid} 历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.delete("/states/cleanup", summary="清理旧状态")
async def cleanup_old_states(
    days: int = Query(30, ge=1, le=365, description="保留最近N天的状态")
):
    """
    清理超过指定天数的旧状态文件
    
    Args:
        days: 保留最近N天
        
    Returns:
        清理结果
    """
    try:
        await strategy_service.cleanup_old_states(days)
        return {
            "status": "success",
            "message": f"已清理超过 {days} 天的旧状态",
            "days": days
        }
    except Exception as e:
        logger.error(f"清理旧状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/states/storage-info", summary="获取存储信息")
async def get_storage_info():
    """
    获取状态存储的统计信息
    
    Returns:
        存储统计数据
    """
    try:
        info = strategy_service.get_storage_info()
        return info
    except Exception as e:
        logger.error(f"获取存储信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取存储信息失败: {str(e)}")


@router.get("/status", response_model=StrategyStatusResponse, summary="获取策略运行状态")
async def get_strategy_status():
    """
    获取所有运行中策略的状态信息
    
    Returns:
        StrategyStatusResponse: 运行状态字典
    """
    try:
        status = strategy_service.get_status()
        return {"running": status}
    except Exception as e:
        logger.error(f"获取策略状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取策略状态失败: {str(e)}")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    filter: Optional[str] = Query(None, description="可选：只接收指定策略ID的消息")
):
    """
    WebSocket 端点，用于实时接收策略消息
    
    Args:
        websocket: WebSocket连接
        filter: 可选，指定策略ID进行消息过滤
        
    消息格式:
        {
            "type": "log"|"error"|"status"|"order"|"trade",
            "sid": "策略ID",
            "payload": "消息内容",
            "trace": "错误堆栈（仅error类型）"
        }
    """
    await websocket.accept()
    logger.info(f"WebSocket连接已建立, filter={filter}")
    
    # 创建消息队列（增大队列容量，避免高频消息时阻塞）
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    
    try:
        # 注册队列到策略服务
        strategy_service.register_ws_queue(q)
        
        # 持续接收并转发消息
        while True:
            try:
                # 使用超时机制，避免无限等待导致关闭时被强制取消
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # 超时后检查 WebSocket 连接状态，如果已断开则退出
                    # 这确保在系统关闭时能快速检测到并退出循环
                    try:
                        # 尝试发送一个心跳 ping 来检测连接状态
                        await asyncio.wait_for(websocket.send_json({"type": "ping"}), timeout=0.1)
                    except Exception:
                        # 连接已断开或发送失败，退出循环
                        logger.info("WebSocket连接已断开，退出消息循环")
                        break
                    continue
                
                # 可选过滤
                if filter and msg.get("sid") != filter:
                    continue
                
                # 序列化消息（转换 Interval 枚举对象为字符串）
                serialized_msg = serialize_message(msg)
                
                # 发送消息（增加超时和错误处理）
                try:
                    await asyncio.wait_for(websocket.send_json(serialized_msg), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("WebSocket发送消息超时，跳过该消息")
                    continue
                except Exception as send_err:
                    logger.error(f"WebSocket发送消息失败: {send_err}", exc_info=True)
                    raise  # 连接已断开，退出循环
            
            except asyncio.CancelledError:
                # 优雅关闭：记录日志并退出循环，不重新抛出异常
                logger.info("WebSocket任务被取消（系统关闭中）")
                break
            except Exception as loop_err:
                logger.error(f"WebSocket消息处理循环错误: {loop_err}", exc_info=True)
                raise
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接已断开, filter={filter}")
    except asyncio.CancelledError:
        # 优雅关闭：系统关闭时 WebSocket 任务被取消是正常行为
        logger.info("WebSocket任务被取消（系统关闭中）")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}", exc_info=True)
    finally:
        # 清理：注销队列
        strategy_service.unregister_ws_queue(q)
        try:
            await websocket.close()
        except Exception:
            pass


# ========== 策略日志相关端点 ==========

@router.get("/{sid}/logs", summary="获取策略日志")
async def get_strategy_logs(
    sid: str,
    limit: int = Query(100, ge=1, le=1000, description="返回最近N条日志"),
    trace_id: Optional[str] = Query(None, description="可选：按 trace_id 过滤日志"),
    context: Optional[str] = Query(None, description="可选：按 context 标签过滤日志")
):
    """
    获取指定策略的最近日志，支持按 trace_id 和 context 过滤
    
    Args:
        sid: 策略ID
        limit: 返回的最大日志条数
        trace_id: 可选，按 trace_id 过滤日志
        context: 可选，按 context 标签过滤日志
        
    Returns:
        包含日志列表和追踪信息的响应
    """
    try:
        result = strategy_service.get_strategy_logs(sid, limit, trace_id, context)
        return {
            "code": 200,
            "message": "获取日志成功",
            "data": {
                "sid": sid,
                "logs": result.get("logs", []),
                "count": result.get("count", 0),
                "available_trace_ids": result.get("available_trace_ids", []),
                "available_contexts": result.get("available_contexts", []),
                "filter": result.get("filter", {})
            }
        }
    except Exception as e:
        logger.error(f"获取策略日志失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

