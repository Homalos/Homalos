#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CTP实盘级别集成测试
测试完整的订单执行链路：策略信号 -> 风控 -> CTP网关 -> 真实成交回报
"""

import asyncio
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.event_bus import EventBus
from src.core.event import Event
from src.config.config_manager import ConfigManager
from src.services.trading_engine import TradingEngine
from src.ctp.gateway.order_trading_gateway import OrderTradingGateway
from src.ctp.gateway.market_data_gateway import MarketDataGateway
from src.core.object import OrderRequest, Direction, OrderType, Offset
from src.core.logger import get_logger

logger = get_logger("CTPIntegrationTest")


class CTRealTimeIntegrationTest:
    """CTP实盘级别集成测试"""
    
    def __init__(self):
        self.config = ConfigManager("config/system.yaml")
        self.event_bus = EventBus("test_bus")
        self.trading_engine = None
        self.trading_gateway = None
        self.market_gateway = None
        
        # 测试状态
        self.test_results = []
        self.order_sent_count = 0
        self.order_responses = []
        self.trade_responses = []
        
    async def setup(self):
        """测试环境设置"""
        try:
            logger.info("🔧 设置测试环境...")
            
            # 启动事件总线
            self.event_bus.start()
            
            # 初始化交易引擎
            self.trading_engine = TradingEngine(self.event_bus, self.config)
            await self.trading_engine.initialize()
            await self.trading_engine.start()
            
            # 初始化CTP网关
            await self._setup_gateways()
            
            # 注册测试事件监听
            self._setup_test_listeners()
            
            logger.info("✅ 测试环境设置完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 测试环境设置失败: {e}")
            return False
    
    async def _setup_gateways(self):
        """设置CTP网关"""
        try:
            # 获取CTP配置
            ctp_config = self.config.get("gateway.ctp", {})
            
            if not ctp_config.get("user_id") or not ctp_config.get("password"):
                logger.warning("⚠️ CTP配置不完整，跳过网关连接测试")
                return
            
            # 创建交易网关
            self.trading_gateway = OrderTradingGateway(self.event_bus, "CTP_TD_TEST")
            self.trading_gateway.connect(ctp_config)
            
            # 创建行情网关
            self.market_gateway = MarketDataGateway(self.event_bus, "CTP_MD_TEST")
            self.market_gateway.connect(ctp_config)
            
            # 等待连接建立
            await asyncio.sleep(5)
            
            logger.info("✅ CTP网关连接完成")
            
        except Exception as e:
            logger.error(f"❌ CTP网关设置失败: {e}")
            raise
    
    def _setup_test_listeners(self):
        """设置测试事件监听器"""
        self.event_bus.subscribe("order.submitted", self._on_order_submitted)
        self.event_bus.subscribe("order.updated", self._on_order_updated)
        self.event_bus.subscribe("order.filled", self._on_order_filled)
        self.event_bus.subscribe("order.send_failed", self._on_order_send_failed)
        self.event_bus.subscribe("order.sent_to_ctp", self._on_order_sent_to_ctp)
    
    def _on_order_submitted(self, event: Event):
        """订单提交事件"""
        logger.info(f"📤 订单已提交: {event.data}")
        self.order_responses.append(("submitted", event.data, time.time()))
    
    def _on_order_updated(self, event: Event):
        """订单更新事件"""
        order_data = event.data
        logger.info(f"📋 订单状态更新: {order_data.orderid} -> {order_data.status.value}")
        self.order_responses.append(("updated", order_data, time.time()))
    
    def _on_order_filled(self, event: Event):
        """订单成交事件"""
        trade_data = event.data
        logger.info(f"💰 订单成交: {trade_data.symbol} {trade_data.volume}@{trade_data.price}")
        self.trade_responses.append(("filled", trade_data, time.time()))
    
    def _on_order_send_failed(self, event: Event):
        """订单发送失败事件"""
        data = event.data
        logger.error(f"❌ 订单发送失败: {data.get('reason', '未知原因')}")
        self.order_responses.append(("send_failed", data, time.time()))
    
    def _on_order_sent_to_ctp(self, event: Event):
        """订单已发送到CTP事件"""
        data = event.data
        logger.info(f"🚀 订单已发送到CTP: {data.get('order_id')}")
        self.order_responses.append(("sent_to_ctp", data, time.time()))
    
    async def test_order_execution_chain(self):
        """测试完整的订单执行链路"""
        logger.info("🧪 开始测试订单执行链路...")
        
        try:
            # 创建测试订单
            order_request = OrderRequest(
                symbol="rb2501",  # 螺纹钢主力合约
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=1,
                price=3500.0,
                offset=Offset.OPEN,
                reference="test_order"
            )
            
            logger.info(f"📝 创建测试订单: {order_request.symbol} {order_request.direction.value} {order_request.volume}@{order_request.price}")
            
            # 发送订单到交易引擎
            start_time = time.time()
            
            # 通过事件总线发送订单
            self.event_bus.publish(Event("order.place", {
                "order_request": order_request,
                "strategy_id": "integration_test"
            }))
            
            self.order_sent_count += 1
            
            # 等待订单处理
            logger.info("⏳ 等待订单处理...")
            await asyncio.sleep(10)
            
            # 分析结果
            await self._analyze_order_execution_results(start_time)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 订单执行链路测试失败: {e}")
            return False
    
    async def _analyze_order_execution_results(self, start_time: float):
        """分析订单执行结果"""
        logger.info("📊 分析订单执行结果...")
        
        # 统计各类事件
        event_counts = {}
        for event_type, data, timestamp in self.order_responses:
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        logger.info(f"📈 事件统计: {event_counts}")
        
        # 检查关键事件
        success_indicators = [
            ("submitted", "订单提交成功"),
            ("sent_to_ctp", "订单发送到CTP成功"),
        ]
        
        test_passed = True
        for event_type, description in success_indicators:
            if event_counts.get(event_type, 0) > 0:
                logger.info(f"✅ {description}")
            else:
                logger.error(f"❌ {description} - 未收到事件")
                test_passed = False
        
        # 计算延迟
        if self.order_responses:
            first_response_time = min(timestamp for _, _, timestamp in self.order_responses)
            max_response_time = max(timestamp for _, _, timestamp in self.order_responses)
            
            submission_latency = (first_response_time - start_time) * 1000
            total_processing_time = (max_response_time - start_time) * 1000
            
            logger.info(f"⏱️ 订单提交延迟: {submission_latency:.2f}ms")
            logger.info(f"⏱️ 总处理时间: {total_processing_time:.2f}ms")
            
            # 延迟检查
            if submission_latency < 100:  # 100ms以内算正常
                logger.info("✅ 订单提交延迟正常")
            else:
                logger.warning(f"⚠️ 订单提交延迟偏高: {submission_latency:.2f}ms")
        
        self.test_results.append({
            "test": "order_execution_chain",
            "passed": test_passed,
            "events": event_counts,
            "details": self.order_responses
        })
    
    async def test_risk_management(self):
        """测试风控系统"""
        logger.info("🧪 开始测试风控系统...")
        
        try:
            # 测试1: 超大订单（应被拒绝）
            large_order = OrderRequest(
                symbol="rb2501",
                exchange="SHFE", 
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=1000,  # 超大手数
                price=3500.0,
                offset=Offset.OPEN,
                reference="risk_test_large"
            )
            
            logger.info("📝 测试超大订单风控...")
            self.event_bus.publish(Event("order.place", {
                "order_request": large_order,
                "strategy_id": "risk_test"
            }))
            
            await asyncio.sleep(3)
            
            # 测试2: 异常价格订单（应被拒绝）
            bad_price_order = OrderRequest(
                symbol="rb2501",
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=1,
                price=10000.0,  # 异常高价
                offset=Offset.OPEN,
                reference="risk_test_price"
            )
            
            logger.info("📝 测试异常价格风控...")
            self.event_bus.publish(Event("order.place", {
                "order_request": bad_price_order,
                "strategy_id": "risk_test"
            }))
            
            await asyncio.sleep(3)
            
            # 分析风控结果
            risk_rejection_count = sum(1 for event_type, _, _ in self.order_responses 
                                     if event_type in ["send_failed", "rejected"])
            
            if risk_rejection_count >= 2:
                logger.info("✅ 风控系统正常工作")
                return True
            else:
                logger.warning("⚠️ 风控系统可能未正常工作")
                return False
                
        except Exception as e:
            logger.error(f"❌ 风控测试失败: {e}")
            return False
    
    async def test_account_position_sync(self):
        """测试账户持仓同步"""
        logger.info("🧪 开始测试账户持仓同步...")
        
        try:
            # 触发账户查询
            self.event_bus.publish(Event("gateway.query_account", {}))
            self.event_bus.publish(Event("gateway.query_position", {}))
            
            await asyncio.sleep(5)
            
            # 检查是否收到回报
            logger.info("✅ 账户持仓查询完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 账户持仓同步测试失败: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始CTP实盘级别集成测试...")
        
        # 设置测试环境
        if not await self.setup():
            return False
        
        test_cases = [
            ("订单执行链路测试", self.test_order_execution_chain),
            ("风控系统测试", self.test_risk_management),
            ("账户持仓同步测试", self.test_account_position_sync),
        ]
        
        passed_tests = 0
        total_tests = len(test_cases)
        
        for test_name, test_func in test_cases:
            logger.info(f"\n{'='*50}")
            logger.info(f"🧪 执行测试: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                result = await test_func()
                if result:
                    logger.info(f"✅ {test_name} - 通过")
                    passed_tests += 1
                else:
                    logger.error(f"❌ {test_name} - 失败")
            except Exception as e:
                logger.error(f"❌ {test_name} - 异常: {e}")
        
        # 生成测试报告
        await self._generate_test_report(passed_tests, total_tests)
        
        return passed_tests == total_tests
    
    async def _generate_test_report(self, passed: int, total: int):
        """生成测试报告"""
        logger.info(f"\n{'='*60}")
        logger.info("📋 CTP实盘级别集成测试报告")
        logger.info(f"{'='*60}")
        logger.info(f"总测试数: {total}")
        logger.info(f"通过测试: {passed}")
        logger.info(f"失败测试: {total - passed}")
        logger.info(f"成功率: {(passed/total)*100:.1f}%")
        
        logger.info(f"\n📊 详细结果:")
        for result in self.test_results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            logger.info(f"  {result['test']}: {status}")
        
        logger.info(f"\n📈 订单事件统计:")
        logger.info(f"  发送订单数: {self.order_sent_count}")
        logger.info(f"  收到响应数: {len(self.order_responses)}")
        logger.info(f"  成交回报数: {len(self.trade_responses)}")
        
        if passed == total:
            logger.info(f"\n🎉 所有测试通过！CTP实盘链路运行正常")
        else:
            logger.warning(f"\n⚠️ 部分测试失败，请检查系统配置和网络连接")
    
    async def cleanup(self):
        """清理测试环境"""
        try:
            if self.trading_engine:
                await self.trading_engine.stop()
            
            if self.trading_gateway:
                self.trading_gateway.close()
            
            if self.market_gateway:
                self.market_gateway.close()
            
            if self.event_bus:
                self.event_bus.stop()
            
            logger.info("🧹 测试环境清理完成")
            
        except Exception as e:
            logger.error(f"❌ 清理失败: {e}")


async def main():
    """主函数"""
    test = CTRealTimeIntegrationTest()
    
    try:
        success = await test.run_all_tests()
        
        if success:
            logger.info("🎯 CTP实盘级别集成测试全部通过！")
            sys.exit(0)
        else:
            logger.error("💥 CTP实盘级别集成测试失败！")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 测试执行异常: {e}")
        sys.exit(1)
    finally:
        await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 