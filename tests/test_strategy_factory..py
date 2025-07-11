#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : test_strategy_factory
@Date       : 2025/7/9 12:12
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略工厂测试 - 演示策略的创建和管理
"""
import asyncio
from src.strategies.strategy_factory import create_strategy, get_available_strategies, EXAMPLE_STRATEGIES
from src.core.event_bus import EventBus


async def test_strategy_factory():
    """测试策略工厂功能"""
    print("=" * 60)
    print("策略工厂测试")
    print("=" * 60)

    # 创建事件总线
    event_bus = EventBus(name="StrategyTest")

    # 1. 查看可用策略
    print("\n1. 可用策略列表:")
    available_strategies = get_available_strategies()
    for strategy_type, info in available_strategies.items():
        print(f"  - {strategy_type}: {info['strategy_name']} v{info['version']}")
        print(f"    描述: {info['description']}")
        print(f"    作者: {', '.join(info['authors'])}")

    # 2. 创建移动平均策略
    print("\n2. 创建移动平均策略:")
    ma_params = EXAMPLE_STRATEGIES["ma_ag2412"]["params"]
    ma_strategy = create_strategy(
        strategy_type="moving_average",
        strategy_id="test_ma_ag2412",
        event_bus=event_bus,
        params=ma_params
    )
    print(f"  策略ID: {ma_strategy.strategy_id}")
    print(f"  策略名称: {ma_strategy.strategy_name}")
    print(f"  交易品种: {ma_strategy.get_parameter('symbol')}")
    print(f"  短期均线: {ma_strategy.get_parameter('short_window')}")
    print(f"  长期均线: {ma_strategy.get_parameter('long_window')}")

    # 3. 创建网格交易策略
    print("\n3. 创建网格交易策略:")
    grid_params = EXAMPLE_STRATEGIES["grid_au2412"]["params"]
    grid_strategy = create_strategy(
        strategy_type="grid_trading",
        strategy_id="test_grid_au2412",
        event_bus=event_bus,
        params=grid_params
    )
    print(f"  策略ID: {grid_strategy.strategy_id}")
    print(f"  策略名称: {grid_strategy.strategy_name}")
    print(f"  交易品种: {grid_strategy.get_parameter('symbol')}")
    print(f"  网格间距: {grid_strategy.get_parameter('grid_spacing')}")
    print(f"  网格数量: {grid_strategy.get_parameter('grid_count')}")

    # 4. 测试策略初始化
    print("\n4. 测试策略初始化:")
    try:
        await ma_strategy.initialize()
        print("  ✓ 移动平均策略初始化成功")

        await grid_strategy.initialize()
        print("  ✓ 网格交易策略初始化成功")
    except Exception as e:
        print(f"  ✗ 策略初始化失败: {e}")

    # 5. 测试策略启动
    print("\n5. 测试策略启动:")
    try:
        await ma_strategy.start()
        print("  ✓ 移动平均策略启动成功")

        await grid_strategy.start()
        print("  ✓ 网格交易策略启动成功")
    except Exception as e:
        print(f"  ✗ 策略启动失败: {e}")

    # 6. 查看策略状态
    print("\n6. 策略状态:")
    ma_stats = ma_strategy.get_strategy_stats()
    grid_stats = grid_strategy.get_strategy_stats()

    print(f"  移动平均策略: active={ma_stats['active']}, runtime={ma_stats['runtime']}")
    print(f"  网格交易策略: active={grid_stats['active']}, runtime={grid_stats['runtime']}")

    # 7. 测试策略停止
    print("\n7. 测试策略停止:")
    try:
        await ma_strategy.stop()
        print("  ✓ 移动平均策略停止成功")

        await grid_strategy.stop()
        print("  ✓ 网格交易策略停止成功")
    except Exception as e:
        print(f"  ✗ 策略停止失败: {e}")

    # 停止事件总线
    event_bus.stop()

    print("\n" + "=" * 60)
    print("策略工厂测试完成")
    print("=" * 60)


def test_strategy_creation_methods():
    """测试不同的策略创建方法"""
    print("\n" + "=" * 60)
    print("策略创建方法对比")
    print("=" * 60)

    # 方法1: 直接实例化（不推荐）
    print("\n方法1: 直接实例化策略类")
    print("优点: 简单直接")
    print("缺点: 硬编码，不易扩展，无法动态配置")
    print("适用场景: 开发测试阶段")

    # 方法2: 使用策略工厂（推荐）
    print("\n方法2: 使用策略工厂")
    print("优点: 统一管理，支持动态配置，易于扩展")
    print("缺点: 需要额外的工厂类")
    print("适用场景: 生产环境，需要动态加载策略")

    # 方法3: 配置文件驱动
    print("\n方法3: 配置文件驱动")
    print("优点: 完全解耦，支持热更新")
    print("缺点: 需要配置文件管理")
    print("适用场景: 大型系统，多策略管理")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_strategy_factory())
    test_strategy_creation_methods()
