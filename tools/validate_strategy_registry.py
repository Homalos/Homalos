#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : validate_strategy_registry.py
@Date       : 2025/10/17
@Author     : Lumosylva
@Description: 验证策略注册表配置是否正确
"""
import json
import sys
from pathlib import Path

def validate_strategy_registry(registry_path: str = "config/strategy_registry.json"):
    """
    验证策略注册表配置
    
    Args:
        registry_path: 注册表文件路径
    """
    print("=" * 60)
    print("策略注册表验证工具")
    print("=" * 60)
    print()
    
    # 1. 检查文件是否存在
    registry_file = Path(registry_path)
    if not registry_file.exists():
        print(f"❌ 错误: 注册表文件不存在: {registry_path}")
        return False
    
    print(f"✅ 注册表文件存在: {registry_path}")
    
    # 2. 检查JSON格式
    try:
        with open(registry_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ 错误: JSON格式错误")
        print(f"   详细: {e}")
        return False
    
    print(f"✅ JSON格式正确")
    
    # 3. 检查配置内容
    if not config:
        print("⚠️  警告: 注册表为空，没有配置任何策略")
        return True
    
    print(f"✅ 发现 {len(config)} 个策略配置")
    print()
    
    # 4. 验证每个策略配置
    errors = []
    warnings = []
    enabled_count = 0
    
    for strategy_id, strategy_config in config.items():
        print(f"📋 验证策略: {strategy_id}")
        print(f"   {'─' * 50}")
        
        # 检查必填字段
        required_fields = ['file', 'module', 'class', 'enabled']
        missing_fields = [field for field in required_fields if field not in strategy_config]
        
        if missing_fields:
            error_msg = f"   ❌ 缺少必填字段: {', '.join(missing_fields)}"
            print(error_msg)
            errors.append(f"{strategy_id}: {error_msg}")
            continue
        
        # 检查文件是否存在
        strategy_file = Path(strategy_config['file'])
        if not strategy_file.exists():
            error_msg = f"   ❌ 策略文件不存在: {strategy_config['file']}"
            print(error_msg)
            errors.append(f"{strategy_id}: {error_msg}")
        else:
            print(f"   ✅ 文件: {strategy_config['file']}")
        
        # 打印配置信息
        print(f"   📦 模块: {strategy_config['module']}")
        print(f"   🏷️  类名: {strategy_config['class']}")
        
        # 检查启用状态
        if strategy_config['enabled']:
            print(f"   🟢 状态: 已启用")
            enabled_count += 1
        else:
            print(f"   ⚪ 状态: 已禁用")
        
        # 检查参数
        params = strategy_config.get('params', {})
        if params:
            print(f"   ⚙️  参数: {json.dumps(params, ensure_ascii=False)}")
        else:
            print(f"   ⚙️  参数: 无")
        
        # 检查module路径格式
        module_path = strategy_config['module']
        if '/' in module_path or '\\' in module_path:
            warning_msg = f"   ⚠️  警告: module路径应使用点分隔，不是斜杠"
            print(warning_msg)
            warnings.append(f"{strategy_id}: {warning_msg}")
        
        print()
    
    # 5. 输出总结
    print("=" * 60)
    print("验证总结")
    print("=" * 60)
    print(f"总策略数: {len(config)}")
    print(f"已启用: {enabled_count}")
    print(f"已禁用: {len(config) - enabled_count}")
    print()
    
    if errors:
        print(f"❌ 发现 {len(errors)} 个错误:")
        for error in errors:
            print(f"   {error}")
        print()
    
    if warnings:
        print(f"⚠️  发现 {len(warnings)} 个警告:")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    if not errors and not warnings:
        print("✅ 所有配置验证通过!")
        print()
        print("🚀 可以启动策略的配置:")
        for strategy_id, strategy_config in config.items():
            if strategy_config['enabled']:
                print(f"   - {strategy_id}")
        return True
    elif not errors:
        print("✅ 配置基本正确，但有一些警告需要注意")
        return True
    else:
        print("❌ 配置存在错误，请修复后重试")
        return False


def main():
    """主函数"""
    registry_path = "config/strategy_registry.json"
    
    if len(sys.argv) > 1:
        registry_path = sys.argv[1]
    
    success = validate_strategy_registry(registry_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

