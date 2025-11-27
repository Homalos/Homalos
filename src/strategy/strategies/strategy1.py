#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy1.py
@Date       : 2025/10/11 15:42
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略1demo - 演示交易链路的完整流程
"""
import datetime

from src.core.constants import Interval, Direction, Offset
from src.core.object import OrderData, TradeData, BarData, TickData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategy
from src.utils.strategy_logger import get_strategy_logger as get_logger
from src.utils.utility import write_csv


class Strategy1(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.logger = get_logger(name=self.__class__.__name__)
        self.strategy_name: str = "策略1"
        self.strategy_content: str = "用来测试从行情->交易信号->下单全流程"
        self.author: str = "Lumosylva"
        self.instruments: list[str] = ["SA601", "FG601"]
        self.bar_intervals: dict[str, list[Interval]] = {
            "SA601": [Interval.MINUTE],
            "FG601": [Interval.MINUTE]
        }

        # 初始化详细策略文件
        self.specific_strategy_map: dict[str, SpecificStrategy] = {}
        for instrument_id in self.instruments:
            self.specific_strategy_map[instrument_id] = Strategy1.Specific(
                self,
                self.strategy_id,
                instrument_id,
                self.bar_intervals.get(instrument_id, [])
            )

    def one_min(self, now: datetime.datetime) -> None:
        """每分钟调用一次执行"""
        pass

    class Specific(SpecificStrategy):
        """
        策略的详细策略文件
        """
        def __init__(
                self,
                base_strategy: BaseStrategy,
                strategy_id: str,
                instrument_id: str,
                bar_intervals: list[Interval]
        ) -> None:
            super().__init__(base_strategy, instrument_id, bar_intervals)
            self.logger = get_logger(name=base_strategy.strategy_name)
            self.base_strategy: BaseStrategy = base_strategy
            self.strategy_id: str = strategy_id
            self.instrument_id: str = instrument_id
            self.bar_intervals: list[Interval] = bar_intervals
            
            # 信号去重机制 - 防止同一时刻生成重复信号
            self.last_signal_time: dict[str, tuple] = {}  # {signal_key: (timestamp, direction, price)}
            
            # 创建csv文件
            for bar_interval in bar_intervals:
                write_csv(
                    f"{self.instrument_id}_{bar_interval.value}.csv",
                    "w",
                    [
                        "bar_type",
                        "update_time",
                        "instrument_id",
                        "exchange_id",
                        "volume",
                        "open_interest",
                        "open_price",
                        "high_price",
                        "low_price",
                        "close_price",
                        "last_volume"
                    ]
                )

        def on_init(self) -> None:
            self.logger.info(f"{self.strategy_id} 策略开始运行")

        def on_close(self) -> None:
            pass

        def on_alarm(self) -> None:
            pass

        def on_tick(self, tick: TickData) -> None:
            # 降低日志频率，避免I/O阻塞FastAPI事件循环
            # self.logger.info(f"收到tick: "
            #                  f"{self.base_strategy.strategy_name} "
            #                  f"{tick.trading_day} "
            #                  f"{tick.exchange_id} "
            #                  f"{tick.instrument_id} "
            #                  f"{tick.last_price} "
            #                  f"{tick.update_time} "
            #                  f"{tick.update_millisec}")
            pass

        def on_bar(self, bar: BarData) -> None:
            self.logger.info(f"{self.base_strategy.strategy_name} 收到bar: "
                             f"{bar.instrument_id} "
                             f"{bar.exchange_id.value} "
                             f"open={bar.open_price} "
                             f"high={bar.high_price} "
                             f"low={bar.low_price} "
                             f"close={bar.close_price} "
                             f"vol={bar.volume}")

            # write_csv(f"{self.instrument_id}_{bar.bar_type.value}.csv",
            #           "a+",
            #           [
            #               bar.bar_type.value,
            #               bar.update_time,
            #               bar.instrument_id,
            #               bar.exchange_id.value,
            #               bar.volume,
            #               bar.open_interest,
            #               bar.open_price,
            #               bar.high_price,
            #               bar.low_price,
            #               bar.close_price,
            #               bar.last_volume
            #             ]
            #           )
            
            # ========== 交易信号生成逻辑 ==========
            # 演示：简单的交易策略 - 当收盘价高于开盘价时做多，低于开盘价时做空
            try:
                if bar.close_price > bar.open_price:
                    # 做多信号：收盘价 > 开盘价
                    self.logger.info(f"[{self.instrument_id}] 生成做多信号: close({bar.close_price}) > open({bar.open_price})")
                    
                    # 检查是否已经在同一时刻发送过相同的信号（去重）
                    if self._should_send_signal(Direction.LONG, bar.close_price, bar.update_time):
                        self.send_order(
                            direction=Direction.LONG,
                            offset=Offset.OPEN,
                            volume=1,
                            price=bar.close_price,
                            exchange_id=bar.exchange_id
                        )
                    else:
                        self.logger.info(f"[{self.instrument_id}] 信号被去重过滤: 同一时刻已发送过相同信号")
                        
                elif bar.close_price < bar.open_price:
                    # 做空信号：收盘价 < 开盘价
                    self.logger.info(f"[{self.instrument_id}] 生成做空信号: close({bar.close_price}) < open({bar.open_price})")
                    
                    # 检查是否已经在同一时刻发送过相同的信号（去重）
                    if self._should_send_signal(Direction.SHORT, bar.close_price, bar.update_time):
                        self.send_order(
                            direction=Direction.SHORT,
                            offset=Offset.OPEN,
                            volume=1,
                            price=bar.close_price,
                            exchange_id=bar.exchange_id
                        )
                    else:
                        self.logger.info(f"[{self.instrument_id}] 信号被去重过滤: 同一时刻已发送过相同信号")
            except Exception as e:
                self.logger.error(f"[{self.instrument_id}] 生成交易信号异常: {e}", exc_info=True)

        def _should_send_signal(self, direction: Direction, price: float, timestamp: str) -> bool:
            """检查是否应该发送信号（去重机制）"""
            # 使用时间戳作为信号的唯一标识（同一秒内的信号视为重复）
            signal_key = f"{self.instrument_id}_{timestamp}"
            
            # 获取最后一次发送的信号
            last_signal = self.last_signal_time.get(signal_key)
            
            if last_signal:
                last_direction, last_price = last_signal
                # 如果方向和价格都相同，则认为是重复信号
                if last_direction == direction and abs(last_price - price) < 0.01:
                    return False
            
            # 记录本次信号
            self.last_signal_time[signal_key] = (direction, price)
            
            # 清理过期的信号记录（保留最近100条）
            if len(self.last_signal_time) > 100:
                # 删除最早的记录
                oldest_key = next(iter(self.last_signal_time))
                del self.last_signal_time[oldest_key]
            
            return True


        def on_trade(self, trade: TradeData) -> None:
            """成交回调 - 更新策略持仓"""
            self.logger.info(f"[{self.instrument_id}] 成交回调: "
                           f"exchange_id={trade.exchange_id}, "
                           f"order_id={trade.order_id}, "
                           f"trade_id={trade.trade_id}, "
                           f"direction={trade.direction}, "
                           f"offset={trade.offset}, "
                           f"price={trade.price}, "
                           f"volume={trade.volume}, "
                           f"timestamp={trade.timestamp}")

            # 更新策略持仓
            self._update_strategy_position(trade)

        def on_order(self, order: OrderData) -> None:
            """订单回调"""
            self.logger.info(f"[{self.instrument_id}] 订单状态: "
                           f"order_id={order.order_id}, "
                           f"status={order.order_status}, "
                           f"volume_traded={order.volume_traded}")

        def _update_strategy_position(self, trade: TradeData) -> None:
            """根据成交数据更新策略持仓"""
            # 查找或创建持仓记录
            position_key = f"{trade.instrument_id}_{trade.direction}"
            
            # 在策略的持仓列表中查找相同的持仓
            existing_position = None
            for pos in self.base_strategy.positions:
                if (pos.get("instrument_id") == trade.instrument_id and 
                    pos.get("direction") == trade.direction):
                    existing_position = pos
                    break
            
            if existing_position:
                # 更新现有持仓
                existing_position["volume"] += trade.trade_volume
                existing_position["last_price"] = trade.trade_price
                # 更新持仓均价
                total_cost = (existing_position.get("avg_price", trade.trade_price) * 
                             (existing_position["volume"] - trade.trade_volume) + 
                             trade.trade_price * trade.trade_volume)
                existing_position["avg_price"] = total_cost / existing_position["volume"]
                existing_position["pnl"] = (trade.trade_price - existing_position["avg_price"]) * existing_position["volume"]
                self.logger.info(f"[{self.instrument_id}] 更新持仓: {existing_position}")
            else:
                # 创建新的持仓记录
                new_position = {
                    "instrument_id": trade.instrument_id,
                    "direction": trade.direction,
                    "volume": trade.trade_volume,
                    "avg_price": trade.trade_price,
                    "last_price": trade.trade_price,
                    "pnl": 0,
                    "trade_id": trade.trade_id,
                    "timestamp": trade.trade_time
                }
                self.base_strategy.positions.append(new_position)
                self.logger.info(f"[{self.instrument_id}] 新增持仓: {new_position}")


def get_strategy():
    return Strategy1()
