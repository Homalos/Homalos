#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_strategy_api.py
@Date       : 2025/10/16
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略API测试脚本

运行前确保:
1. 启动 Web 服务: python -m src.web.main 或 uvicorn src.web.main:app --reload
2. 确保 strategies.json 中有测试策略配置

测试命令:
python tests/test_strategy_api.py
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/strategies"


def print_response(title, response):
    """打印响应"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    try:
        print(f"响应数据:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应文本: {response.text}")


def test_list_strategies():
    """测试: 获取策略列表"""
    response = requests.get(f"{BASE_URL}/")
    print_response("1. 获取策略列表", response)
    
    if response.status_code == 200:
        data = response.json()
        strategies = data.get("strategies", {})
        print(f"\n✅ 成功! 找到 {len(strategies)} 个策略")
        return list(strategies.keys())
    else:
        print(f"\n❌ 失败!")
        return []


def test_get_status():
    """测试: 获取运行状态"""
    response = requests.get(f"{BASE_URL}/status")
    print_response("2. 获取运行状态", response)
    
    if response.status_code == 200:
        data = response.json()
        running = data.get("running", {})
        print(f"\n✅ 成功! {len(running)} 个策略正在运行")
        return True
    else:
        print(f"\n❌ 失败!")
        return False


def test_start_strategy(sid):
    """测试: 启动策略"""
    response = requests.post(f"{BASE_URL}/{sid}/start")
    print_response(f"3. 启动策略 {sid}", response)
    
    if response.status_code == 200:
        print(f"\n✅ 成功!")
        return True
    else:
        print(f"\n❌ 失败!")
        return False


def test_stop_strategy(sid):
    """测试: 停止策略"""
    response = requests.post(f"{BASE_URL}/{sid}/stop")
    print_response(f"4. 停止策略 {sid}", response)
    
    if response.status_code == 200:
        print(f"\n✅ 成功!")
        return True
    else:
        print(f"\n❌ 失败!")
        return False


def test_reload_strategy(sid):
    """测试: 重载策略"""
    response = requests.post(f"{BASE_URL}/{sid}/reload", timeout=10)
    print_response(f"5. 重载策略 {sid}", response)
    
    if response.status_code == 200:
        print(f"\n✅ 成功!")
        return True
    else:
        print(f"\n❌ 失败!")
        return False


def test_enable_strategy(sid):
    """测试: 启用策略"""
    response = requests.post(f"{BASE_URL}/{sid}/enable")
    print_response(f"6. 启用策略 {sid}", response)
    
    if response.status_code == 200:
        print(f"\n✅ 成功!")
        return True
    else:
        print(f"\n❌ 失败!")
        return False


def test_disable_strategy(sid):
    """测试: 禁用策略"""
    response = requests.post(f"{BASE_URL}/{sid}/disable")
    print_response(f"7. 禁用策略 {sid}", response)
    
    if response.status_code == 200:
        print(f"\n✅ 成功!")
        return True
    else:
        print(f"\n❌ 失败!")
        return False


def main():
    """主测试流程"""
    print("🚀 开始测试策略API...")
    print(f"目标服务: {BASE_URL}")
    
    try:
        # 检查服务是否可用
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print("❌ 服务未启动，请先启动 Web 服务!")
            return
    except:
        print("❌ 无法连接到服务，请确保 Web 服务正在运行!")
        return
    
    # 1. 获取策略列表
    strategy_ids = test_list_strategies()
    if not strategy_ids:
        print("\n⚠️  没有找到策略，请检查 strategies.json 配置")
        return
    
    # 选择第一个策略进行测试
    test_sid = strategy_ids[0]
    print(f"\n📌 使用策略 '{test_sid}' 进行测试")
    
    # 2. 获取状态
    time.sleep(1)
    test_get_status()
    
    # 3. 启动策略
    time.sleep(1)
    test_start_strategy(test_sid)
    
    # 等待策略启动
    time.sleep(2)
    
    # 4. 再次查看状态
    time.sleep(1)
    test_get_status()
    
    # 5. 重载策略
    time.sleep(1)
    print("\n⏳ 正在重载策略，这可能需要5-10秒...")
    test_reload_strategy(test_sid)
    
    # 等待重载完成
    print("⏳ 等待重载完成...")
    time.sleep(3)
    
    # 6. 停止策略
    time.sleep(1)
    test_stop_strategy(test_sid)
    
    # 等待策略停止
    time.sleep(2)
    
    # 7. 禁用策略
    time.sleep(1)
    test_disable_strategy(test_sid)
    
    # 8. 启用策略
    time.sleep(1)
    test_enable_strategy(test_sid)
    
    # 最终状态
    time.sleep(1)
    test_get_status()
    
    print("\n" + "="*60)
    print("✨ 测试完成!")
    print("="*60)


if __name__ == "__main__":
    main()

