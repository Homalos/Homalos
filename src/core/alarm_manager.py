#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : alarm_manager.py
@Date       : 2025/10/16 18:00
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 告警管理器 - 负责告警的创建、存储、通知和清理
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import aiosqlite

from src.utils.log.logger import get_logger


class AlarmManager:
    """
    告警管理器
    
    功能：
    - 告警事件的创建、存储、查询
    - 告警规则的触发检测
    - 通知器的管理和调度
    - 定时清理过期告警记录
    """
    
    def __init__(self, db_path: str, loop=None):
        """
        Args:
            db_path: 数据库文件路径
            loop: 事件循环
        """
        self.logger = get_logger("AlarmManager")
        self.db_path = db_path
        self.loop = loop
        
        # 通知器列表
        self._notifiers = []
        
        # 告警去重缓存 {alarm_key: last_trigger_time}
        self._alarm_cache: Dict[str, float] = {}
        self._cache_ttl = 60  # 1分钟内同类告警只触发一次
        
        # 告警配置缓存
        self._config: Dict[str, Any] = {}
        self._config_refresh_interval = 30  # 30秒刷新一次配置
        self._last_config_refresh = 0
        
        # 定时任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._config_refresh_task: Optional[asyncio.Task] = None
        
        self.logger.info(f"告警管理器初始化，数据库: {db_path}")
    
    async def startup(self):
        """启动告警管理器"""
        self.logger.info("告警管理器启动中...")
        
        # 加载配置
        await self._refresh_config()
        
        # 启动定时任务
        if self.loop:
            # 每小时清理一次过期告警
            self._cleanup_task = self.loop.create_task(self._cleanup_loop())
            # 每30秒刷新一次配置
            self._config_refresh_task = self.loop.create_task(self._config_refresh_loop())
            self.logger.info("告警管理器定时任务已启动")
        else:
            self.logger.warning("事件循环未设置，定时任务未启动")
        
        self.logger.info("告警管理器启动完成")
    
    async def shutdown(self):
        """关闭告警管理器"""
        self.logger.info("告警管理器关闭中...")
        
        # 停止定时任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._config_refresh_task:
            self._config_refresh_task.cancel()
            try:
                await self._config_refresh_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("告警管理器已关闭")
    
    def register_notifier(self, notifier):
        """
        注册通知器
        
        Args:
            notifier: 通知器实例，需要实现 async send_alarm(alarm_data) 方法
        """
        self._notifiers.append(notifier)
        self.logger.info(f"已注册通知器: {notifier.__class__.__name__}")
    
    async def trigger_alarm(
        self,
        alarm_type: str,
        severity: str,
        source: str,
        message: str,
        target: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> Optional[str]:
        """
        触发告警
        
        Args:
            alarm_type: 告警类型 (process_crash, high_cpu, high_memory, ws_disconnect, custom)
            severity: 严重程度 (info, warning, error, critical)
            source: 告警源 (strategy_manager, system_monitor, datacenter)
            message: 告警消息
            target: 目标对象 (策略ID、进程名等)
            details: 详细信息字典
        
        Returns:
            str: 告警ID，如果被去重则返回None
        """
        # 告警去重检查
        alarm_key = f"{alarm_type}:{source}:{target}"
        now = time.time()
        
        if alarm_key in self._alarm_cache:
            last_trigger = self._alarm_cache[alarm_key]
            if now - last_trigger < self._cache_ttl:
                self.logger.debug(f"告警被去重: {alarm_key}")
                return None
        
        # 更新缓存
        self._alarm_cache[alarm_key] = now
        
        # 创建告警记录
        alarm_id = str(uuid.uuid4())
        alarm_data = {
            "alarm_id": alarm_id,
            "alarm_type": alarm_type,
            "severity": severity,
            "source": source,
            "target": target,
            "message": message,
            "details": json.dumps(details) if details else None,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        
        # 保存到数据库
        try:
            await self._save_alarm(alarm_data)
            self.logger.info(f"告警已触发: [{severity}] {alarm_type} - {message}")
        except Exception as e:
            self.logger.error(f"保存告警失败: {e}", exc_info=True)
            return None
        
        # 发送通知（异步，不阻塞）
        for notifier in self._notifiers:
            try:
                asyncio.create_task(notifier.send_alarm(alarm_data))
            except Exception as e:
                self.logger.error(f"通知器 {notifier.__class__.__name__} 发送失败: {e}", exc_info=True)
        
        return alarm_id
    
    async def acknowledge_alarm(self, alarm_id: str) -> bool:
        """
        确认告警
        
        Args:
            alarm_id: 告警ID
        
        Returns:
            bool: 是否成功
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE alarm_records 
                    SET status = 'acknowledged', acknowledged_at = ?
                    WHERE alarm_id = ? AND status = 'active'
                    """,
                    (datetime.now().isoformat(), alarm_id)
                )
                await db.commit()
                self.logger.info(f"告警已确认: {alarm_id}")
                return True
        except Exception as e:
            self.logger.error(f"确认告警失败: {e}", exc_info=True)
            return False
    
    async def resolve_alarm(self, alarm_id: str) -> bool:
        """
        解决告警
        
        Args:
            alarm_id: 告警ID
        
        Returns:
            bool: 是否成功
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE alarm_records 
                    SET status = 'resolved', resolved_at = ?
                    WHERE alarm_id = ?
                    """,
                    (datetime.now().isoformat(), alarm_id)
                )
                await db.commit()
                self.logger.info(f"告警已解决: {alarm_id}")
                return True
        except Exception as e:
            self.logger.error(f"解决告警失败: {e}", exc_info=True)
            return False
    
    async def query_alarms(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        alarm_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        查询告警列表
        
        Args:
            status: 状态筛选
            severity: 严重程度筛选
            alarm_type: 类型筛选
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            page_size: 每页数量
        
        Returns:
            Dict: 包含 total, page, page_size, items
        """
        try:
            # 构建查询条件
            conditions = []
            params = []
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            if severity:
                conditions.append("severity = ?")
                params.append(severity)
            
            if alarm_type:
                conditions.append("alarm_type = ?")
                params.append(alarm_type)
            
            if start_date:
                conditions.append("created_at >= ?")
                params.append(start_date)
            
            if end_date:
                conditions.append("created_at <= ?")
                params.append(end_date)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # 查询总数
                cursor = await db.execute(
                    f"SELECT COUNT(*) as total FROM alarm_records WHERE {where_clause}",
                    params
                )
                row = await cursor.fetchone()
                total = row[0] if row else 0
                
                # 查询列表
                offset = (page - 1) * page_size
                cursor = await db.execute(
                    f"""
                    SELECT * FROM alarm_records 
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    params + [page_size, offset]
                )
                rows = await cursor.fetchall()
                
                items = []
                for row in rows:
                    item = dict(row)
                    # 解析details JSON
                    if item.get("details"):
                        try:
                            item["details"] = json.loads(item["details"])
                        except:
                            pass
                    items.append(item)
                
                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "items": items
                }
        except Exception as e:
            self.logger.error(f"查询告警失败: {e}", exc_info=True)
            return {"total": 0, "page": page, "page_size": page_size, "items": []}
    
    async def get_alarm_detail(self, alarm_id: str) -> Optional[Dict]:
        """获取告警详情"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM alarm_records WHERE alarm_id = ?",
                    (alarm_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    item = dict(row)
                    if item.get("details"):
                        try:
                            item["details"] = json.loads(item["details"])
                        except:
                            pass
                    return item
                return None
        except Exception as e:
            self.logger.error(f"获取告警详情失败: {e}", exc_info=True)
            return None
    
    async def get_alarm_stats(self) -> Dict[str, Any]:
        """获取告警统计"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # 按状态统计
                cursor = await db.execute(
                    "SELECT status, COUNT(*) as count FROM alarm_records GROUP BY status"
                )
                status_stats = {row["status"]: row["count"] for row in await cursor.fetchall()}
                
                # 按严重程度统计
                cursor = await db.execute(
                    "SELECT severity, COUNT(*) as count FROM alarm_records GROUP BY severity"
                )
                severity_stats = {row["severity"]: row["count"] for row in await cursor.fetchall()}
                
                # 按类型统计
                cursor = await db.execute(
                    "SELECT alarm_type, COUNT(*) as count FROM alarm_records GROUP BY alarm_type"
                )
                type_stats = {row["alarm_type"]: row["count"] for row in await cursor.fetchall()}
                
                # 今日告警数
                today = datetime.now().date().isoformat()
                cursor = await db.execute(
                    "SELECT COUNT(*) as count FROM alarm_records WHERE DATE(created_at) = ?",
                    (today,)
                )
                row = await cursor.fetchone()
                today_count = row[0] if row else 0
                
                # 未处理告警数
                cursor = await db.execute(
                    "SELECT COUNT(*) as count FROM alarm_records WHERE status = 'active'"
                )
                row = await cursor.fetchone()
                active_count = row[0] if row else 0
                
                return {
                    "status_stats": status_stats,
                    "severity_stats": severity_stats,
                    "type_stats": type_stats,
                    "today_count": today_count,
                    "active_count": active_count
                }
        except Exception as e:
            self.logger.error(f"获取告警统计失败: {e}", exc_info=True)
            return {}
    
    async def get_config(self) -> Dict[str, Any]:
        """获取告警配置"""
        if not self._config or time.time() - self._last_config_refresh > self._config_refresh_interval:
            await self._refresh_config()
        return self._config.copy()
    
    async def update_config(self, config: Dict[str, Any]) -> bool:
        """
        更新告警配置
        
        Args:
            config: 配置字典
        
        Returns:
            bool: 是否成功
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                for key, value in config.items():
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO alarm_config (config_key, config_value, updated_at)
                        VALUES (?, ?, ?)
                        """,
                        (key, json.dumps(value), datetime.now().isoformat())
                    )
                await db.commit()
            
            # 立即刷新缓存
            await self._refresh_config()
            self.logger.info(f"告警配置已更新: {list(config.keys())}")
            return True
        except Exception as e:
            self.logger.error(f"更新告警配置失败: {e}", exc_info=True)
            return False
    
    async def _save_alarm(self, alarm_data: Dict):
        """保存告警到数据库"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO alarm_records 
                (alarm_id, alarm_type, severity, source, target, message, details, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alarm_data["alarm_id"],
                    alarm_data["alarm_type"],
                    alarm_data["severity"],
                    alarm_data["source"],
                    alarm_data["target"],
                    alarm_data["message"],
                    alarm_data["details"],
                    alarm_data["status"],
                    alarm_data["created_at"]
                )
            )
            await db.commit()
    
    async def _refresh_config(self):
        """从数据库刷新配置"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT config_key, config_value FROM alarm_config")
                rows = await cursor.fetchall()
                
                self._config = {}
                for row in rows:
                    try:
                        self._config[row["config_key"]] = json.loads(row["config_value"])
                    except:
                        self._config[row["config_key"]] = row["config_value"]
                
                self._last_config_refresh = time.time()
                self.logger.debug(f"告警配置已刷新: {list(self._config.keys())}")
        except Exception as e:
            self.logger.error(f"刷新告警配置失败: {e}", exc_info=True)
    
    async def _cleanup_old_alarms(self):
        """清理过期告警记录"""
        try:
            # 获取保留天数配置
            retention_days = self._config.get("retention_days", 30)
            cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM alarm_records WHERE created_at < ?",
                    (cutoff_date,)
                )
                await db.commit()
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    self.logger.info(f"已清理 {deleted_count} 条超过 {retention_days} 天的告警记录")
        except Exception as e:
            self.logger.error(f"清理告警记录失败: {e}", exc_info=True)
    
    async def _cleanup_loop(self):
        """定时清理循环（每小时）"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1小时
                await self._cleanup_old_alarms()
            except asyncio.CancelledError:
                self.logger.info("告警清理任务被取消")
                break
            except Exception as e:
                self.logger.error(f"告警清理任务失败: {e}", exc_info=True)
    
    async def _config_refresh_loop(self):
        """配置刷新循环（每30秒）"""
        while True:
            try:
                await asyncio.sleep(self._config_refresh_interval)
                await self._refresh_config()
            except asyncio.CancelledError:
                self.logger.info("配置刷新任务被取消")
                break
            except Exception as e:
                self.logger.error(f"配置刷新任务失败: {e}", exc_info=True)

