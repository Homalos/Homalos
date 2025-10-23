#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_system_service.py
@Date       : 2025/10/23
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易系统进程管理服务
"""
import os
import sys
import json
import subprocess
import psutil  # type: ignore
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from src.utils.log import get_logger
from src.web.models.audit_log import AuditLog

logger = get_logger(__name__)


class TradingSystemService:
    """交易系统进程管理服务"""
    
    # 运行时文件路径
    _RUNTIME_DIR = Path("runtime")
    _PID_FILE = _RUNTIME_DIR / "trading_system.pid"
    _STATUS_FILE = _RUNTIME_DIR / "trading_system_status.json"
    _LOG_DIR = Path("logs")  # 日志目录
    
    @classmethod
    def _ensure_runtime_dir(cls):
        """确保运行时目录存在"""
        cls._RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        cls._LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    async def start(cls, user_id: int, db) -> Dict[str, Any]:
        """
        启动交易系统
        
        Args:
            user_id: 操作用户ID
            db: 数据库会话（AsyncSession）
            
        Returns:
            {"success": True/False, "message": str, "pid": int}
        """
        cls._ensure_runtime_dir()
        
        # 1. 检查是否已运行
        if cls.is_running():
            return {
                "success": False,
                "message": "交易系统已在运行中",
                "pid": cls.get_pid()
            }
        
        # 2. 启动进程
        try:
            # 获取Python解释器路径
            python_exe = sys.executable
            if not python_exe:
                python_exe = "python"
            
            # 获取start_homalos.py的绝对路径
            script_path = Path("start_homalos.py").absolute()
            if not script_path.exists():
                return {
                    "success": False,
                    "message": f"启动脚本不存在: {script_path}"
                }
            
            # Windows环境使用CREATE_NEW_PROCESS_GROUP创建独立进程组
            # 这样可以避免Web服务器停止时影响交易系统进程
            creationflags = 0
            # 准备环境变量
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'  # 强制使用UTF-8编码
            env['NO_COLOR'] = '1'              # 禁用彩色输出（通用标准）
            env['TERM'] = 'dumb'               # 设置终端类型为 dumb，禁用颜色
            
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                creationflags = 0
            
            # 启动交易系统进程
            # 注意：使用 DEVNULL 避免 Windows 上的管道关闭异常
            # 交易系统的日志已经通过 logger 写入到 homalos_YYYYMMDD.log
            process = subprocess.Popen(
                [python_exe, str(script_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                cwd=str(Path.cwd()),  # 设置工作目录
                env=env  # 传递环境变量
            )
            
            # 3. 记录PID
            cls._save_pid(process.pid)
            
            # 4. 记录审计日志
            await cls._log_operation(
                db=db,
                user_id=user_id,
                operation="start",
                target="trading_system",
                details=json.dumps({"pid": process.pid}),
                success=True
            )
            
            logger.info(f"交易系统启动成功 PID={process.pid}")
            
            # 5. 等待启动确认（简化版，检查进程是否存活）
            import time
            time.sleep(2)
            if psutil.pid_exists(process.pid):
                return {
                    "success": True,
                    "message": "交易系统启动成功",
                    "pid": process.pid
                }
            else:
                return {
                    "success": False,
                    "message": "交易系统启动后立即退出，请检查日志",
                    "pid": process.pid
                }
                
        except Exception as e:
            error_msg = f"启动失败: {e}"
            logger.error(error_msg, exc_info=True)
            await cls._log_operation(
                db=db,
                user_id=user_id,
                operation="start",
                target="trading_system",
                details=json.dumps({"error": str(e)}),
                success=False,
                error_message=error_msg
            )
            return {"success": False, "message": error_msg}
    
    @classmethod
    async def stop(cls, user_id: int, db, force: bool = False, timeout: int = 30) -> Dict[str, Any]:
        """
        停止交易系统
        
        Args:
            user_id: 操作用户ID
            db: 数据库会话（AsyncSession）
            force: 是否强制停止（SIGKILL）
            timeout: 等待超时时间（秒）
            
        Returns:
            {"success": True/False, "message": str}
        """
        pid = cls.get_pid()
        if not pid:
            return {"success": False, "message": "交易系统未运行"}
        
        try:
            process = psutil.Process(pid)
            
            if force:
                # 强制终止
                process.kill()
                action = "强制停止"
                logger.info(f"强制停止交易系统 PID={pid}")
            else:
                # 优雅停止（发送SIGTERM）
                process.terminate()
                action = "优雅停止"
                logger.info(f"发送SIGTERM信号到交易系统 PID={pid}")
                
                # 等待进程结束
                try:
                    process.wait(timeout=timeout)
                except psutil.TimeoutExpired:
                    return {
                        "success": False,
                        "message": f"停止超时({timeout}秒)，建议使用强制停止"
                    }
            
            # 清理PID文件和状态文件
            cls._remove_pid()
            cls._remove_status()
            
            # 审计日志
            await cls._log_operation(
                db=db,
                user_id=user_id,
                operation="stop",
                target="trading_system",
                details=json.dumps({"pid": pid, "force": force}),
                success=True
            )
            
            logger.info(f"交易系统已{action} PID={pid}")
            return {"success": True, "message": f"交易系统已{action}"}
            
        except psutil.NoSuchProcess:
            cls._remove_pid()
            cls._remove_status()
            return {"success": False, "message": "进程不存在，已清理PID文件"}
        except Exception as e:
            error_msg = f"停止失败: {e}"
            logger.error(error_msg, exc_info=True)
            await cls._log_operation(
                db=db,
                user_id=user_id,
                operation="stop",
                target="trading_system",
                details=json.dumps({"pid": pid, "error": str(e)}),
                success=False,
                error_message=error_msg
            )
            return {"success": False, "message": error_msg}
    
    @classmethod
    async def restart(cls, user_id: int, db) -> Dict[str, Any]:
        """
        重启交易系统
        
        Args:
            user_id: 操作用户ID
            db: 数据库会话（AsyncSession）
            
        Returns:
            {"success": True/False, "message": str}
        """
        logger.info("开始重启交易系统...")
        
        # 先停止
        stop_result = await cls.stop(user_id, db)
        if not stop_result["success"] and "未运行" not in stop_result["message"]:
            return stop_result
        
        # 等待2秒确保进程完全退出
        import asyncio
        await asyncio.sleep(2)
        
        # 再启动
        start_result = await cls.start(user_id, db)
        
        # 审计日志
        await cls._log_operation(
            db=db,
            user_id=user_id,
            operation="restart",
            target="trading_system",
            details=json.dumps({"success": start_result["success"]}),
            success=start_result["success"]
        )
        
        return start_result
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """
        获取交易系统详细状态
        
        Returns:
            包含运行状态、进程信息、内部状态的字典
        """
        pid = cls.get_pid()
        
        if not pid:
            return {
                "running": False,
                "message": "交易系统未运行"
            }
        
        try:
            process = psutil.Process(pid)
            
            # 进程基本信息
            info = {
                "running": True,
                "pid": pid,
                "status": process.status(),
                "cpu_percent": round(process.cpu_percent(interval=0.1), 1),
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
                "memory_percent": round(process.memory_percent(), 1),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                "num_threads": process.num_threads(),
            }
            
            # 读取交易系统内部状态文件（如果存在）
            internal_status = cls._read_status_file()
            if internal_status:
                info["internal_status"] = internal_status
            
            return info
            
        except psutil.NoSuchProcess:
            cls._remove_pid()
            return {"running": False, "message": "进程已不存在"}
        except Exception as e:
            logger.error(f"获取状态失败: {e}", exc_info=True)
            return {"running": False, "message": f"获取状态失败: {e}"}
    
    @classmethod
    def is_running(cls) -> bool:
        """检查交易系统是否运行"""
        pid = cls.get_pid()
        if not pid:
            return False
        
        try:
            return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
        except Exception:
            return False
    
    @classmethod
    def get_pid(cls) -> Optional[int]:
        """从PID文件读取进程ID"""
        if not cls._PID_FILE.exists():
            return None
        try:
            pid_str = cls._PID_FILE.read_text().strip()
            return int(pid_str) if pid_str else None
        except Exception as e:
            logger.error(f"读取PID文件失败: {e}")
            return None
    
    @classmethod
    def _save_pid(cls, pid: int):
        """保存PID到文件"""
        try:
            cls._ensure_runtime_dir()
            cls._PID_FILE.write_text(str(pid))
            logger.debug(f"PID已保存: {pid}")
        except Exception as e:
            logger.error(f"保存PID失败: {e}")
    
    @classmethod
    def _remove_pid(cls):
        """删除PID文件"""
        try:
            if cls._PID_FILE.exists():
                cls._PID_FILE.unlink()
                logger.debug("PID文件已删除")
        except Exception as e:
            logger.error(f"删除PID文件失败: {e}")
    
    @classmethod
    def _remove_status(cls):
        """删除状态文件"""
        try:
            if cls._STATUS_FILE.exists():
                cls._STATUS_FILE.unlink()
                logger.debug("状态文件已删除")
        except Exception as e:
            logger.error(f"删除状态文件失败: {e}")
    
    @classmethod
    def _read_status_file(cls) -> Optional[Dict[str, Any]]:
        """
        读取交易系统状态文件
        
        Returns:
            状态字典或None
        """
        try:
            if cls._STATUS_FILE.exists():
                content = cls._STATUS_FILE.read_text(encoding='utf-8')
                return json.loads(content)
        except Exception as e:
            logger.error(f"读取状态文件失败: {e}")
        return None
    
    @classmethod
    async def _log_operation(cls, db, user_id: int, operation: str, target: str,
                      details: str, success: bool = True, error_message: Optional[str] = None):
        """
        记录操作审计日志（同时写入数据库和日志文件）
        
        Args:
            db: 数据库会话（AsyncSession）
            user_id: 用户ID
            operation: 操作类型
            target: 操作目标
            details: 详情(JSON字符串)
            success: 是否成功
            error_message: 错误信息
        """
        try:
            # 1. 写入数据库
            audit_log = AuditLog(
                user_id=user_id,
                operation_type=operation,
                target=target,
                details=details,
                success=success,
                error_message=error_message
            )
            db.add(audit_log)
            await db.commit()  # 异步提交
            
            # 2. 写入日志文件
            log_msg = f"[审计] 用户{user_id} {operation} {target}: {details}"
            if error_message:
                log_msg += f" | 错误: {error_message}"
            
            if success:
                logger.info(log_msg)
            else:
                logger.error(log_msg)
                
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}", exc_info=True)
            # 不抛出异常，避免影响主流程
    
    @classmethod
    def _get_current_log_file(cls) -> Optional[Path]:
        """
        获取当前日期的日志文件路径
        
        Returns:
            日志文件路径或None
        """
        try:
            # 从日志配置中获取文件名格式
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            log_file = cls._LOG_DIR / f"homalos_{today}.log"
            
            if log_file.exists():
                return log_file
            
            # 如果当天日志不存在，尝试查找最新的日志文件
            log_files = sorted(cls._LOG_DIR.glob("homalos_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            if log_files:
                return log_files[0]
            
            return None
        except Exception as e:
            logger.error(f"查找日志文件失败: {e}")
            return None
    
    @classmethod
    def get_logs(cls, lines: int = 100, level: str = "all", since_line: Optional[int] = None) -> Dict[str, Any]:
        """
        获取交易系统日志（优化版：使用行数缓存和增量读取）
        
        Args:
            lines: 返回最后N行
            level: 日志级别过滤 (all/INFO/WARNING/ERROR/DEBUG)
            since_line: 从第N行之后开始读取（用于增量更新）
            
        Returns:
            {"success": True/False, "logs": list, "total_lines": int, "log_file": str}
        """
        log_file = cls._get_current_log_file()
        
        if not log_file:
            return {
                "success": False, 
                "message": "日志文件不存在",
                "logs": [],
                "total_lines": 0
            }
        
        try:
            # 优化1：快速统计总行数（不读取内容）
            total_lines = 0
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for _ in f:
                    total_lines += 1
            
            # 如果指定了 since_line，检查是否有新日志
            if since_line is not None and since_line >= 0:
                if since_line >= total_lines:
                    # 没有新日志，直接返回
                    return {
                        "success": True,
                        "logs": [],
                        "total_lines": total_lines,
                        "log_file": log_file.name
                    }
                
                # 优化2：只读取新增的行
                recent_lines = []
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f):
                        if i >= since_line:
                            recent_lines.append(line)
                        if i >= total_lines:  # 安全边界
                            break
            else:
                # 优化3：只读取最后N行（使用deque提高效率）
                from collections import deque
                recent_lines = deque(maxlen=lines)
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        recent_lines.append(line)
                recent_lines = list(recent_lines)
            
            # 过滤日志级别
            if level != "all":
                level_upper = level.upper()
                filtered_lines = []
                for line in recent_lines:
                    # 检查日志级别（支持常见格式）
                    if f" {level_upper} " in line or f"|{level_upper}|" in line or f"-{level_upper}-" in line:
                        filtered_lines.append(line)
                recent_lines = filtered_lines
            
            return {
                "success": True,
                "logs": [line.rstrip() for line in recent_lines],  # 移除行尾换行符
                "total_lines": total_lines,
                "log_file": log_file.name
            }
        except Exception as e:
            error_msg = f"读取日志失败: {e}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg, "logs": [], "total_lines": 0}

