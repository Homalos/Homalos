#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网关状态管理单元测试
测试修复后的线程安全状态管理功能
"""

import asyncio
import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.event_bus import EventBus
from src.ctp.gateway.order_trading_gateway import OrderTradingGateway, GatewayState
from src.core.logger import get_logger

logger = get_logger("GatewayStateTest")


class GatewayStateManagementTest:
    """网关状态管理测试"""
    
    def __init__(self):
        self.event_bus = EventBus("state_test_bus")
        self.gateway = None
        self.state_changes = []
        
    def setup(self):
        """设置测试环境"""
        logger.info("🔧 设置状态管理测试环境...")
        
        # 启动事件总线
        self.event_bus.start()
        
        # 创建网关实例
        self.gateway = OrderTradingGateway(self.event_bus, "TEST_GATEWAY")
        
        # 监听状态变更事件
        self.event_bus.subscribe("gateway.state_changed", self._on_state_changed)
        
        logger.info("✅ 测试环境设置完成")
    
    def _on_state_changed(self, event):
        """状态变更事件处理"""
        data = event.data
        change_info = {
            "gateway_name": data.get("gateway_name"),
            "old_state": data.get("old_state"),
            "new_state": data.get("new_state"),
            "thread_name": data.get("thread_name"),
            "timestamp": data.get("timestamp")
        }
        self.state_changes.append(change_info)
        logger.info(f"📝 记录状态变更: {change_info['old_state']} -> {change_info['new_state']} [线程:{change_info['thread_name']}]")
    
    def test_synchronous_state_management(self):
        """测试同步状态管理"""
        logger.info("🧪 开始测试同步状态管理...")
        
        try:
            # 检查初始状态
            initial_state = self.gateway._get_gateway_state()
            assert initial_state == GatewayState.DISCONNECTED, f"初始状态应为DISCONNECTED，实际为{initial_state}"
            logger.info("✅ 初始状态检查通过")
            
            # 测试状态变更（主线程）
            self.gateway._set_gateway_state(GatewayState.CONNECTING)
            new_state = self.gateway._get_gateway_state()
            assert new_state == GatewayState.CONNECTING, f"状态应为CONNECTING，实际为{new_state}"
            logger.info("✅ 主线程状态变更成功")
            
            # 等待事件处理
            time.sleep(0.1)
            
            # 验证事件发布
            assert len(self.state_changes) >= 1, "应该收到至少一个状态变更事件"
            last_change = self.state_changes[-1]
            assert last_change["new_state"] == "connecting", f"事件中的新状态应为connecting，实际为{last_change['new_state']}"
            logger.info("✅ 状态变更事件发布成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 同步状态管理测试失败: {e}")
            return False
    
    def test_multi_thread_state_management(self):
        """测试多线程状态管理"""
        logger.info("🧪 开始测试多线程状态管理...")
        
        try:
            # 清空之前的状态变更记录
            self.state_changes.clear()
            
            # 定义线程函数
            def thread_function(thread_id, target_state):
                thread_name = f"TestThread-{thread_id}"
                threading.current_thread().name = thread_name
                logger.info(f"🔄 线程{thread_name}开始执行状态变更...")
                
                # 模拟CTP回调中的状态变更
                self.gateway._set_gateway_state(target_state)
                logger.info(f"✅ 线程{thread_name}状态变更完成")
            
            # 启动多个线程同时进行状态变更
            threads = []
            states = [GatewayState.AUTHENTICATED, GatewayState.QUERYING_CONTRACTS, GatewayState.READY]
            
            for i, state in enumerate(states):
                thread = threading.Thread(target=thread_function, args=(i+1, state))
                threads.append(thread)
                thread.start()
            
            # 等待所有线程完成
            for thread in threads:
                thread.join()
            
            # 等待事件处理
            time.sleep(0.2)
            
            # 验证结果
            final_state = self.gateway._get_gateway_state()
            logger.info(f"📊 最终状态: {final_state.value}")
            
            # 验证状态变更事件
            assert len(self.state_changes) >= len(states), f"应该收到至少{len(states)}个状态变更事件，实际收到{len(self.state_changes)}个"
            
            # 验证线程信息记录
            thread_names = [change["thread_name"] for change in self.state_changes]
            logger.info(f"📋 参与状态变更的线程: {thread_names}")
            
            logger.info("✅ 多线程状态管理测试成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 多线程状态管理测试失败: {e}")
            return False
    
    def test_no_asyncio_errors(self):
        """测试是否还有asyncio相关错误"""
        logger.info("🧪 开始测试asyncio错误修复...")
        
        try:
            # 模拟CTP回调场景：在没有事件循环的线程中调用状态管理
            def ctp_callback_simulation():
                # 确保这个线程没有事件循环
                try:
                    asyncio.get_running_loop()
                    logger.warning("⚠️ 当前线程有运行中的事件循环，测试条件不理想")
                except RuntimeError:
                    logger.info("✅ 确认当前线程无运行中的事件循环")
                
                # 执行状态变更（这在修复前会导致 RuntimeError: no running event loop）
                self.gateway._set_gateway_state(GatewayState.ERROR)
                logger.info("✅ 在无事件循环线程中状态变更成功")
            
            # 在新线程中执行（模拟CTP回调线程）
            ctp_thread = threading.Thread(target=ctp_callback_simulation, name="CTP-Callback-Simulation")
            ctp_thread.start()
            ctp_thread.join()
            
            # 验证状态变更成功
            final_state = self.gateway._get_gateway_state()
            assert final_state == GatewayState.ERROR, f"状态应为ERROR，实际为{final_state}"
            
            logger.info("✅ asyncio错误修复验证成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ asyncio错误测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始网关状态管理单元测试...")
        
        # 设置测试环境
        self.setup()
        
        test_cases = [
            ("同步状态管理", self.test_synchronous_state_management),
            ("多线程状态管理", self.test_multi_thread_state_management),
            ("asyncio错误修复验证", self.test_no_asyncio_errors),
        ]
        
        passed_tests = 0
        total_tests = len(test_cases)
        
        for test_name, test_func in test_cases:
            logger.info(f"\n{'='*50}")
            logger.info(f"🧪 执行测试: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                result = test_func()
                if result:
                    logger.info(f"✅ {test_name} - 通过")
                    passed_tests += 1
                else:
                    logger.error(f"❌ {test_name} - 失败")
            except Exception as e:
                logger.error(f"❌ {test_name} - 异常: {e}")
        
        # 生成测试报告
        self.generate_test_report(passed_tests, total_tests)
        
        return passed_tests == total_tests
    
    def generate_test_report(self, passed: int, total: int):
        """生成测试报告"""
        logger.info(f"\n{'='*60}")
        logger.info("📋 网关状态管理单元测试报告")
        logger.info(f"{'='*60}")
        
        logger.info(f"总测试数: {total}")
        logger.info(f"通过测试: {passed}")
        logger.info(f"失败测试: {total - passed}")
        logger.info(f"成功率: {(passed/total)*100:.1f}%")
        
        logger.info(f"\n📊 状态变更事件统计:")
        logger.info(f"  总事件数: {len(self.state_changes)}")
        
        if self.state_changes:
            logger.info(f"  事件详情:")
            for i, change in enumerate(self.state_changes):
                logger.info(f"    {i+1}. {change['old_state']} -> {change['new_state']} [线程:{change['thread_name']}]")
        
        if passed == total:
            logger.info(f"\n🎉 所有测试通过！状态管理修复成功")
        else:
            logger.warning(f"\n⚠️ 部分测试失败，需要进一步检查")
    
    def cleanup(self):
        """清理测试环境"""
        try:
            if self.event_bus:
                self.event_bus.stop()
            logger.info("🧹 测试环境清理完成")
        except Exception as e:
            logger.error(f"❌ 清理失败: {e}")


def main():
    """主函数"""
    test = GatewayStateManagementTest()
    
    try:
        success = test.run_all_tests()
        
        if success:
            logger.info("🎯 网关状态管理单元测试全部通过！")
            sys.exit(0)
        else:
            logger.error("💥 网关状态管理单元测试失败！")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 测试执行异常: {e}")
        sys.exit(1)
    finally:
        test.cleanup()


if __name__ == "__main__":
    main() 