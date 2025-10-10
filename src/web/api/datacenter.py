#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : datacenter.py
@Date       : 2025/10/10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据中心管理相关API路由
"""
import asyncio
import json
import queue
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.web.core.security import get_current_user
from src.web.core.database import get_db
from src.web.models.user import User
from src.web.services.datacenter_service import DataCenterService
from src.web.services.config_service import ConfigService
from src.web.schemas.datacenter import (
    StartRequest, StartResponse,
    StopRequest, StopResponse,
    StatusResponse,
    LogsResponse,
    ConfigResponse, ConfigUpdateRequest, ConfigUpdateResponse
)

router = APIRouter(prefix="/datacenter", tags=["数据中心管理"])


def check_admin_permission(current_user: User):
    """检查管理员权限"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )


# ========== 控制接口 ==========

@router.post("/start", response_model=StartResponse, summary="启动数据中心")
async def start_datacenter(
    request: StartRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    启动数据中心进程
    
    - **需要管理员权限**
    - 如果已在运行则返回错误
    - 返回进程PID
    """
    check_admin_permission(current_user)
    
    result = await DataCenterService.start(current_user.id, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return StartResponse(**result)


@router.post("/stop", response_model=StopResponse, summary="停止数据中心")
async def stop_datacenter(
    request: StopRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    停止数据中心进程
    
    - **需要管理员权限**
    - **force**: 是否强制停止（SIGKILL），默认优雅停止（SIGTERM）
    - **timeout**: 等待超时时间（秒），默认30秒
    """
    check_admin_permission(current_user)
    
    result = await DataCenterService.stop(
        current_user.id, 
        db, 
        force=request.force,
        timeout=request.timeout
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return StopResponse(**result)


@router.post("/restart", response_model=StartResponse, summary="重启数据中心")
async def restart_datacenter(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    重启数据中心（先停止再启动）
    
    - **需要管理员权限**
    """
    check_admin_permission(current_user)
    
    result = await DataCenterService.restart(current_user.id, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return StartResponse(**result)


# ========== 状态查询接口 ==========

@router.get("/status", response_model=StatusResponse, summary="获取数据中心状态")
async def get_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取数据中心详细运行状态
    
    返回信息：
    - **running**: 是否运行
    - **pid**: 进程ID
    - **cpu_percent**: CPU使用率
    - **memory_mb**: 内存使用(MB)
    - **memory_percent**: 内存使用率(%)
    - **create_time**: 启动时间(ISO格式)
    - **num_threads**: 线程数
    - **internal_status**: 数据中心内部状态（如果可用）
    """
    status_info = DataCenterService.get_status()
    return StatusResponse(**status_info)


# ========== 日志查看接口 ==========

@router.get("/logs", response_model=LogsResponse, summary="获取数据中心日志")
async def get_logs(
    lines: int = 100,
    level: str = "all",
    since_line: int = None,
    current_user: User = Depends(get_current_user)
):
    """
    获取数据中心日志（兼容模式）
    
    参数:
    - **lines**: 返回最后N行，默认100（当since_line未指定时有效）
    - **level**: 日志级别 (all/INFO/WARNING/ERROR/DEBUG)
    - **since_line**: 从第N行之后开始读取，用于增量更新（可选）
    
    注：优先从内存缓冲区读取，回退到文件读取
    """
    # 优先尝试从内存缓冲区读取
    try:
        from src.web.services.log_buffer import log_buffer, format_log_for_display
        
        logs = log_buffer.get_recent(lines)
        if logs:
            # 格式化日志用于显示
            formatted_logs = [format_log_for_display(log) for log in logs]
            
            # 应用级别过滤
            if level != "all":
                level_upper = level.upper()
                formatted_logs = [
                    log for log in formatted_logs
                    if f" {level_upper} " in log or f"|{level_upper}|" in log
                ]
            
            return LogsResponse(
                success=True,
                logs=formatted_logs,
                total_lines=log_buffer.total_logs_count,
                log_file="memory_buffer"
            )
    except ImportError:
        pass  # 内存缓冲未启用，使用文件读取
    except Exception as e:
        # 内存读取失败，回退到文件
        pass
    
    # 回退到文件读取
    result = DataCenterService.get_logs(lines=lines, level=level, since_line=since_line)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return LogsResponse(**result)


@router.get("/logs/stream", summary="SSE实时日志流")
async def stream_logs(
    current_user: User = Depends(get_current_user)
):
    """
    SSE实时日志流
    
    返回格式：text/event-stream
    - 首次连接：发送最新100条历史日志
    - 之后：实时推送新日志
    - 每30秒发送心跳防止超时
    
    使用方法（前端）：
    ```javascript
    const eventSource = new EventSource('/api/datacenter/logs/stream')
    eventSource.onmessage = (event) => {
        const log = JSON.parse(event.data)
        console.log(log)
    }
    ```
    """
    try:
        from src.web.services.log_buffer import log_buffer
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSE日志流未启用，请设置环境变量 ENABLE_SSE_LOGS=true"
        )
    
    async def event_generator():
        import time
        
        subscriber_queue = None
        try:
            # 1. 发送历史日志（最新100条）
            recent_logs = log_buffer.get_recent(100)
            for log in recent_logs:
                yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"
            
            # 2. 订阅新日志
            try:
                subscriber_queue = log_buffer.subscribe()
            except Exception as e:
                # 超过最大订阅者数量
                yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                return
            
            # 3. 持续推送新日志
            last_heartbeat = time.time()
            
            while True:
                try:
                    # 从队列获取日志（1秒超时）
                    log_entry = await asyncio.get_event_loop().run_in_executor(
                        None, subscriber_queue.get, True, 1
                    )
                    yield f"data: {json.dumps(log_entry, ensure_ascii=False)}\n\n"
                    last_heartbeat = time.time()
                    
                except queue.Empty:
                    # 检查是否需要发送心跳
                    if time.time() - last_heartbeat > 30:
                        yield ": heartbeat\n\n"
                        last_heartbeat = time.time()
                        
                except asyncio.CancelledError:
                    # 客户端断开连接
                    break
                    
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            
        finally:
            # 清理：取消订阅
            if subscriber_queue:
                log_buffer.unsubscribe(subscriber_queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )


@router.get("/logs/stats", summary="获取日志缓冲统计")
async def get_log_stats(
    current_user: User = Depends(get_current_user)
):
    """
    获取日志缓冲区统计信息
    
    返回：
    - buffer_size: 当前缓冲区日志数量
    - total_logs: 总共处理的日志数量
    - active_subscribers: 活跃的SSE订阅者数量
    - memory_usage_kb: 内存使用量（KB）
    """
    try:
        from src.web.services.log_buffer import log_buffer
        return log_buffer.get_stats()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSE日志流未启用"
        )


# ========== 配置管理接口 ==========

@router.get("/config", response_model=ConfigResponse, summary="获取数据中心配置")
async def get_config(
    current_user: User = Depends(get_current_user)
):
    """
    获取数据中心当前配置
    
    - **需要管理员权限**
    """
    check_admin_permission(current_user)
    
    result = ConfigService.get_config()
    return ConfigResponse(**result)


@router.put("/config", response_model=ConfigUpdateResponse, summary="更新数据中心配置")
async def update_config(
    request: ConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    更新数据中心配置
    
    - **需要管理员权限**
    - **注意**: 配置更新后需要重启数据中心才能生效
    - 自动备份原配置文件
    """
    check_admin_permission(current_user)
    
    result = await ConfigService.update_config(current_user.id, request.config, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return ConfigUpdateResponse(**result)

