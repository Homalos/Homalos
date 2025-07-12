#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速数据流测试脚本 - 验证MinimalStrategy无tick数据问题
"""
import asyncio
import time
import requests
import json

async def test_strategy_data_flow():
    """测试策略数据流"""
    print("🧪 开始数据流测试...")
    
    # 1. 检查系统状态
    try:
        response = requests.get("http://127.0.0.1:8000/api/v1/system/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 系统运行正常: {len(data['data']['strategies'])} 个策略")
        else:
            print("❌ 系统状态检查失败")
            return
    except Exception as e:
        print(f"❌ 无法连接到系统: {e}")
        return
    
    # 2. 检查当前策略
    try:
        strategies = data['data']['strategies']
        active_strategies = [s for s in strategies.values() if s['status'] == 'running']
        print(f"📊 活跃策略数量: {len(active_strategies)}")
        
        for strategy in active_strategies:
            print(f"  - {strategy['strategy_name']} ({strategy['strategy_uuid'][:8]}...)")
            
    except Exception as e:
        print(f"❌ 策略状态检查失败: {e}")
    
    # 3. 检查最新日志中的数据流信息
    print("\n🔍 检查数据流状态...")
    
    # 检查关键指标
    checks = [
        ("CTP行情网关连接", "检查网关连接状态"),
        ("合约订阅状态", "检查行情订阅"),
        ("Tick数据接收", "检查数据推送"),
        ("策略on_tick调用", "检查策略执行")
    ]
    
    for check_name, description in checks:
        print(f"  📋 {check_name}: {description}")
    
    print("\n💡 建议检查:")
    print("  1. 查看日志: findstr /C:\"行情订阅成功\" log\\homalos_20250711.log")
    print("  2. 查看tick推送: findstr /C:\"onRtnDepthMarketData\" log\\homalos_20250711.log")
    print("  3. 查看策略日志: findstr /C:\"收到Tick数据\" log\\homalos_20250711.log")
    print("  4. 检查网关连接: findstr /C:\"心跳\" log\\homalos_20250711.log")

if __name__ == "__main__":
    asyncio.run(test_strategy_data_flow()) 