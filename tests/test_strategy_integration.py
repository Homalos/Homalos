#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试策略集成脚本
验证策略是否正确初始化和执行
"""
import datetime
import time

from tests.test_alarm import AlarmScheduler


def test_strategy_integration():
    """测试策略集成"""
    print("=" * 50)
    print("开始测试策略集成")
    print("=" * 50)
    
    # 计算测试时间 - 10秒后触发闹钟
    now_time = datetime.datetime.now()
    test_time = now_time + datetime.timedelta(seconds=10)
    test_time_str = test_time.strftime('%H:%M')
    
    print(f"当前时间: {now_time.strftime('%H:%M:%S')}")
    print(f"设置闹钟时间: {test_time_str}")
    
    # 创建调度器
    scheduler = AlarmScheduler()
    
    # 检查策略是否正确初始化
    print(f"\n策略数量: {len(scheduler.strategy_map)}")
    for strategy_id, strategy in scheduler.strategy_map.items():
        print(f"策略ID: {strategy_id}")
        print(f"策略名称: {strategy.strategy_name}")
        print(f"订阅合约: {strategy.sub_ins_id}")
        print(f"具体策略映射: {list(strategy.specific_strategy_map.keys())}")
        
        # 检查每个合约的具体策略是否正确初始化
        for instrument_id, specific_strategy in strategy.specific_strategy_map.items():
            if specific_strategy is None:
                print(f"❌ 合约 {instrument_id} 的具体策略未初始化！")
            else:
                print(f"✅ 合约 {instrument_id} 的具体策略已初始化")
    
    # 设置测试闹钟
    scheduler.alarm.set_alarm(test_time_str, "1001")
    print(f"\n✅ 已设置测试闹钟: {test_time_str} -> 策略1001")
    
    # 启动调度器
    if scheduler.start():
        print("✅ 调度器启动成功")
        
        # 等待闹钟触发
        print(f"等待闹钟触发... (预计{10}秒后)")
        
        # 运行15秒后停止
        time.sleep(15)
        
        # 获取状态
        status = scheduler.get_status()
        print(f"\n调度器状态:")
        print(f"  执行次数: {status['execution_count']}")
        print(f"  策略数量: {status['strategy_count']}")
        print(f"  闹钟数量: {status['alarm_count']}")
        print(f"  最后执行时间: {status['last_execution']}")
        
        # 停止调度器
        scheduler.stop()
        print("✅ 调度器已停止")
    else:
        print("❌ 调度器启动失败")
    
    print("=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    test_strategy_integration()
