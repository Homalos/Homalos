# -*- coding: utf-8 -*-
"""
交易引擎全链路集成测试脚本
"""
import asyncio
import sys
import time
from unittest.mock import MagicMock

from src.config.constant import Exchange, Product
from src.core.event_bus import EventBus
from src.core.object import ContractData, SubscribeRequest
from src.ctp.gateway.market_data_gateway import MarketDataGateway, symbol_contract_map
from src.services.data_service import DataService
from src.services.trading_engine import TradingEngine
from src.strategies.minimal_strategy import MinimalStrategy


class TradingMonitor:
    """交易监控器 - 监控订单、账户、持仓变化"""
    def __init__(self):
        self.orders = []
        self.trades = []
        self.accounts = []
        self.positions = []
        
    def __call__(self, event):
        if event.type.startswith("market.tick"):
            print(f"[TICK] 收到Tick: {event.data.symbol} {event.data.last_price} 事件类型:{event.type}")
            
        elif event.type == "order.submitted":
            self.orders.append(event.data)
            print(f"[ORDER] 订单提交: {event.data.orderid} {event.data.symbol} {event.data.direction.value if event.data.direction else 'UNKNOWN'} {event.data.volume}@{event.data.price}")
            
        elif event.type == "order.filled":
            self.trades.append(event.data)
            print(f"[TRADE] 订单成交: {event.data.trade_id} {event.data.symbol} {event.data.direction.value if event.data.direction else 'UNKNOWN'} {event.data.volume}@{event.data.price}")
            
        elif event.type == "account.updated":
            self.accounts.append(event.data)
            print(f"[ACCOUNT] 账户更新: 余额={event.data.balance:.2f} 可用={event.data.available:.2f} 冻结={event.data.frozen:.2f}")
            
        elif event.type == "position.updated":
            self.positions.append(event.data)
            print(f"[POSITION] 持仓更新: {event.data.symbol} {event.data.direction.value} 数量={event.data.volume} 价格={event.data.price:.2f} 盈亏={event.data.pnl:.2f}")

async def main():
    # 配置
    test_symbols = ["FG509"]
    ctp_config = {
        "userid": "160219",
        "password": "donny@103010",
        "broker_id": "9999",
        "md_address": "tcp://182.254.243.31:30011",
        "appid": "simnow_client_test",
        "auth_code": "0000000000000000"
    }
    
    # 预加载合约
    for symbol in test_symbols:
        contract = ContractData(
            symbol=symbol,
            exchange=Exchange.CZCE,
            name=f"{symbol}合约",
            product=Product.FUTURES,
            size=1,
            price_tick=0.01,
            min_volume=1,
            gateway_name="CTP_MD"
        )
        symbol_contract_map[symbol] = contract
    
    # 初始化服务
    event_bus = EventBus("TradingEngineTest")
    
    # 配置
    config = MagicMock()
    config.get.side_effect = lambda k, d=None: {
        "database.path": ":memory:",
        "database.batch_size": 2,
        "database.flush_interval": 1,
        "data.market.buffer_size": 10,
        "data.market.enable_persistence": False,
        "trading.risk.enabled": True,
        "trading.risk.max_order_volume": 10,
        "trading.risk.max_position_volume": 100,
        "trading.risk.max_daily_orders": 1000
    }.get(k, d)
    
    # 启动服务
    ds = DataService(event_bus, config)
    trading_engine = TradingEngine(event_bus, config)
    
    # 监控器
    monitor = TradingMonitor()
    event_bus.add_monitor(monitor)
    
    # 启动行情网关
    md_gateway = MarketDataGateway(event_bus, "CTP_MD")
    md_gateway.connect(ctp_config)
    await asyncio.sleep(2)
    
    # 订阅合约
    for symbol in test_symbols:
        req = SubscribeRequest(symbol=symbol, exchange=Exchange.CZCE)
        md_gateway.subscribe(req)
        await asyncio.sleep(0.5)
    
    # 创建并启动最小策略
    strategy = MinimalStrategy(
        strategy_id="test_minimal",
        event_bus=event_bus,
        params={
            "symbol": "FG509",
            "exchange": "CZCE",
            "volume": 1,
            "order_interval": 5,  # 5秒间隔
            "max_orders": 3       # 最多3个订单
        }
    )
    
    await strategy.initialize()
    await strategy.start()
    
    print("=" * 60)
    print("交易引擎全链路测试启动")
    print("监控内容：订单状态、成交回报、账户变化、持仓变化")
    print("策略：每5秒下单买入1手FG509，最多3个订单")
    print("=" * 60)
    
    try:
        # 运行测试
        start_time = time.time()
        while True:
            await asyncio.sleep(5)
            elapsed = time.time() - start_time
            
            print(f"\n--- 运行时间: {elapsed:.0f}秒 ---")
            print(f"订单数量: {len(monitor.orders)}")
            print(f"成交数量: {len(monitor.trades)}")
            print(f"账户更新: {len(monitor.accounts)}")
            print(f"持仓更新: {len(monitor.positions)}")
            
            # 显示策略统计
            stats = strategy.get_strategy_stats()
            print(f"策略状态: {stats['active']}, 运行时间: {stats['runtime']:.1f}秒")
            print(f"策略统计: 总订单={stats['stats']['total_orders']}, 成交订单={stats['stats']['filled_orders']}")
            
            # 测试结束条件
            if len(monitor.trades) >= 3 or elapsed > 60:
                print("\n测试完成条件达成，准备退出...")
                break
                
    except KeyboardInterrupt:
        print("\n用户中断，准备退出...")
    finally:
        # 清理
        await strategy.stop()
        ds.db_manager.stop()
        event_bus.stop()
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print(f"最终统计:")
        print(f"  订单数量: {len(monitor.orders)}")
        print(f"  成交数量: {len(monitor.trades)}")
        print(f"  账户更新: {len(monitor.accounts)}")
        print(f"  持仓更新: {len(monitor.positions)}")
        print("=" * 60)

if __name__ == "__main__":
    if sys.version_info < (3, 10):
        print("❌ 需要Python 3.10或更高版本")
        sys.exit(1)
    asyncio.run(main()) 