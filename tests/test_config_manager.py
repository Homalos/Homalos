#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置管理器功能测试脚本
测试ConfigManager的所有主要功能
"""
import os
# 激活虚拟环境并导入模块
import sys
import tempfile
import time

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.config_manager import ConfigManager, get_config_manager, get_config, set_config, watch_config

def create_test_config():
    """创建测试配置文件"""
    test_config = {
        "system": {
            "name": "Test System",
            "version": "1.0.0",
            "debug": True
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "test_db"
        },
        "features": {
            "logging": True,
            "monitoring": False,
            "cache": {
                "enabled": True,
                "size": 1000
            }
        }
    }
    return test_config

def test_basic_operations():
    """测试基本操作：创建、获取、设置配置"""
    print("\n" + "="*50)
    print("测试基本操作")
    print("="*50)
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = create_test_config()
        yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        config_file = f.name
    
    try:
        # 创建配置管理器
        cm = ConfigManager(config_file)
        
        # 测试获取配置
        print("1. 测试获取配置值:")
        assert cm.get("system.name") == "Test System"
        assert cm.get("database.port") == 5432
        assert cm.get("features.cache.size") == 1000
        assert cm.get("nonexistent.key", "default") == "default"
        print("   ✓ 获取配置值测试通过")
        
        # 测试设置配置
        print("2. 测试设置配置值:")
        cm.set("system.version", "2.0.0")
        cm.set("new.section.value", 123)
        cm.set("features.cache.size", 2000)
        
        assert cm.get("system.version") == "2.0.0"
        assert cm.get("new.section.value") == 123
        assert cm.get("features.cache.size") == 2000
        print("   ✓ 设置配置值测试通过")
        
        # 测试has_key方法
        print("3. 测试键存在检查:")
        assert cm.has_key("system.name") == True
        assert cm.has_key("nonexistent.key") == False
        assert cm.has_key("features.cache.enabled") == True
        print("   ✓ 键存在检查测试通过")
        
        # 测试get_all方法
        print("4. 测试获取所有配置:")
        all_config = cm.get_all()
        assert "system" in all_config
        assert "database" in all_config
        assert "features" in all_config
        print("   ✓ 获取所有配置测试通过")
        
    finally:
        # 清理临时文件
        os.unlink(config_file)
    
    print("   ✓ 基本操作测试全部通过")

def test_watchers():
    """测试配置监听器功能"""
    print("\n" + "="*50)
    print("测试配置监听器")
    print("="*50)
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = create_test_config()
        yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        config_file = f.name
    
    try:
        cm = ConfigManager(config_file)
        
        # 记录回调调用
        callback_calls = []
        
        def test_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))
            print(f"   回调触发: {key} = {old_value} -> {new_value}")
        
        # 测试特定键监听
        print("1. 测试特定键监听:")
        cm.watch("system.version", test_callback)
        cm.set("system.version", "3.0.0")
        assert len(callback_calls) == 1
        assert callback_calls[0] == ("system.version", "1.0.0", "3.0.0")
        print("   ✓ 特定键监听测试通过")
        
        # 测试通配符监听
        print("2. 测试通配符监听:")
        callback_calls.clear()
        cm.watch("system.*", test_callback)
        cm.set("system.name", "New System")
        assert len(callback_calls) == 1
        print("   ✓ 通配符监听测试通过")
        
        # 测试全局监听
        print("3. 测试全局监听:")
        callback_calls.clear()
        cm.watch("*", test_callback)
        cm.set("database.host", "newhost")
        assert len(callback_calls) == 1
        print("   ✓ 全局监听测试通过")
        
    finally:
        os.unlink(config_file)
    
    print("   ✓ 配置监听器测试全部通过")

def test_hot_reload():
    """测试热重载功能"""
    print("\n" + "="*50)
    print("测试热重载功能")
    print("="*50)
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = create_test_config()
        yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        config_file = f.name
    
    try:
        cm = ConfigManager(config_file)
        
        # 记录回调调用
        callback_calls = []
        
        def reload_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))
            print(f"   重载回调: {key} = {old_value} -> {new_value}")
        
        cm.watch("*", reload_callback)
        
        # 测试文件不存在的情况
        print("1. 测试文件不存在:")
        os.unlink(config_file)
        result = cm.reload()
        assert result == False
        print("   ✓ 文件不存在测试通过")
        
        # 重新创建文件并测试热重载
        print("2. 测试文件热重载:")
        new_config = {
            "system": {
                "name": "Reloaded System",
                "version": "2.0.0"
            },
            "new_section": {
                "value": 456
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(new_config, f, default_flow_style=False, allow_unicode=True)
        
        # 等待文件系统更新
        time.sleep(0.1)
        
        result = cm.reload()
        assert result == True
        assert cm.get("system.name") == "Reloaded System"
        assert cm.get("new_section.value") == 456
        assert len(callback_calls) > 0
        print("   ✓ 文件热重载测试通过")
        
    finally:
        if os.path.exists(config_file):
            os.unlink(config_file)
    
    print("   ✓ 热重载功能测试全部通过")

def test_global_functions():
    """测试全局函数"""
    print("\n" + "="*50)
    print("测试全局函数")
    print("="*50)
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = create_test_config()
        yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        config_file = f.name
    
    try:
        # 测试全局配置管理器
        print("1. 测试全局配置管理器:")
        cm = get_config_manager(config_file)
        assert cm.get("system.name") == "Test System"
        print("   ✓ 全局配置管理器测试通过")
        
        # 测试快捷函数
        print("2. 测试快捷函数:")
        assert get_config("system.version") == "1.0.0"
        set_config("tests.key", "test_value")
        assert get_config("tests.key") == "test_value"
        print("   ✓ 快捷函数测试通过")
        
        # 测试全局监听器
        print("3. 测试全局监听器:")
        callback_calls = []
        
        def global_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))
            print(f"   全局回调: {key} = {old_value} -> {new_value}")
        
        watch_config("tests.*", global_callback)
        set_config("tests.new_key", "new_value")
        assert len(callback_calls) == 1
        print("   ✓ 全局监听器测试通过")
        
    finally:
        os.unlink(config_file)
    
    print("   ✓ 全局函数测试全部通过")

def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*50)
    print("测试错误处理")
    print("="*50)
    
    # 测试不存在的配置文件
    print("1. 测试不存在的配置文件:")
    cm = ConfigManager("nonexistent_config.yaml")
    assert cm.get("any.key", "default") == "default"
    assert cm.get_all() == {}
    print("   ✓ 不存在配置文件测试通过")
    
    # 测试无效的YAML文件
    print("2. 测试无效的YAML文件:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: content: [")
        config_file = f.name
    
    try:
        cm = ConfigManager(config_file)
        # 应该优雅地处理错误并返回空配置
        assert cm.get_all() == {}
        print("   ✓ 无效YAML文件测试通过")
    finally:
        os.unlink(config_file)
    
    # 测试回调函数异常
    print("3. 测试回调函数异常:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = create_test_config()
        yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        config_file = f.name
    
    try:
        cm = ConfigManager(config_file)
        
        def error_callback(key, old_value, new_value):
            raise Exception("测试异常")
        
        cm.watch("system.name", error_callback)
        # 应该不会抛出异常
        cm.set("system.name", "Error Test")
        print("   ✓ 回调函数异常测试通过")
        
    finally:
        os.unlink(config_file)
    
    print("   ✓ 错误处理测试全部通过")

def test_save_functionality():
    """测试保存功能"""
    print("\n" + "="*50)
    print("测试保存功能")
    print("="*50)
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = create_test_config()
        yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        config_file = f.name
    
    try:
        cm = ConfigManager(config_file)
        
        # 修改配置
        cm.set("system.version", "5.0.0")
        cm.set("new.section", {"key": "value"})
        
        # 保存配置
        cm.save()
        
        # 验证文件内容
        with open(config_file, 'r') as f:
            saved_config = yaml.safe_load(f)
        
        assert saved_config["system"]["version"] == "5.0.0"
        assert saved_config["new"]["section"]["key"] == "value"
        print("   ✓ 保存功能测试通过")
        
    finally:
        os.unlink(config_file)
    
    print("   ✓ 保存功能测试全部通过")

def main():
    """主测试函数"""
    print("开始配置管理器功能测试")
    print("="*60)
    
    try:
        # 运行所有测试
        test_basic_operations()
        test_watchers()
        test_hot_reload()
        test_global_functions()
        test_error_handling()
        test_save_functionality()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！配置管理器功能正常")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 