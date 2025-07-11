#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : test_ctp_simple
@Date       : 2025/7/9 13:40
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: CTP行情网关简化测试 - 专注于基本功能验证
"""
import asyncio
import sys
import time

from src.config.setting import get_instrument_exchange_id
from src.core.event import EventType

# 添加项目根目录到Python路径
sys.path.insert(0, '.')

from src.core.event_bus import EventBus
from src.core.object import SubscribeRequest, TickData, LogData, ContractData
from src.config.constant import Exchange, Product
from src.ctp.gateway.market_data_gateway import MarketDataGateway, symbol_contract_map
from src.core.logger import get_logger

logger = get_logger("CTPSimpleTest")


class CTPSimpleTester:
    """CTP简化测试器"""
    
    def __init__(self):
        self.event_bus = None
        self.market_gateway = None
        self.tick_received = False
        self.connection_success = False
        self.login_success = False
        
        # 使用更活跃的品种
        self.test_symbols = [
            "FG509",  # 纯碱主力
            "SA509",  # 玻璃主力
        ]
        
        # CTP配置
        self.ctp_config = {
            "userid": "160219",
            "password": "donny@103010",
            "broker_id": "9999",
            "md_address": "tcp://182.254.243.31:30011",
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
        print("=" * 50)
        print("CTP行情网关简化测试")
        print("=" * 50)
        
        # 预加载合约数据
        self._preload_contracts()
        
        # 创建事件总线
        self.event_bus = EventBus(name="CTPSimpleTest")
        
        # 创建行情网关
        self.market_gateway = MarketDataGateway(self.event_bus, "CTP_MD")
        
        # 设置事件处理器
        self._setup_handlers()
        
        print("✓ 测试环境初始化完成")
    
    def _setup_handlers(self):
        """设置事件处理器"""
        # 订阅Tick事件（使用字符串）
        self.event_bus.subscribe(EventType.MARKET_TICK, self._on_tick)
        
        # 订阅日志事件
        self.event_bus.subscribe(EventType.LOG_MESSAGE, self._on_log)
        
        # 订阅合约事件
        self.event_bus.subscribe(EventType.CONTRACT, self._on_contract)
    
    def _on_tick(self, event):
        """处理Tick数据"""
        self.tick_received = True
        tick_data: TickData = event.data
        print(f"\n📊 收到Tick数据!")
        print(f"   品种: {tick_data.symbol}")
        print(f"   交易所: {tick_data.exchange}")
        print(f"   最新价: {tick_data.last_price}")
        print(f"   时间: {tick_data.datetime}")
    
    def _on_log(self, event):
        """处理日志事件"""
        log_data: LogData = event.data
        if hasattr(log_data, 'msg'):
            msg = log_data.msg
            print(f"📝 {msg}")
            
            # 检测连接和登录状态
            if "行情服务器连接成功" in msg:
                self.connection_success = True
            elif "行情服务器登录成功" in msg:
                self.login_success = True
    
    def _on_contract(self, event):
        """处理合约事件"""
        contract_data: ContractData = event.data
        print(f"📋 收到合约数据: {contract_data.symbol}")
    
    async def test_connection(self):
        """测试连接"""
        print("\n🔗 测试连接...")
        
        try:
            # 发起连接
            self.market_gateway.connect(self.ctp_config)
            
            # 等待连接和登录完成（最多等待10秒）
            print("⏳ 等待连接和登录...")
            for i in range(20):  # 20次，每次0.5秒
                await asyncio.sleep(0.5)
                
                if self.connection_success and self.login_success:
                    print("✅ 连接和登录成功")
                    return True
                elif i % 4 == 0:  # 每2秒打印一次状态
                    print(f"   等待中... 连接:{self.connection_success}, 登录:{self.login_success}")
            
            # 检查最终状态
            if self.market_gateway.md_api:
                print(f"📊 最终状态 - 连接:{self.market_gateway.md_api.connect_status}, 登录:{self.market_gateway.md_api.login_status}")
                
                if self.market_gateway.md_api.connect_status and self.market_gateway.md_api.login_status:
                    print("✅ 连接成功")
                    return True
            
            print("❌ 连接失败")
            return False
                
        except Exception as e:
            print(f"❌ 连接异常: {e}")
            return False
    
    async def test_subscription(self):
        """测试订阅"""
        print("\n📡 测试订阅...")
        
        try:
            # 获取交易所映射
            instrument_exchange_json = get_instrument_exchange_id()
            print(f"📋 加载交易所映射: {len(instrument_exchange_json)} 个合约")
            
            for symbol in self.test_symbols:
                print(f"   订阅 {symbol}...")
                
                # 获取交易所
                exchange_str = instrument_exchange_json.get(symbol)
                if exchange_str:
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
                        print(f"   ⚠️  未知交易所 {exchange_str}，使用默认交易所")
                        exchange = Exchange.CZCE
                else:
                    print(f"   ⚠️  {symbol} 未找到交易所映射，使用默认交易所")
                    exchange = Exchange.CZCE
                
                subscribe_req = SubscribeRequest(
                    symbol=symbol,
                    exchange=exchange
                )
                self.market_gateway.subscribe(subscribe_req)
                await asyncio.sleep(0.5)
            
            # 检查订阅状态
            if self.market_gateway.md_api:
                subscribed_count = len(self.market_gateway.md_api.subscribed)
                print(f"✅ 订阅完成，已订阅 {subscribed_count} 个品种")
                print(f"   已订阅品种: {list(self.market_gateway.md_api.subscribed)}")
                return True
            else:
                print("❌ 行情API未初始化")
                return False
            
        except Exception as e:
            print(f"❌ 订阅异常: {e}")
            return False
    
    async def test_market_data(self):
        """测试行情数据接收"""
        print("\n📊 测试行情数据接收...")
        print("   等待30秒接收数据...")
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < 30:
                await asyncio.sleep(5)
                elapsed = int(time.time() - start_time)
                print(f"   ⏱️  {elapsed}秒 - {'已收到数据' if self.tick_received else '等待中...'}")
                
                if self.tick_received:
                    break
            
            if self.tick_received:
                print("✅ 成功接收到行情数据")
                return True
            else:
                print("❌ 未接收到行情数据")
                return False
                
        except KeyboardInterrupt:
            print("\n⏹️  用户中断")
            return self.tick_received
    
    async def run_test(self):
        """运行完整测试"""
        try:
            # 初始化
            await self.setup()
            
            # 连接测试
            if not await self.test_connection():
                print("❌ 连接测试失败，停止后续测试")
                return False
            
            # 订阅测试
            if not await self.test_subscription():
                print("❌ 订阅测试失败，停止后续测试")
                return False
            
            # 行情数据测试
            result = await self.test_market_data()
            
            print("\n" + "=" * 50)
            if result:
                print("🎉 测试成功！CTP行情网关工作正常")
            else:
                print("❌ 测试失败，但连接和订阅正常")
                print("   可能原因：")
                print("   1. 当前时间不在交易时段")
                print("   2. 订阅的品种不活跃")
                print("   3. 需要合约数据初始化")
            print("=" * 50)
            
            return result
            
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            return False
        finally:
            # 清理资源
            if self.event_bus:
                self.event_bus.stop()


async def main():
    """主函数"""
    print("CTP行情网关简化测试程序")
    
    try:
        tester = CTPSimpleTester()
        await tester.run_test()
        
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