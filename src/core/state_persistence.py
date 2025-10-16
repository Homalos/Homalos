#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : state_persistence.py
@Date       : 2025/10/16 15:00
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略状态持久化管理器

主要功能：
- 策略运行时状态的序列化和持久化
- 支持msgpack高性能二进制格式
- 自动保存和历史管理
- 状态恢复和清理
"""
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import msgpack

from src.utils.log.logger import get_logger


class StatePersistenceManager:
    """
    策略状态持久化管理器
    
    职责：
    - 将策略状态序列化为msgpack格式并保存到文件
    - 从文件加载状态并反序列化
    - 管理状态历史快照
    - 清理过期状态文件
    
    存储结构：
        data/strategy_states/
            _meta.msgpack                    # 元数据
            {strategy_id}/
                state_latest.msgpack         # 最新状态
                state_20251016_143000.msgpack  # 历史快照
    """
    
    def __init__(self, storage_dir: Path, max_history: int = 288):
        """
        初始化状态持久化管理器
        
        Args:
            storage_dir: 状态存储根目录
            max_history: 单个策略保留的最大历史记录数（默认288=24小时@5分钟间隔）
        """
        self.logger = get_logger("StatePersistence")
        self.storage_dir = Path(storage_dir)
        self.max_history = max_history
        
        # 确保存储目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 元数据文件
        self.meta_file = self.storage_dir / "_meta.msgpack"
        
        self.logger.info(f"状态持久化管理器已初始化: {self.storage_dir}")
    
    # ========== 序列化/反序列化 ==========
    
    def _serialize(self, data: dict) -> bytes:
        """
        将字典序列化为msgpack二进制格式
        
        Args:
            data: 要序列化的数据
            
        Returns:
            bytes: msgpack格式的二进制数据
        """
        try:
            return msgpack.packb(data, use_bin_type=True)
        except Exception as e:
            self.logger.error(f"序列化失败: {e}", exc_info=True)
            raise
    
    def _deserialize(self, data: bytes) -> dict:
        """
        从msgpack二进制格式反序列化为字典
        
        Args:
            data: msgpack格式的二进制数据
            
        Returns:
            dict: 反序列化后的数据
        """
        try:
            return msgpack.unpackb(data, raw=False)
        except Exception as e:
            self.logger.error(f"反序列化失败: {e}", exc_info=True)
            raise
    
    # ========== 文件操作 ==========
    
    def _get_strategy_dir(self, sid: str) -> Path:
        """获取策略的存储目录"""
        strategy_dir = self.storage_dir / sid
        strategy_dir.mkdir(parents=True, exist_ok=True)
        return strategy_dir
    
    def _get_latest_file(self, sid: str) -> Path:
        """获取最新状态文件路径"""
        return self._get_strategy_dir(sid) / "state_latest.msgpack"
    
    def _get_snapshot_filename(self, timestamp: datetime = None) -> str:
        """
        生成快照文件名
        
        Args:
            timestamp: 时间戳，默认使用当前时间
            
        Returns:
            str: 文件名，格式如 state_20251016_143000.msgpack
        """
        if timestamp is None:
            timestamp = datetime.now()
        return f"state_{timestamp.strftime('%Y%m%d_%H%M%S')}.msgpack"
    
    async def _write_file_atomic(self, file_path: Path, data: bytes):
        """
        原子性写入文件（先写临时文件，再重命名）
        
        Args:
            file_path: 目标文件路径
            data: 要写入的数据
        """
        temp_file = file_path.with_suffix('.tmp')
        
        try:
            # 异步写入临时文件
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, temp_file.write_bytes, data)
            
            # 原子性重命名
            await loop.run_in_executor(None, temp_file.replace, file_path)
            
        except Exception as e:
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()
            raise e
    
    async def _read_file(self, file_path: Path) -> Optional[bytes]:
        """
        异步读取文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bytes: 文件内容，如果文件不存在返回None
        """
        if not file_path.exists():
            return None
        
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, file_path.read_bytes)
        except Exception as e:
            self.logger.error(f"读取文件失败 {file_path}: {e}")
            return None
    
    # ========== 核心功能：保存状态 ==========
    
    async def save_strategy_state(self, sid: str, state: dict) -> bool:
        """
        保存单个策略的状态
        
        流程：
        1. 序列化状态为msgpack
        2. 保存为最新状态文件
        3. 创建历史快照
        4. 清理过期快照
        
        Args:
            sid: 策略ID
            state: 策略状态数据（必须可序列化）
            
        Returns:
            bool: 是否保存成功
        """
        if state is None:
            self.logger.debug(f"策略 {sid} 没有状态需要保存")
            return True
        
        try:
            # 1. 序列化
            serialized_data = self._serialize({
                "strategy_id": sid,
                "timestamp": time.time(),
                "state": state
            })
            
            # 2. 保存为最新状态
            latest_file = self._get_latest_file(sid)
            await self._write_file_atomic(latest_file, serialized_data)
            
            # 3. 创建历史快照
            snapshot_file = self._get_strategy_dir(sid) / self._get_snapshot_filename()
            await self._write_file_atomic(snapshot_file, serialized_data)
            
            # 4. 清理过期快照（保留最近max_history个）
            await self._cleanup_old_snapshots(sid)
            
            self.logger.debug(f"已保存策略 {sid} 的状态: {len(serialized_data)} bytes")
            return True
            
        except Exception as e:
            self.logger.error(f"保存策略 {sid} 状态失败: {e}", exc_info=True)
            return False
    
    async def save_all_states(self, states: Dict[str, dict]) -> Dict[str, bool]:
        """
        批量保存所有策略状态（并发执行）
        
        Args:
            states: 策略ID到状态的映射
            
        Returns:
            Dict[str, bool]: 每个策略的保存结果
        """
        if not states:
            return {}
        
        self.logger.info(f"开始批量保存 {len(states)} 个策略的状态...")
        
        # 并发保存
        tasks = [
            self.save_strategy_state(sid, state)
            for sid, state in states.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 构建结果映射
        result_dict = {}
        for sid, result in zip(states.keys(), results):
            if isinstance(result, Exception):
                self.logger.error(f"保存 {sid} 时发生异常: {result}")
                result_dict[sid] = False
            else:
                result_dict[sid] = result
        
        success_count = sum(1 for v in result_dict.values() if v)
        self.logger.info(f"批量保存完成: {success_count}/{len(states)} 成功")
        
        return result_dict
    
    # ========== 核心功能：加载状态 ==========
    
    async def load_strategy_state(self, sid: str, timestamp: str = None) -> Optional[dict]:
        """
        加载策略状态
        
        Args:
            sid: 策略ID
            timestamp: 可选，指定加载哪个历史快照（格式：20251016_143000）
            
        Returns:
            dict: 策略状态数据，如果不存在返回None
        """
        try:
            # 确定要加载的文件
            if timestamp:
                # 加载历史快照
                snapshot_file = self._get_strategy_dir(sid) / f"state_{timestamp}.msgpack"
                data = await self._read_file(snapshot_file)
                if data is None:
                    self.logger.warning(f"历史快照不存在: {snapshot_file}")
                    return None
            else:
                # 加载最新状态
                latest_file = self._get_latest_file(sid)
                data = await self._read_file(latest_file)
                if data is None:
                    self.logger.debug(f"策略 {sid} 没有保存的状态")
                    return None
            
            # 反序列化
            deserialized = self._deserialize(data)
            state = deserialized.get("state")
            
            self.logger.info(f"已加载策略 {sid} 的状态: {len(data)} bytes")
            return state
            
        except Exception as e:
            self.logger.error(f"加载策略 {sid} 状态失败: {e}", exc_info=True)
            return None
    
    # ========== 核心功能：历史管理 ==========
    
    async def get_state_history(self, sid: str, limit: int = 10) -> List[dict]:
        """
        获取策略的状态历史列表（元数据）
        
        Args:
            sid: 策略ID
            limit: 返回最近N条记录
            
        Returns:
            List[dict]: 历史记录列表，每条包含：
                - filename: 文件名
                - timestamp: 时间戳
                - size: 文件大小（字节）
                - created: 创建时间（ISO格式）
        """
        try:
            strategy_dir = self._get_strategy_dir(sid)
            
            # 查找所有快照文件
            snapshot_files = sorted(
                strategy_dir.glob("state_*.msgpack"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            # 排除latest文件
            snapshot_files = [f for f in snapshot_files if f.name != "state_latest.msgpack"]
            
            # 限制数量
            snapshot_files = snapshot_files[:limit]
            
            # 构建元数据
            history = []
            for file in snapshot_files:
                stat = file.stat()
                history.append({
                    "filename": file.name,
                    "timestamp": file.stem.replace("state_", ""),
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"获取策略 {sid} 历史失败: {e}")
            return []
    
    async def _cleanup_old_snapshots(self, sid: str):
        """
        清理单个策略的过期快照（保留最近max_history个）
        
        Args:
            sid: 策略ID
        """
        try:
            strategy_dir = self._get_strategy_dir(sid)
            
            # 获取所有快照文件（按修改时间排序）
            snapshot_files = sorted(
                [f for f in strategy_dir.glob("state_*.msgpack") 
                 if f.name != "state_latest.msgpack"],
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            # 删除超出max_history的文件
            if len(snapshot_files) > self.max_history:
                files_to_delete = snapshot_files[self.max_history:]
                
                loop = asyncio.get_event_loop()
                for file in files_to_delete:
                    await loop.run_in_executor(None, file.unlink)
                
                self.logger.debug(f"已清理 {sid} 的 {len(files_to_delete)} 个过期快照")
                
        except Exception as e:
            self.logger.warning(f"清理快照失败: {e}")
    
    async def cleanup_old_states(self, days: int = 30):
        """
        清理所有策略超过N天的旧状态
        
        Args:
            days: 保留最近N天的状态
        """
        self.logger.info(f"开始清理超过 {days} 天的旧状态...")
        
        cutoff_time = time.time() - (days * 24 * 3600)
        deleted_count = 0
        
        try:
            # 遍历所有策略目录
            for strategy_dir in self.storage_dir.iterdir():
                if not strategy_dir.is_dir() or strategy_dir.name.startswith("_"):
                    continue
                
                # 检查该策略的所有快照
                for file in strategy_dir.glob("state_*.msgpack"):
                    if file.name == "state_latest.msgpack":
                        continue
                    
                    # 检查文件修改时间
                    if file.stat().st_mtime < cutoff_time:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, file.unlink)
                        deleted_count += 1
            
            self.logger.info(f"清理完成，共删除 {deleted_count} 个过期状态文件")
            
        except Exception as e:
            self.logger.error(f"清理旧状态失败: {e}", exc_info=True)
    
    # ========== 工具方法 ==========
    
    def get_storage_info(self) -> dict:
        """
        获取存储信息统计
        
        Returns:
            dict: 包含策略数量、总文件数、总大小等信息
        """
        try:
            strategy_count = 0
            total_files = 0
            total_size = 0
            
            for strategy_dir in self.storage_dir.iterdir():
                if not strategy_dir.is_dir() or strategy_dir.name.startswith("_"):
                    continue
                
                strategy_count += 1
                
                for file in strategy_dir.glob("*.msgpack"):
                    total_files += 1
                    total_size += file.stat().st_size
            
            return {
                "storage_dir": str(self.storage_dir),
                "strategy_count": strategy_count,
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2)
            }
            
        except Exception as e:
            self.logger.error(f"获取存储信息失败: {e}")
            return {}

