#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_system.py
@Date       : 2025/10/23
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易系统管理相关API路由
"""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.web.core.security import get_current_user
from src.web.core.database import get_db
from src.web.models.user import User
from src.web.models.admin import Admin
from src.web.services.trading_system_service import TradingSystemService
from src.web.schemas.trading_system import (
    StartRequest, StartResponse,
    StopRequest, StopResponse,
    StatusResponse,
    LogsResponse
)

router = APIRouter(prefix="/trading-system", tags=["交易系统管理"])


def check_admin_permission(current_user):
    """检查管理员权限"""
    # 如果是Admin对象，直接允许（管理员登录）
    if isinstance(current_user, Admin):
        return
    
    # 如果是User对象，检查is_admin属性
    if isinstance(current_user, User):
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            return
    
    # 否则拒绝访问
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="需要管理员权限才能控制交易系统"
    )


# ========== 控制接口 ==========

@router.post("/start", response_model=StartResponse, summary="启动交易系统")
async def start_trading_system(
    request: StartRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    启动交易系统进程
    
    - **需要管理员权限**
    - 如果已在运行则返回错误
    - 返回进程PID
    """
    check_admin_permission(current_user)
    
    result = await TradingSystemService.start(current_user.id, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return StartResponse(**result)


@router.post("/stop", response_model=StopResponse, summary="停止交易系统")
async def stop_trading_system(
    request: StopRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    停止交易系统进程
    
    - **需要管理员权限**
    - **force**: 是否强制停止（SIGKILL），默认优雅停止（SIGTERM）
    - **timeout**: 等待超时时间（秒），默认30秒
    """
    check_admin_permission(current_user)
    
    result = await TradingSystemService.stop(
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


@router.post("/restart", response_model=StartResponse, summary="重启交易系统")
async def restart_trading_system(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    重启交易系统（先停止再启动）
    
    - **需要管理员权限**
    """
    check_admin_permission(current_user)
    
    result = await TradingSystemService.restart(current_user.id, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return StartResponse(**result)


# ========== 状态查询接口 ==========

@router.get("/status", response_model=StatusResponse, summary="获取交易系统状态")
async def get_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取交易系统详细运行状态
    
    返回信息：
    - **running**: 是否运行
    - **pid**: 进程ID
    - **cpu_percent**: CPU使用率
    - **memory_mb**: 内存使用(MB)
    - **memory_percent**: 内存使用率(%)
    - **create_time**: 启动时间(ISO格式)
    - **num_threads**: 线程数
    - **internal_status**: 交易系统内部状态（如果可用）
    """
    status_info = TradingSystemService.get_status()
    return StatusResponse(**status_info)


# ========== 日志查看接口 ==========

@router.get("/logs", response_model=LogsResponse, summary="获取交易系统日志")
async def get_logs(
    lines: int = 100,
    level: str = "all",
    since_line: int = None,
    current_user: User = Depends(get_current_user)
):
    """
    获取交易系统日志（支持增量查询）
    
    参数：
    - **lines**: 返回最后N行，默认100
    - **level**: 日志级别过滤，可选 all/INFO/WARNING/ERROR/DEBUG，默认all
    - **since_line**: 从第N行之后开始读取（用于增量更新），可选
    
    返回：
    - **success**: 是否成功
    - **logs**: 日志行数组
    - **total_lines**: 日志文件总行数
    - **log_file**: 日志文件名
    """
    result = TradingSystemService.get_logs(lines, level, since_line)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("message", "日志文件不存在")
        )
    
    return LogsResponse(**result)


@router.get("/logs/stream", summary="交易系统日志流（SSE）")
async def stream_logs(
    current_user: User = Depends(get_current_user)
):
    """
    交易系统日志实时流（Server-Sent Events）
    
    - 实时推送新增日志
    - 客户端使用 EventSource 接收
    - 自动重连机制
    
    返回格式：
    ```json
    {
        "timestamp": "2025-10-23 12:30:45",
        "level": "INFO",
        "context": "System",
        "message": "日志内容"
    }
    ```
    """
    from src.web.services.log_buffer import LogBuffer
    
    async def event_generator():
        """SSE事件生成器"""
        buffer = LogBuffer()
        last_position = 0
        
        try:
            while True:
                # 获取新日志
                new_logs = TradingSystemService.get_logs(lines=50, since_line=last_position)
                
                if new_logs["success"] and new_logs["logs"]:
                    # 更新位置
                    last_position = new_logs["total_lines"]
                    
                    # 发送日志
                    for log_line in new_logs["logs"]:
                        # 解析日志行
                        log_obj = parse_log_line(log_line)
                        
                        # 发送SSE事件
                        yield f"data: {json.dumps(log_obj, ensure_ascii=False)}\n\n"
                
                # 等待1秒再查询（避免过于频繁）
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            # 客户端断开连接
            pass
        except Exception as e:
            # 发送错误消息
            error_msg = {
                "timestamp": "",
                "level": "ERROR",
                "context": "SSE",
                "message": f"日志流异常: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )


def parse_log_line(line: str) -> dict:
    """
    解析日志行为结构化对象
    
    Args:
        line: 日志行字符串
        
    Returns:
        {"timestamp": str, "level": str, "context": str, "message": str}
    """
    import re
    from datetime import datetime
    
    # 日志格式: 2025-10-23 12:34:56.789 | INFO     | [Context] trace_id Module:method:line - Message
    log_patterns = [
        # 匹配格式1: YYYY-MM-DD HH:mm:ss.SSS | LEVEL | [Context] ...
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.,]\d{3})\s*\|\s*(\w+)\s*\|\s*\[([^\]]+)\](.*)$',
        # 匹配格式2: YYYY-MM-DD HH:mm:ss | LEVEL | [Context] ...
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*(\w+)\s*\|\s*\[([^\]]+)\](.*)$',
        # 匹配格式3: YYYY-MM-DD HH:mm:ss.SSS - LEVEL - ...
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-\s*(\w+)\s*-(.*)$'
    ]
    
    for pattern in log_patterns:
        match = re.match(pattern, line)
        if match:
            if len(match.groups()) == 4:
                timestamp = match.group(1)
                level = match.group(2).strip().upper()
                context = match.group(3).strip()
                message = match.group(4).strip()
            else:
                timestamp = match.group(1)
                level = match.group(2).strip().upper()
                context = "System"
                message = match.group(3).strip()
            
            return {
                "timestamp": timestamp,
                "level": level,
                "context": context,
                "message": message.lstrip("- ")
            }
    
    # 如果没有匹配到格式，返回原始日志行
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "level": "INFO",
        "context": "System",
        "message": line
    }

