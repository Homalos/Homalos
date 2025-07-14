#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : strategy_event_handler.py
@Date       : 2025/1/15 10:30
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略事件处理器 - 统一处理、路由、分发和持久化策略事件
"""
import asyncio
import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Set, Union

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.logger import get_logger


class EventPriority(Enum):
    """事件优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(Enum):
    """事件状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class EventFilter:
    """事件过滤器"""
    event_types: Optional[Set[str]] = None
    strategy_ids: Optional[Set[str]] = None
    priority: Optional[EventPriority] = None
    time_range: Optional[tuple] = None  # (start_time, end_time)
    status: Optional[EventStatus] = None
    tags: Optional[Set[str]] = None


@dataclass
class EventAggregate:
    """事件聚合"""
    event_type: str
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    strategy_ids: Set[str] = field(default_factory=set)
    total_duration: timedelta = field(default_factory=lambda: timedelta(0))
    avg_processing_time: float = 0.0
    success_rate: float = 0.0


@dataclass
class StoredEvent:
    """存储的事件"""
    id: Optional[int] = None
    event_type: str = ""
    strategy_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    status: EventStatus = EventStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    tags: Set[str] = field(default_factory=set)
    correlation_id: Optional[str] = None
    parent_event_id: Optional[int] = None


class StrategyEventHandler:
    """策略事件处理器"""
    
    def __init__(self, event_bus: EventBus, config: Optional[ConfigManager] = None):
        self.event_bus = event_bus
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
        
        # 配置
        self.db_path = "data/strategy_events.db"
        self.batch_size = 100
        self.flush_interval = 30  # 秒
        self.max_retries = 3
        self.retention_days = 30
        self.enable_persistence = True
        self.enable_aggregation = True
        
        # 事件处理器注册表
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.middleware: List[Callable] = []
        
        # 事件缓存和批处理
        self.event_buffer: List[StoredEvent] = []
        self.buffer_lock = asyncio.Lock()
        
        # 聚合数据
        self.event_aggregates: Dict[str, EventAggregate] = {}
        
        # 数据库连接
        self.db_connection: Optional[sqlite3.Connection] = None
        
        # 任务
        self.flush_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # 状态
        self.is_running = False
        
        # 加载配置
        self._load_config()
        
        # 初始化数据库
        if self.enable_persistence:
            self._init_database()
        
        # 注册默认事件处理器
        self._register_default_handlers()
    
    def _load_config(self):
        """加载配置"""
        if not self.config:
            return
        
        try:
            event_config = self.config.get("strategy_management.event_handling", {})
            self.db_path = event_config.get("db_path", self.db_path)
            self.batch_size = event_config.get("batch_size", self.batch_size)
            self.flush_interval = event_config.get("flush_interval", self.flush_interval)
            self.max_retries = event_config.get("max_retries", self.max_retries)
            self.retention_days = event_config.get("retention_days", self.retention_days)
            self.enable_persistence = event_config.get("enable_persistence", self.enable_persistence)
            self.enable_aggregation = event_config.get("enable_aggregation", self.enable_aggregation)
            
            self.logger.info(f"事件处理配置加载完成: 持久化={self.enable_persistence}, 聚合={self.enable_aggregation}")
        except Exception as e:
            self.logger.error(f"加载事件处理配置失败: {e}")
    
    def _init_database(self):
        """初始化数据库"""
        try:
            # 确保数据目录存在
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.db_connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.db_connection.row_factory = sqlite3.Row
            
            # 创建表
            self._create_tables()
            
            self.logger.info(f"事件数据库初始化完成: {self.db_path}")
        except Exception as e:
            self.logger.error(f"初始化事件数据库失败: {e}")
            self.enable_persistence = False
    
    def _create_tables(self):
        """创建数据库表"""
        cursor = self.db_connection.cursor()
        
        # 策略事件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                data TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                processed_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                tags TEXT,
                correlation_id TEXT,
                parent_event_id INTEGER,
                FOREIGN KEY (parent_event_id) REFERENCES strategy_events (id)
            )
        """)
        
        # 事件聚合表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_aggregates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                date DATE NOT NULL,
                count INTEGER NOT NULL,
                first_occurrence TIMESTAMP NOT NULL,
                last_occurrence TIMESTAMP NOT NULL,
                strategy_ids TEXT NOT NULL,
                total_duration_seconds REAL NOT NULL,
                avg_processing_time REAL NOT NULL,
                success_rate REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_type, date)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON strategy_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_strategy ON strategy_events(strategy_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON strategy_events(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON strategy_events(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_aggregates_type_date ON event_aggregates(event_type, date)")
        
        self.db_connection.commit()
    
    def _register_default_handlers(self):
        """注册默认事件处理器"""
        # 策略生命周期事件
        self.register_handler(EventType.STRATEGY_STARTED, self._handle_strategy_started)
        self.register_handler(EventType.STRATEGY_STOPPED, self._handle_strategy_stopped)
        self.register_handler(EventType.STRATEGY_ERROR, self._handle_strategy_error)
        
        # 策略验证和依赖检查事件
        self.register_handler(EventType.STRATEGY_DEPENDENCY_CHECK, self._handle_dependency_check)
        self.register_handler(EventType.STRATEGY_VALIDATION_PASSED, self._handle_validation_passed)
        self.register_handler(EventType.STRATEGY_VALIDATION_FAILED, self._handle_validation_failed)
        
        # 策略健康监控事件
        self.register_handler(EventType.STRATEGY_HEALTH_CHECK, self._handle_health_check)
        self.register_handler(EventType.STRATEGY_ANOMALY_DETECTED, self._handle_anomaly_detected)
        
        # 策略恢复事件
        self.register_handler(EventType.STRATEGY_RECOVERY_STARTED, self._handle_recovery_started)
        self.register_handler(EventType.STRATEGY_RECOVERY_COMPLETED, self._handle_recovery_completed)
        self.register_handler(EventType.STRATEGY_RECOVERY_FAILED, self._handle_recovery_failed)
        
        # 策略性能事件
        self.register_handler(EventType.STRATEGY_PERFORMANCE_UPDATE, self._handle_performance_update)
    
    async def start(self):
        """启动事件处理器"""
        if self.is_running:
            self.logger.warning("事件处理器已在运行")
            return
        
        self.is_running = True
        
        # 启动定时任务
        if self.enable_persistence:
            self.flush_task = asyncio.create_task(self._flush_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # 订阅所有策略相关事件
        strategy_events = [
            EventType.STRATEGY_STARTED, EventType.STRATEGY_STOPPED, EventType.STRATEGY_ERROR,
            EventType.STRATEGY_DEPENDENCY_CHECK, EventType.STRATEGY_VALIDATION_PASSED,
            EventType.STRATEGY_VALIDATION_FAILED, EventType.STRATEGY_HEALTH_CHECK,
            EventType.STRATEGY_ANOMALY_DETECTED, EventType.STRATEGY_RECOVERY_STARTED,
            EventType.STRATEGY_RECOVERY_COMPLETED, EventType.STRATEGY_RECOVERY_FAILED,
            EventType.STRATEGY_PERFORMANCE_UPDATE
        ]
        
        for event_type in strategy_events:
            self.event_bus.subscribe(event_type, self.handle_strategy_event)
        
        self.logger.info("策略事件处理器已启动")
    
    async def stop(self):
        """停止事件处理器"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 停止定时任务
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 刷新剩余事件
        if self.enable_persistence:
            await self._flush_events()
        
        # 关闭数据库连接
        if self.db_connection:
            self.db_connection.close()
        
        self.logger.info("策略事件处理器已停止")
    
    async def handle_strategy_event(self, event: Event):
        """处理策略事件"""
        try:
            # 创建存储事件
            stored_event = self._create_stored_event(event)
            
            # 应用中间件
            for middleware in self.middleware:
                stored_event = await middleware(stored_event)
                if stored_event is None:
                    return  # 中间件拦截了事件
            
            # 更新状态
            stored_event.status = EventStatus.PROCESSING
            stored_event.processed_at = datetime.now()
            
            # 执行事件处理器
            handlers = self.event_handlers.get(event.type, [])
            for handler in handlers:
                try:
                    await handler(stored_event)
                except Exception as e:
                    self.logger.error(f"事件处理器执行失败: {handler.__name__}, 错误: {e}")
                    stored_event.error_message = str(e)
                    stored_event.status = EventStatus.FAILED
            
            # 更新完成状态
            if stored_event.status == EventStatus.PROCESSING:
                stored_event.status = EventStatus.COMPLETED
                stored_event.completed_at = datetime.now()
            
            # 添加到缓冲区
            if self.enable_persistence:
                async with self.buffer_lock:
                    self.event_buffer.append(stored_event)
            
            # 更新聚合数据
            if self.enable_aggregation:
                self._update_aggregates(stored_event)
            
        except Exception as e:
            self.logger.error(f"处理策略事件失败: {e}")
    
    def register_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        self.logger.info(f"已注册事件处理器: {event_type} -> {handler.__name__}")
    
    def unregister_handler(self, event_type: str, handler: Callable):
        """取消注册事件处理器"""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
                self.logger.info(f"已取消注册事件处理器: {event_type} -> {handler.__name__}")
            except ValueError:
                pass
    
    def add_middleware(self, middleware: Callable):
        """添加中间件"""
        self.middleware.append(middleware)
        self.logger.info(f"已添加中间件: {middleware.__name__}")
    
    async def persist_event(self, event: StoredEvent) -> Optional[int]:
        """持久化单个事件"""
        if not self.enable_persistence or not self.db_connection:
            return None
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO strategy_events (
                    event_type, strategy_id, data, priority, status,
                    created_at, processed_at, completed_at, error_message,
                    retry_count, max_retries, tags, correlation_id, parent_event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_type, event.strategy_id, json.dumps(event.data),
                event.priority.value, event.status.value, event.created_at,
                event.processed_at, event.completed_at, event.error_message,
                event.retry_count, event.max_retries, 
                json.dumps(list(event.tags)) if event.tags else None,
                event.correlation_id, event.parent_event_id
            ))
            
            self.db_connection.commit()
            return cursor.lastrowid
            
        except Exception as e:
            self.logger.error(f"持久化事件失败: {e}")
            return None
    
    async def replay_events(self, 
                          event_filter: Optional[EventFilter] = None,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[StoredEvent]:
        """回放事件"""
        if not self.enable_persistence or not self.db_connection:
            return []
        
        try:
            query = "SELECT * FROM strategy_events WHERE 1=1"
            params = []
            
            # 构建查询条件
            if event_filter:
                if event_filter.event_types:
                    placeholders = ','.join(['?' for _ in event_filter.event_types])
                    query += f" AND event_type IN ({placeholders})"
                    params.extend(event_filter.event_types)
                
                if event_filter.strategy_ids:
                    placeholders = ','.join(['?' for _ in event_filter.strategy_ids])
                    query += f" AND strategy_id IN ({placeholders})"
                    params.extend(event_filter.strategy_ids)
                
                if event_filter.priority:
                    query += " AND priority = ?"
                    params.append(event_filter.priority.value)
                
                if event_filter.status:
                    query += " AND status = ?"
                    params.append(event_filter.status.value)
            
            if start_time:
                query += " AND created_at >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND created_at <= ?"
                params.append(end_time)
            
            query += " ORDER BY created_at ASC"
            
            cursor = self.db_connection.cursor()
            cursor.execute(query, params)
            
            events = []
            for row in cursor.fetchall():
                event = StoredEvent(
                    id=row['id'],
                    event_type=row['event_type'],
                    strategy_id=row['strategy_id'],
                    data=json.loads(row['data']) if row['data'] else {},
                    priority=EventPriority(row['priority']),
                    status=EventStatus(row['status']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    processed_at=datetime.fromisoformat(row['processed_at']) if row['processed_at'] else None,
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    error_message=row['error_message'],
                    retry_count=row['retry_count'],
                    max_retries=row['max_retries'],
                    tags=set(json.loads(row['tags'])) if row['tags'] else set(),
                    correlation_id=row['correlation_id'],
                    parent_event_id=row['parent_event_id']
                )
                events.append(event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"回放事件失败: {e}")
            return []
    
    def get_event_statistics(self, 
                           strategy_id: Optional[str] = None,
                           event_type: Optional[str] = None,
                           time_range: Optional[tuple] = None) -> Dict[str, Any]:
        """获取事件统计信息"""
        if not self.enable_persistence or not self.db_connection:
            return {}
        
        try:
            query = "SELECT COUNT(*) as total, status, AVG(julianday(completed_at) - julianday(created_at)) * 86400 as avg_duration FROM strategy_events WHERE 1=1"
            params = []
            
            if strategy_id:
                query += " AND strategy_id = ?"
                params.append(strategy_id)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            if time_range:
                query += " AND created_at BETWEEN ? AND ?"
                params.extend(time_range)
            
            query += " GROUP BY status"
            
            cursor = self.db_connection.cursor()
            cursor.execute(query, params)
            
            stats = {
                'total_events': 0,
                'completed_events': 0,
                'failed_events': 0,
                'pending_events': 0,
                'avg_processing_time': 0.0,
                'success_rate': 0.0
            }
            
            for row in cursor.fetchall():
                status = row['status']
                count = row['total']
                avg_duration = row['avg_duration'] or 0
                
                stats['total_events'] += count
                
                if status == EventStatus.COMPLETED.value:
                    stats['completed_events'] = count
                    stats['avg_processing_time'] = avg_duration
                elif status == EventStatus.FAILED.value:
                    stats['failed_events'] = count
                elif status == EventStatus.PENDING.value:
                    stats['pending_events'] = count
            
            if stats['total_events'] > 0:
                stats['success_rate'] = stats['completed_events'] / stats['total_events'] * 100
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取事件统计失败: {e}")
            return {}
    
    def get_aggregates(self, 
                      event_type: Optional[str] = None,
                      date_range: Optional[tuple] = None) -> List[EventAggregate]:
        """获取事件聚合数据"""
        if not self.enable_aggregation:
            return list(self.event_aggregates.values())
        
        if not self.enable_persistence or not self.db_connection:
            return []
        
        try:
            query = "SELECT * FROM event_aggregates WHERE 1=1"
            params = []
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            if date_range:
                query += " AND date BETWEEN ? AND ?"
                params.extend(date_range)
            
            query += " ORDER BY date DESC"
            
            cursor = self.db_connection.cursor()
            cursor.execute(query, params)
            
            aggregates = []
            for row in cursor.fetchall():
                aggregate = EventAggregate(
                    event_type=row['event_type'],
                    count=row['count'],
                    first_occurrence=datetime.fromisoformat(row['first_occurrence']),
                    last_occurrence=datetime.fromisoformat(row['last_occurrence']),
                    strategy_ids=set(json.loads(row['strategy_ids'])),
                    total_duration=timedelta(seconds=row['total_duration_seconds']),
                    avg_processing_time=row['avg_processing_time'],
                    success_rate=row['success_rate']
                )
                aggregates.append(aggregate)
            
            return aggregates
            
        except Exception as e:
            self.logger.error(f"获取聚合数据失败: {e}")
            return []
    
    def _create_stored_event(self, event: Event) -> StoredEvent:
        """创建存储事件"""
        strategy_id = event.data.get('strategy_id', '') if event.data else ''
        
        # 确定优先级
        priority = EventPriority.NORMAL
        if event.type in [EventType.STRATEGY_ERROR, EventType.STRATEGY_ANOMALY_DETECTED]:
            priority = EventPriority.HIGH
        elif event.type in [EventType.STRATEGY_RECOVERY_FAILED]:
            priority = EventPriority.CRITICAL
        
        return StoredEvent(
            event_type=event.type,
            strategy_id=strategy_id,
            data=event.data or {},
            priority=priority,
            status=EventStatus.PENDING,
            created_at=event.timestamp or datetime.now(),
            correlation_id=event.trace_id
        )
    
    def _update_aggregates(self, event: StoredEvent):
        """更新聚合数据"""
        try:
            key = event.event_type
            now = datetime.now()
            
            if key not in self.event_aggregates:
                self.event_aggregates[key] = EventAggregate(
                    event_type=event.event_type,
                    count=0,
                    first_occurrence=now,
                    last_occurrence=now
                )
            
            aggregate = self.event_aggregates[key]
            aggregate.count += 1
            aggregate.last_occurrence = now
            aggregate.strategy_ids.add(event.strategy_id)
            
            # 计算处理时间
            if event.completed_at and event.created_at:
                duration = (event.completed_at - event.created_at).total_seconds()
                aggregate.total_duration += timedelta(seconds=duration)
                aggregate.avg_processing_time = aggregate.total_duration.total_seconds() / aggregate.count
            
            # 计算成功率（简化版本）
            if event.status == EventStatus.COMPLETED:
                # 这里需要更复杂的逻辑来计算实际成功率
                pass
            
        except Exception as e:
            self.logger.error(f"更新聚合数据失败: {e}")
    
    async def _flush_events(self):
        """刷新事件到数据库"""
        if not self.enable_persistence or not self.event_buffer:
            return
        
        async with self.buffer_lock:
            events_to_flush = self.event_buffer[:self.batch_size]
            self.event_buffer = self.event_buffer[self.batch_size:]
        
        if not events_to_flush:
            return
        
        try:
            cursor = self.db_connection.cursor()
            
            for event in events_to_flush:
                cursor.execute("""
                    INSERT INTO strategy_events (
                        event_type, strategy_id, data, priority, status,
                        created_at, processed_at, completed_at, error_message,
                        retry_count, max_retries, tags, correlation_id, parent_event_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_type, event.strategy_id, json.dumps(event.data),
                    event.priority.value, event.status.value, event.created_at,
                    event.processed_at, event.completed_at, event.error_message,
                    event.retry_count, event.max_retries,
                    json.dumps(list(event.tags)) if event.tags else None,
                    event.correlation_id, event.parent_event_id
                ))
            
            self.db_connection.commit()
            self.logger.debug(f"已刷新 {len(events_to_flush)} 个事件到数据库")
            
        except Exception as e:
            self.logger.error(f"刷新事件到数据库失败: {e}")
    
    async def _flush_loop(self):
        """定时刷新循环"""
        while self.is_running:
            try:
                await self._flush_events()
                await asyncio.sleep(self.flush_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"刷新循环异常: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self):
        """定时清理循环"""
        while self.is_running:
            try:
                await self._cleanup_old_events()
                await asyncio.sleep(3600)  # 每小时清理一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"清理循环异常: {e}")
                await asyncio.sleep(300)  # 5分钟后重试
    
    async def _cleanup_old_events(self):
        """清理旧事件"""
        if not self.enable_persistence or not self.db_connection:
            return
        
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM strategy_events WHERE created_at < ?", (cutoff_date,))
            deleted_count = cursor.rowcount
            
            cursor.execute("DELETE FROM event_aggregates WHERE date < ?", (cutoff_date.date(),))
            deleted_aggregates = cursor.rowcount
            
            self.db_connection.commit()
            
            if deleted_count > 0 or deleted_aggregates > 0:
                self.logger.info(f"已清理 {deleted_count} 个旧事件和 {deleted_aggregates} 个旧聚合记录")
            
        except Exception as e:
            self.logger.error(f"清理旧事件失败: {e}")
    
    # 默认事件处理器
    async def _handle_strategy_started(self, event: StoredEvent):
        """处理策略启动事件"""
        self.logger.info(f"策略启动: {event.strategy_id}")
    
    async def _handle_strategy_stopped(self, event: StoredEvent):
        """处理策略停止事件"""
        self.logger.info(f"策略停止: {event.strategy_id}")
    
    async def _handle_strategy_error(self, event: StoredEvent):
        """处理策略错误事件"""
        self.logger.error(f"策略错误: {event.strategy_id}, 详情: {event.data}")
    
    async def _handle_dependency_check(self, event: StoredEvent):
        """处理依赖检查事件"""
        self.logger.info(f"依赖检查: {event.strategy_id}, 结果: {event.data.get('status')}")
    
    async def _handle_validation_passed(self, event: StoredEvent):
        """处理验证通过事件"""
        self.logger.info(f"策略验证通过: {event.strategy_id}")
    
    async def _handle_validation_failed(self, event: StoredEvent):
        """处理验证失败事件"""
        self.logger.warning(f"策略验证失败: {event.strategy_id}, 原因: {event.data.get('reason')}")
    
    async def _handle_health_check(self, event: StoredEvent):
        """处理健康检查事件"""
        status = event.data.get('status')
        if status in ['critical', 'warning']:
            self.logger.warning(f"策略健康状态异常: {event.strategy_id}, 状态: {status}")
    
    async def _handle_anomaly_detected(self, event: StoredEvent):
        """处理异常检测事件"""
        anomaly_type = event.data.get('anomaly_type')
        severity = event.data.get('severity')
        self.logger.warning(f"检测到策略异常: {event.strategy_id}, 类型: {anomaly_type}, 严重程度: {severity}")
    
    async def _handle_recovery_started(self, event: StoredEvent):
        """处理恢复开始事件"""
        self.logger.info(f"策略恢复开始: {event.strategy_id}, 异常类型: {event.data.get('anomaly_type')}")
    
    async def _handle_recovery_completed(self, event: StoredEvent):
        """处理恢复完成事件"""
        self.logger.info(f"策略恢复完成: {event.strategy_id}")
    
    async def _handle_recovery_failed(self, event: StoredEvent):
        """处理恢复失败事件"""
        reason = event.data.get('reason')
        self.logger.error(f"策略恢复失败: {event.strategy_id}, 原因: {reason}")
    
    async def _handle_performance_update(self, event: StoredEvent):
        """处理性能更新事件"""
        performance_data = event.data.get('performance', {})
        self.logger.debug(f"策略性能更新: {event.strategy_id}, 数据: {performance_data}")