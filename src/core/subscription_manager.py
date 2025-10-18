#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : subscription_manager.py
@Date       : 2025/10/17 15:00
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 订阅管理器 - 负责收集和管理所有策略的订阅信息
"""
import asyncio
from collections import defaultdict
from threading import Lock
from typing import Any

from src.core.constants import Interval
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.utils.log.logger import get_logger


class SubscriptionManager:
    """
    订阅管理器
    
    功能：
    - 收集所有策略实例的订阅信息（合约、K线周期等）
    - 统一向行情网关发送订阅请求
    - 向K线合成器发送订阅配置
    - 管理订阅状态和动态更新
    """
    
    def __init__(self, event_bus: EventBus):
        self.logger = get_logger(self.__class__.__name__)
        self.event_bus = event_bus
        
        # 策略订阅信息 {strategy_id: {instruments: set, intervals: set}}
        self._strategy_subscriptions: dict[str, dict[str, set]] = {}
        
        # 全局合约订阅状态 {instrument_id: subscriber_count}
        self._instrument_subscribers: dict[str, int] = defaultdict(int)
        
        # 全局K线订阅状态 {instrument_id: {interval: subscriber_count}}
        self._kline_subscribers: dict[str, dict[Interval, int]] = defaultdict(lambda: defaultdict(int))
        
        # 已订阅的合约（避免重复订阅）
        self._subscribed_instruments: set[str] = set()
        
        # 线程锁
        self._lock = Lock()
        
        # 订阅状态
        self._subscription_active = False
        
        # 网关就绪状态（新增）
        self._md_gateway_ready = False  # 行情网关就绪
        self._td_gateway_ready = False  # 交易网关就绪
        self._contracts_loaded = False  # 合约信息已加载
        
        # 待处理的订阅请求缓存（在网关未就绪时缓存）
        self._pending_subscriptions: dict[str, dict[str, Any]] = {}
        
        self.logger.info("订阅管理器初始化完成")
    
    async def startup(self):
        """启动订阅管理器"""
        self.logger.info("订阅管理器启动中...")
        
        # 订阅策略相关事件
        self.event_bus.subscribe(EventType.STRATEGY_SUBSCRIPTION_UPDATE, self._handle_subscription_update)
        self.event_bus.subscribe(EventType.STRATEGY_LOADED, self._handle_strategy_loaded)
        self.event_bus.subscribe(EventType.STRATEGY_UNLOADED, self._handle_strategy_unloaded)
        
        # 订阅网关就绪事件（新增）
        self.event_bus.subscribe(EventType.MD_GATEWAY_LOGIN, self._handle_md_gateway_login)
        self.event_bus.subscribe(EventType.TD_CONFIRM_SUCCESS, self._handle_td_gateway_ready)
        self.event_bus.subscribe(EventType.TD_QRY_INS, self._handle_contracts_loaded)
        
        self._subscription_active = True
        self.logger.info("订阅管理器启动完成")
    
    async def shutdown(self):
        """关闭订阅管理器"""
        self.logger.info("订阅管理器关闭中...")
        
        # 取消所有订阅
        await self._unsubscribe_all()
        
        self._subscription_active = False
        self.logger.info("订阅管理器已关闭")
    
    def register_strategy_subscription(
            self,
            strategy_id: str,
            instruments: list[str],
            intervals: list[Interval]
    ):
        """
        注册策略订阅信息
        
        Args:
            strategy_id: 策略ID
            instruments: 订阅的合约列表
            intervals: 订阅的K线周期列表
        """
        with self._lock:
            # 记录策略订阅信息
            self._strategy_subscriptions[strategy_id] = {
                'instruments': set(instruments),
                'intervals': set(intervals)
            }
            
            # 更新全局订阅计数
            for instrument in instruments:
                self._instrument_subscribers[instrument] += 1
                
                for interval in intervals:
                    self._kline_subscribers[instrument][interval] += 1
            
            self.logger.info(f"策略 {strategy_id} 订阅信息已注册: 合约{len(instruments)}个, K线周期{len(intervals)}个")
            
            # 检查网关是否就绪
            if not self._is_ready_to_subscribe():
                # 缓存待处理的订阅请求
                self._pending_subscriptions[strategy_id] = {
                    'instruments': instruments,
                    'intervals': intervals
                }
                self.logger.info(f"网关尚未完全就绪，策略 {strategy_id} 的订阅请求已缓存，等待网关就绪后处理")
                self._log_gateway_status()
                return
            
            # 如果网关已就绪，立即发送订阅请求
            new_instruments = [inst for inst in instruments if inst not in self._subscribed_instruments]
            if new_instruments:
                self._publish_subscription_requests(new_instruments)
    
    def unregister_strategy_subscription(self, strategy_id: str):
        """
        取消策略订阅信息
        
        Args:
            strategy_id: 策略ID
        """
        with self._lock:
            if strategy_id not in self._strategy_subscriptions:
                return
            
            subscription_info = self._strategy_subscriptions[strategy_id]
            instruments = subscription_info['instruments']
            intervals = subscription_info['intervals']
            
            # 更新全局订阅计数
            instruments_to_unsubscribe = []
            for instrument in instruments:
                self._instrument_subscribers[instrument] -= 1
                
                # 如果没有策略订阅这个合约了，标记为需要取消订阅
                if self._instrument_subscribers[instrument] <= 0:
                    del self._instrument_subscribers[instrument]
                    instruments_to_unsubscribe.append(instrument)
                    self._subscribed_instruments.discard(instrument)
                
                # 更新K线订阅计数
                for interval in intervals:
                    self._kline_subscribers[instrument][interval] -= 1
                    if self._kline_subscribers[instrument][interval] <= 0:
                        del self._kline_subscribers[instrument][interval]
                
                # 如果这个合约没有K线订阅了，清理
                if not self._kline_subscribers[instrument]:
                    del self._kline_subscribers[instrument]
            
            # 删除策略订阅记录
            del self._strategy_subscriptions[strategy_id]
            
            self.logger.info(f"策略 {strategy_id} 订阅信息已取消")
            
            # 取消不再需要的合约订阅
            if instruments_to_unsubscribe:
                asyncio.create_task(self._unsubscribe_instruments(instruments_to_unsubscribe))
    
    def get_all_subscribed_instruments(self) -> set[str]:
        """获取所有订阅的合约"""
        with self._lock:
            return set(self._instrument_subscribers.keys())
    
    def get_kline_subscription_map(self) -> dict[str, list[Interval]]:
        """
        获取K线订阅映射
        
        Returns:
            dict[str, list[Interval]]: {instrument_id: [intervals]}
        """
        with self._lock:
            result = {}
            for instrument, intervals_dict in self._kline_subscribers.items():
                result[instrument] = list(intervals_dict.keys())
            return result
    
    def get_subscription_stats(self) -> dict[str, Any]:
        """获取订阅统计信息"""
        with self._lock:
            return {
                "total_strategies": len(self._strategy_subscriptions),
                "total_instruments": len(self._instrument_subscribers),
                "total_kline_subscriptions": sum(
                    len(intervals) for intervals in self._kline_subscribers.values()
                ),
                "strategy_subscriptions": {
                    sid: {
                        "instruments": list(info["instruments"]),
                        "intervals": [interval.value for interval in info["intervals"]]
                    } for sid, info in self._strategy_subscriptions.items()
                }
            }
    
    def _publish_subscription_requests(self, instruments: list[str]):
        """
        通过事件总线发送订阅请求（线程安全，同步方法）
        
        Args:
            instruments: 待订阅的合约列表
        """
        if not self._subscription_active:
            self.logger.warning("订阅管理器未激活，跳过订阅请求")
            return
        
        self.logger.info(f"开始发送订阅请求: {len(instruments)} 个合约")
        
        try:
            # 逐个发送订阅事件到事件总线
            for instrument in instruments:
                try:
                    # 发送订阅事件给行情网关
                    event = Event(
                        EventType.MARKET_SUBSCRIBE_REQUEST,
                        payload={
                            "instrument_id": instrument,
                            "action": "subscribe"
                        }
                    )
                    self.event_bus.publish(event)
                    
                    # 标记为已订阅
                    self._subscribed_instruments.add(instrument)
                    self.logger.info(f"✓ 已发送合约订阅请求: {instrument}")
                    
                except Exception as e:
                    self.logger.error(f"✗ 订阅合约 {instrument} 失败: {e}", exc_info=True)
            
            # 发送K线配置更新事件
            self._publish_kline_config_update()
            
            self.logger.info(f"订阅请求发送完成: 成功 {len(instruments)} 个合约")
            
        except Exception as e:
            self.logger.error(f"批量发送订阅请求失败: {e}", exc_info=True)
    
    def _publish_kline_config_update(self):
        """
        发送K线配置更新事件（线程安全，同步方法）
        """
        try:
            kline_config = self.get_kline_subscription_map()
            
            # 发送配置更新事件给K线合成器
            event = Event(
                EventType.KLINE_CONFIG_UPDATE,
                payload={
                    "subscription_map": kline_config
                }
            )
            self.event_bus.publish(event)
            
            self.logger.info(f"✓ 已发送K线配置更新: {len(kline_config)} 个合约")
            
        except Exception as e:
            self.logger.error(f"✗ 发送K线配置更新失败: {e}", exc_info=True)
    
    async def _subscribe_instruments(self, instruments: list[str]):
        """
        向行情网关发送订阅请求（异步方法，保留供其他地方使用）
        
        注意：此方法现在主要由 _publish_subscription_requests 替代
        """
        if not self._subscription_active:
            return
        
        for instrument in instruments:
            try:
                # 发送订阅事件给行情网关
                event = Event(
                    EventType.MARKET_SUBSCRIBE_REQUEST,
                    payload={
                        "instrument_id": instrument,
                        "action": "subscribe"
                    }
                )
                self.event_bus.publish(event)
                
                self._subscribed_instruments.add(instrument)
                self.logger.info(f"已发送合约订阅请求: {instrument}")
                
            except Exception as e:
                self.logger.error(f"订阅合约 {instrument} 失败: {e}", exc_info=True)
        
        # 更新K线合成器配置
        await self._update_kline_generator_config()
    
    async def _unsubscribe_instruments(self, instruments: list[str]):
        """取消合约订阅"""
        for instrument in instruments:
            try:
                # 发送取消订阅事件给行情网关
                event = Event(
                    EventType.MARKET_SUBSCRIBE_REQUEST,
                    payload={
                        "instrument_id": instrument,
                        "action": "unsubscribe"
                    }
                )
                self.event_bus.publish(event)
                
                self.logger.info(f"已取消合约订阅: {instrument}")
                
            except Exception as e:
                self.logger.error(f"取消订阅合约 {instrument} 失败: {e}", exc_info=True)
        
        # 更新K线合成器配置
        await self._update_kline_generator_config()
    
    async def _update_kline_generator_config(self):
        """更新K线合成器配置"""
        try:
            kline_config = self.get_kline_subscription_map()
            
            # 发送配置更新事件给K线合成器
            event = Event(
                EventType.KLINE_CONFIG_UPDATE,
                payload={
                    "subscription_map": kline_config
                }
            )
            self.event_bus.publish(event)
            
            self.logger.info(f"已更新K线合成器配置: {len(kline_config)} 个合约")
            
        except Exception as e:
            self.logger.error(f"更新K线合成器配置失败: {e}", exc_info=True)
    
    async def _unsubscribe_all(self):
        """取消所有订阅"""
        with self._lock:
            all_instruments = list(self._subscribed_instruments)
        
        if all_instruments:
            await self._unsubscribe_instruments(all_instruments)
    
    def _handle_subscription_update(self, event: Event):
        """处理策略订阅更新事件"""
        try:
            payload = event.payload.get("data", {}) if hasattr(event.payload, 'get') else event.payload
            strategy_id = payload.get("strategy_id")
            instruments = payload.get("instruments", [])
            intervals_data = payload.get("intervals", [])
            
            # 转换intervals数据
            intervals = []
            for interval_data in intervals_data:
                if isinstance(interval_data, str):
                    # 如果是字符串，尝试转换为Interval枚举
                    try:
                        intervals.append(Interval(interval_data))
                    except ValueError:
                        self.logger.warning(f"无效的K线周期: {interval_data}")
                elif isinstance(interval_data, Interval):
                    intervals.append(interval_data)
            
            if strategy_id and (instruments or intervals):
                self.register_strategy_subscription(strategy_id, instruments, intervals)
            
        except Exception as e:
            self.logger.error(f"处理订阅更新事件失败: {e}", exc_info=True)
    
    def _handle_strategy_loaded(self, event: Event):
        """处理策略加载事件"""
        try:
            payload = event.payload.get("data", {}) if hasattr(event.payload, 'get') else event.payload
            strategy_id = payload.get("strategy_id")
            
            if strategy_id:
                self.logger.info(f"策略 {strategy_id} 已加载，等待订阅信息")
            
        except Exception as e:
            self.logger.error(f"处理策略加载事件失败: {e}", exc_info=True)
    
    def _handle_strategy_unloaded(self, event: Event):
        """处理策略卸载事件"""
        try:
            payload = event.payload.get("data", {}) if hasattr(event.payload, 'get') else event.payload
            strategy_id = payload.get("strategy_id")
            
            if strategy_id:
                self.unregister_strategy_subscription(strategy_id)
            
        except Exception as e:
            self.logger.error(f"处理策略卸载事件失败: {e}", exc_info=True)
    
    def _is_ready_to_subscribe(self) -> bool:
        """
        检查是否可以开始订阅
        
        Returns:
            bool: True表示所有条件已满足，可以订阅
        """
        return self._md_gateway_ready and self._td_gateway_ready and self._contracts_loaded
    
    def _log_gateway_status(self):
        """记录网关状态"""
        self.logger.info(f"网关状态 - 行情网关: {'✓' if self._md_gateway_ready else '✗'}, "
                        f"交易网关: {'✓' if self._td_gateway_ready else '✗'}, "
                        f"合约加载: {'✓' if self._contracts_loaded else '✗'}")
    
    def _process_pending_subscriptions(self):
        """
        处理所有待处理的订阅请求
        """
        if not self._pending_subscriptions:
            self.logger.debug("没有待处理的订阅请求")
            return
        
        self.logger.info(f"网关已完全就绪，开始处理 {len(self._pending_subscriptions)} 个待处理的订阅请求")
        
        # 收集所有待订阅的合约
        all_instruments = []
        for strategy_id, sub_info in self._pending_subscriptions.items():
            instruments = sub_info['instruments']
            new_instruments = [inst for inst in instruments if inst not in self._subscribed_instruments]
            all_instruments.extend(new_instruments)
            self.logger.info(f"  - 策略 {strategy_id}: {len(instruments)} 个合约")
        
        # 去重
        unique_instruments = list(set(all_instruments))
        
        if unique_instruments:
            self.logger.info(f"开始订阅合约: {len(unique_instruments)} 个（去重后）")
            self._publish_subscription_requests(unique_instruments)
        
        # 清空待处理队列
        self._pending_subscriptions.clear()
        self.logger.info("✓ 所有待处理的订阅请求已发送")
    
    def _handle_md_gateway_login(self, event: Event):
        """
        处理行情网关登录事件
        
        Args:
            event: 行情网关登录事件
        """
        try:
            data = event.payload
            
            if not data or data.get("code") != 0:
                self._md_gateway_ready = False
                self.logger.warning("行情网关登录失败")
                return
            
            was_ready_before = self._is_ready_to_subscribe()
            self._md_gateway_ready = True
            self.logger.info("✓ 行情网关已就绪")
            
            # 如果这是重连（之前已经订阅过），则重新订阅
            if len(self._subscribed_instruments) > 0:
                self.logger.info(f"检测到行情网关重新登录，准备重新订阅 {len(self._subscribed_instruments)} 个合约")
                instruments_to_resubscribe = list(self._subscribed_instruments)
                self._subscribed_instruments.clear()
                self._publish_subscription_requests(instruments_to_resubscribe)
                return
            
            # 检查是否所有网关都就绪，如果是，则处理待处理的订阅
            if not was_ready_before and self._is_ready_to_subscribe():
                self.logger.info("所有网关已就绪！")
                self._process_pending_subscriptions()
            else:
                self._log_gateway_status()
                
        except Exception as e:
            self.logger.error(f"处理行情网关登录事件失败: {e}", exc_info=True)
    
    def _handle_td_gateway_ready(self, event: Event):
        """
        处理交易网关就绪事件
        
        Args:
            event: 交易网关就绪事件
        """
        try:
            data = event.payload
            
            if not data or data.get("code") != 0:
                self._td_gateway_ready = False
                self.logger.warning("交易网关就绪失败")
                return
            
            was_ready_before = self._is_ready_to_subscribe()
            self._td_gateway_ready = True
            self.logger.info("✓ 交易网关已就绪")
            
            # 检查是否所有网关都就绪
            if not was_ready_before and self._is_ready_to_subscribe():
                self.logger.info("所有网关已就绪！")
                self._process_pending_subscriptions()
            else:
                self._log_gateway_status()
                
        except Exception as e:
            self.logger.error(f"处理交易网关就绪事件失败: {e}", exc_info=True)
    
    def _handle_contracts_loaded(self, event: Event):
        """
        处理合约加载完成事件
        
        Args:
            event: 合约查询完成事件
        """
        try:
            data = event.payload
            
            if not data or data.get("code") != 0:
                self._contracts_loaded = False
                self.logger.warning("合约加载失败")
                return
            
            was_ready_before = self._is_ready_to_subscribe()
            self._contracts_loaded = True
            self.logger.info("✓ 合约信息已加载完成")
            
            # 检查是否所有网关都就绪
            if not was_ready_before and self._is_ready_to_subscribe():
                self.logger.info("所有网关已就绪！")
                self._process_pending_subscriptions()
            else:
                self._log_gateway_status()
                
        except Exception as e:
            self.logger.error(f"处理合约加载事件失败: {e}", exc_info=True)
