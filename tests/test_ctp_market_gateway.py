#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : test_ctp_market_gateway
@Date       : 2025/7/9 13:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: CTP行情网关测试 - 测试连接、订阅、接收行情数据
"""
import asyncio
import time
import sys
from datetime import datetime
from typing import Dict, Any

from src.core.event import EventType

# 添加项目根目录到Python路径
sys.path.insert(0, '.')

from src.core.event_bus import EventBus
from src.core.object import SubscribeRequest, TickData, LogData, ContractData
from src.config.constant import Exchange, Product
from src.ctp.gateway.market_data_gateway import MarketDataGateway, symbol_contract_map
from src.config.setting import get_instrument_exchange_id
from src.core.logger import get_logger

logger = get_logger("CTPMarketTest")


class CTPMarketGatewayTester:
    """CTP行情网关测试器"""
    
    def __init__(self):
        self.event_bus = None
        self.market_gateway = None
        self.tick_count = 0
        self.last_tick_time = None
        self.tick_stats = {}  # 按合约统计Tick数量
        self.test_symbols = [
            "SA509",  # 郑州交易所纯碱
            "FG509",  # 郑州交易所玻璃
        ]
        
        # CTP配置（使用SimNow测试环境）
        self.ctp_config = {
            "userid": "160219",           # 用户名
            "password": "donny@103010",   # 密码
            "broker_id": "9999",          # 经纪商代码
            "md_address": "tcp://182.254.243.31:30011",  # 行情服务器地址
            "appid": "simnow_client_test",
            "auth_code": "0000000000000000"
        }
    
    def _preload_contracts(self):
        """预加载合约数据"""
        print("📋 预加载合约数据...")
        
        # 获取交易所映射
        instrument_exchange_json = get_instrument_exchange_id()
        
        # 为测试品种创建合约数据
        for symbol in self.test_symbols:
            exchange_str = instrument_exchange_json.get(symbol, "CZCE")
            
            # 将字符串转换为Exchange枚举
            if exchange_str == "CZCE":
                exchange = Exchange.CZCE
            elif exchange_str == "SHFE":
                exchange = Exchange.SHFE
            elif exchange_str == "DCE":
                exchange = Exchange.DCE
            elif exchange_str == "CFFEX":
                exchange = Exchange.CFFEX
            else:
                exchange = Exchange.CZCE
            
            # 创建合约数据
            contract = ContractData(
                symbol=symbol,
                exchange=exchange,
                name=f"{symbol}合约",
                product=Product.FUTURES,
                size=1,
                price_tick=0.01,
                min_volume=1,
                gateway_name="CTP_MD"
            )
            
            # 添加到全局缓存
            symbol_contract_map[symbol] = contract
            print(f"   ✅ 加载合约: {symbol} -> {exchange.value}")
        
        print(f"📋 合约缓存数量: {len(symbol_contract_map)}")
    
    async def setup(self):
        """初始化测试环境"""
        print("=" * 60)
        print("CTP行情网关测试")
        print("=" * 60)
        
        # 0. 预加载合约数据
        print("\n0. 预加载合约数据...")
        self._preload_contracts()
        
        # 1. 创建事件总线
        print("\n1. 创建事件总线...")
        self.event_bus = EventBus(name="CTPMarketTest")
        
        # 2. 创建行情网关
        print("2. 创建CTP行情网关...")
        self.market_gateway = MarketDataGateway(self.event_bus, "CTP_MD")
        
        # 3. 注册事件处理器
        print("3. 注册事件处理器...")
        self._setup_event_handlers()
        
        print("✓ 测试环境初始化完成")
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        # 订阅Tick事件
        self.event_bus.subscribe(EventType.MARKET_TICK, self._on_tick)
        
        # 订阅日志事件
        self.event_bus.subscribe(EventType.LOG_MESSAGE, self._on_log)

        # 订阅合约事件
        self.event_bus.subscribe(EventType.CONTRACT, self._on_contract)
        
    def _on_tick(self, event):
        """处理Tick数据"""
        tick_data: TickData = event.data
        if isinstance(tick_data, TickData):
            self.tick_count += 1
            self.last_tick_time = datetime.now()
            
            # 按合约统计Tick数量
            symbol = tick_data.symbol
            if symbol not in self.tick_stats:
                self.tick_stats[symbol] = 0
            self.tick_stats[symbol] += 1
            
            # 打印Tick信息（每10个Tick打印一次，避免刷屏）
            if self.tick_count % 10 == 0:
                print(f"\n📊 收到Tick数据 #{self.tick_count}:")
                print(f"   品种: {tick_data.symbol}")
                print(f"   最新价: {tick_data.last_price}")
                print(f"   买一价: {tick_data.bid_price_1}")
                print(f"   卖一价: {tick_data.ask_price_1}")
                print(f"   成交量: {tick_data.volume}")
                print(f"   时间: {tick_data.datetime}")
                
                # 显示各合约统计
                print(f"   各合约统计: {self.tick_stats}")
    
    def _on_log(self, event):
        """处理日志事件"""
        log_data: LogData = event.data
        if hasattr(log_data, 'msg'):
            print(f"📝 日志: {log_data.msg}")

    def _on_contract(self, event):
        """处理合约事件"""
        contract_data: ContractData = event.data
        print(f"📋 收到合约数据: {contract_data.symbol}")
    
    async def test_connection(self):
        """测试连接功能"""
        print("\n" + "=" * 40)
        print("测试1: 连接CTP行情服务器")
        print("=" * 40)
        
        try:
            # 连接行情服务器
            print(f"🔗 正在连接CTP行情服务器...")
            print(f"   地址: {self.ctp_config['md_address']}")
            print(f"   用户: {self.ctp_config['userid']}")
            print(f"   经纪商: {self.ctp_config['broker_id']}")
            
            self.market_gateway.connect(self.ctp_config)
            
            # 等待连接和登录
            print("⏳ 等待连接和登录...")
            await asyncio.sleep(5)
            
            # 检查连接状态
            if hasattr(self.market_gateway, 'md_api') and self.market_gateway.md_api:
                if self.market_gateway.md_api.connect_status:
                    print("✅ 连接成功")
                    if self.market_gateway.md_api.login_status:
                        print("✅ 登录成功")
                        return True
                    else:
                        print("❌ 登录失败")
                        return False
                else:
                    print("❌ 连接失败")
                    return False
            else:
                print("❌ 行情API未初始化")
                return False
                
        except Exception as e:
            print(f"❌ 连接测试失败: {e}")
            return False
    
    async def test_subscription(self):
        """测试订阅功能"""
        print("\n" + "=" * 40)
        print("测试2: 订阅行情数据")
        print("=" * 40)
        
        try:
            # 获取交易所映射
            instrument_exchange_json = get_instrument_exchange_id()
            
            # 订阅测试品种
            for symbol in self.test_symbols:
                print(f"📡 订阅品种: {symbol}")
                
                # 获取交易所
                exchange_str = instrument_exchange_json.get(symbol, "CZCE")
                if exchange_str == "CZCE":
                    exchange = Exchange.CZCE
                elif exchange_str == "SHFE":
                    exchange = Exchange.SHFE
                elif exchange_str == "DCE":
                    exchange = Exchange.DCE
                elif exchange_str == "CFFEX":
                    exchange = Exchange.CFFEX
                else:
                    exchange = Exchange.CZCE
                
                subscribe_req = SubscribeRequest(
                    symbol=symbol,
                    exchange=exchange
                )
                self.market_gateway.subscribe(subscribe_req)
                await asyncio.sleep(0.5)  # 避免订阅过快
            
            print("✅ 订阅请求发送完成")
            return True
            
        except Exception as e:
            print(f"❌ 订阅测试失败: {e}")
            return False
    
    async def test_market_data_reception(self):
        """测试行情数据接收"""
        print("\n" + "=" * 40)
        print("测试3: 接收行情数据")
        print("=" * 40)
        
        print("📊 等待接收行情数据...")
        print("   按 Ctrl+C 停止测试")
        
        start_time = time.time()
        initial_tick_count = self.tick_count
        
        try:
            # 监控30秒
            while time.time() - start_time < 30:
                await asyncio.sleep(1)
                
                # 每5秒显示一次统计
                elapsed = int(time.time() - start_time)
                if elapsed % 5 == 0 and elapsed > 0:
                    received_ticks = self.tick_count - initial_tick_count
                    tick_rate = received_ticks / elapsed if elapsed > 0 else 0
                    print(f"⏱️  {elapsed}秒 - 收到 {received_ticks} 个Tick, 速率: {tick_rate:.1f} tick/秒")
            
            # 最终统计
            total_elapsed = time.time() - start_time
            total_received = self.tick_count - initial_tick_count
            avg_rate = total_received / total_elapsed if total_elapsed > 0 else 0
            
            print(f"\n📈 行情数据接收统计:")
            print(f"   总时长: {total_elapsed:.1f} 秒")
            print(f"   总Tick数: {total_received}")
            print(f"   平均速率: {avg_rate:.1f} tick/秒")
            print(f"   各合约统计: {self.tick_stats}")
            
            # 检查是否所有合约都收到了行情
            for symbol in self.test_symbols:
                if symbol in self.tick_stats:
                    print(f"   ✅ {symbol}: {self.tick_stats[symbol]} 个Tick")
                else:
                    print(f"   ❌ {symbol}: 0 个Tick (未收到行情)")
            
            if total_received > 0:
                print("✅ 行情数据接收正常")
                return True
            else:
                print("❌ 未收到行情数据")
                return False
                
        except KeyboardInterrupt:
            print("\n⏹️  用户中断测试")
            return self.tick_count > initial_tick_count
    
    async def test_disconnection(self):
        """测试断开连接"""
        print("\n" + "=" * 40)
        print("测试4: 断开连接")
        print("=" * 40)
        
        try:
            print("🔌 正在断开连接...")
            self.market_gateway.close()
            await asyncio.sleep(2)
            print("✅ 连接已断开")
            return True
            
        except Exception as e:
            print(f"❌ 断开连接失败: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        try:
            # 初始化
            await self.setup()
            
            # 测试连接
            if not await self.test_connection():
                print("❌ 连接测试失败，停止后续测试")
                return False
            
            # 测试订阅
            if not await self.test_subscription():
                print("❌ 订阅测试失败，停止后续测试")
                return False
            
            # 测试行情数据接收
            if not await self.test_market_data_reception():
                print("❌ 行情数据接收测试失败")
                return False
            
            # 测试断开连接
            await self.test_disconnection()
            
            print("\n" + "=" * 60)
            print("🎉 所有测试完成！")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            return False
        finally:
            # 清理资源
            if self.event_bus:
                self.event_bus.stop()


def test_without_connection():
    """无连接测试 - 测试网关基本功能"""
    print("=" * 60)
    print("CTP行情网关无连接测试")
    print("=" * 60)
    
    try:
        # 创建事件总线
        event_bus = EventBus(name="CTPMarketTest")
        
        # 创建行情网关
        market_gateway = MarketDataGateway(event_bus, "CTP_MD")
        
        print("✅ 网关创建成功")
        print(f"   网关名称: {market_gateway.name}")
        print(f"   默认设置: {market_gateway.default_setting}")
        print(f"   支持交易所: {market_gateway.exchanges}")
        
        # 测试地址处理
        test_addresses = [
            "182.254.243.31:30011",
            "tcp://182.254.243.31:30011",
            "ssl://182.254.243.31:30011"
        ]
        
        print("\n🔧 测试地址处理:")
        for addr in test_addresses:
            processed = market_gateway._prepare_address(addr)
            print(f"   {addr} -> {processed}")
        
        # 清理
        event_bus.stop()
        print("\n✅ 无连接测试完成")
        
    except Exception as e:
        print(f"❌ 无连接测试失败: {e}")


async def main():
    """主函数"""
    print("CTP行情网关测试程序")
    print("请选择测试模式:")
    print("1. 完整测试（需要CTP账号）")
    print("2. 无连接测试（仅测试基本功能）")
    
    try:
        choice = input("\n请输入选择 (1/2): ").strip()
        
        if choice == "1":
            # 完整测试
            tester = CTPMarketGatewayTester()
            await tester.run_all_tests()
        elif choice == "2":
            # 无连接测试
            test_without_connection()
        else:
            print("❌ 无效选择")
            
    except KeyboardInterrupt:
        print("\n⏹️  用户中断程序")
    except Exception as e:
        print(f"❌ 程序运行错误: {e}")


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 10):
        print("❌ 需要Python 3.10或更高版本")
        sys.exit(1)
    
    # 运行测试
    asyncio.run(main()) 