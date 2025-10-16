#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
告警系统测试脚本
"""
import asyncio
import requests
import time

API_BASE = "http://localhost:8000/api"

def test_api_connection():
    """测试API连接"""
    print("=" * 60)
    print("测试1: API连接")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"✅ API连接成功: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ API连接失败: {e}")
        return False

def test_strategy_status():
    """测试策略状态API"""
    print("\n" + "=" * 60)
    print("测试2: 策略状态")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE}/strategies/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 策略状态API正常")
            print(f"运行中的策略: {list(data.get('running', {}).keys())}")
            
            # 检查example_ipc_class
            example_status = data.get('running', {}).get('example_ipc_class')
            if example_status:
                print(f"example_ipc_class状态:")
                print(f"  - PID: {example_status.get('pid')}")
                print(f"  - 存活: {example_status.get('alive')}")
                print(f"  - 模块: {example_status.get('module')}")
                print(f"  - 类: {example_status.get('class')}")
            else:
                print("⚠️ example_ipc_class未运行")
            return True
        else:
            print(f"❌ 策略状态API返回错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 策略状态API失败: {e}")
        return False

def test_alarm_config():
    """测试告警配置API"""
    print("\n" + "=" * 60)
    print("测试3: 告警配置")
    print("=" * 60)
    try:
        # 需要登录才能访问，这里只测试端点是否存在
        response = requests.get(f"{API_BASE}/alarms/config/settings", timeout=5)
        if response.status_code == 401:
            print(f"✅ 告警配置API存在（需要登录）")
            return True
        elif response.status_code == 200:
            data = response.json()
            print(f"✅ 告警配置API正常")
            print(f"CPU阈值: {data.get('cpu_threshold')}%")
            print(f"内存阈值: {data.get('memory_threshold')}%")
            print(f"保留天数: {data.get('retention_days')}天")
            print(f"邮件通知: {'启用' if data.get('email_enabled') else '禁用'}")
            return True
        else:
            print(f"❌ 告警配置API返回错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 告警配置API失败: {e}")
        return False

def test_alarm_stats():
    """测试告警统计API"""
    print("\n" + "=" * 60)
    print("测试4: 告警统计")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE}/alarms/stats/summary", timeout=5)
        if response.status_code == 401:
            print(f"✅ 告警统计API存在（需要登录）")
            return True
        elif response.status_code == 200:
            data = response.json()
            print(f"✅ 告警统计API正常")
            print(f"今日告警: {data.get('today_count')}")
            print(f"未处理: {data.get('active_count')}")
            return True
        else:
            print(f"❌ 告警统计API返回错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 告警统计API失败: {e}")
        return False

def main():
    """主测试函数"""
    print("\n🚀 Homalos 告警系统测试")
    print("请确保Web服务已启动 (python start_web.py)\n")
    
    time.sleep(1)
    
    results = []
    results.append(test_api_connection())
    results.append(test_strategy_status())
    results.append(test_alarm_config())
    results.append(test_alarm_stats())
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
    
    print("\n提示:")
    print("- 如果告警API返回401，请在前端登录后重试")
    print("- 如果策略未运行，请在前端策略管理页面启动")
    print("- 完整功能测试请访问前端界面 http://localhost:5173")

if __name__ == "__main__":
    main()

