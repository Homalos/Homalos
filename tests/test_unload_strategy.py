#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试策略卸载功能
"""
import requests

def test_unload_strategy():
    """测试策略卸载功能"""
    base_url = "http://localhost:8000"
    
    print("=== 策略卸载功能测试 ===")
    
    # 1. 获取当前策略列表
    print("\n1. 获取当前策略列表...")
    response = requests.get(f"{base_url}/api/strategies")
    if response.status_code == 200:
        strategies = response.json()["strategies"]
        print(f"当前注册的策略: {list(strategies.keys())}")
    else:
        print(f"获取策略列表失败: {response.status_code}")
        return
    
    # 2. 获取策略运行状态
    print("\n2. 获取策略运行状态...")
    response = requests.get(f"{base_url}/api/strategies/status")
    if response.status_code == 200:
        status = response.json()["running"]
        print(f"运行中的策略: {list(status.keys())}")
    else:
        print(f"获取策略状态失败: {response.status_code}")
        return
    
    # 3. 选择一个策略进行测试
    test_sid = "example_ipc_class"
    if test_sid not in strategies:
        print(f"测试策略 {test_sid} 不存在")
        return
    
    print(f"\n3. 测试策略: {test_sid}")
    is_running = test_sid in status
    print(f"当前状态: {'运行中' if is_running else '已停止'}")
    
    # 4. 如果策略正在运行，先停止它
    if is_running:
        print(f"\n4. 停止策略 {test_sid}...")
        response = requests.post(f"{base_url}/api/strategies/{test_sid}/stop")
        if response.status_code == 200:
            print("策略停止成功")
        else:
            print(f"停止策略失败: {response.status_code} - {response.text}")
            return
    
    # 5. 测试卸载已停止的策略
    print(f"\n5. 卸载策略 {test_sid}...")
    response = requests.delete(f"{base_url}/api/strategies/{test_sid}/unload")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 卸载成功: {result['message']}")
    else:
        print(f"❌ 卸载失败: {response.status_code}")
        try:
            error_detail = response.json()
            print(f"错误详情: {error_detail}")
        except Exception:
            print("错误内容:", response.text)
    
    # 6. 验证策略是否已从注册表中移除
    print("\n6. 验证策略是否已移除...")
    response = requests.get(f"{base_url}/api/strategies")
    if response.status_code == 200:
        strategies_after = response.json()["strategies"]
        if test_sid not in strategies_after:
            print(f"✅ 策略 {test_sid} 已从注册表中移除")
        else:
            print(f"❌ 策略 {test_sid} 仍在注册表中")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_unload_strategy()
