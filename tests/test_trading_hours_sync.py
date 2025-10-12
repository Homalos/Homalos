#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交易时间检查配置同步测试脚本

测试开发模式和生产模式下交易时间检查配置的同步功能
"""
import requests
import json
import sys
from pathlib import Path

# API基础URL
BASE_URL = "http://localhost:8000"

# 测试用户凭证
TEST_USER = {
    "username": "admin",
    "password": "admin123456"
}


def login():
    """登录获取token"""
    print("\n========== 1. 登录 ==========")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data=TEST_USER
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"✓ 登录成功，Token: {token[:20]}...")
        return token
    else:
        print(f"✗ 登录失败: {response.status_code}")
        print(response.text)
        sys.exit(1)


def get_system_config(token):
    """获取系统配置"""
    print("\n========== 2. 获取系统配置 ==========")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/system-config",
        headers=headers
    )
    
    if response.status_code == 200:
        config = response.json()
        print("✓ 获取成功:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return config
    else:
        print(f"✗ 获取失败: {response.status_code}")
        print(response.text)
        return None


def update_system_config(token, config):
    """更新系统配置"""
    print("\n========== 3. 更新系统配置 ==========")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("发送配置:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    response = requests.put(
        f"{BASE_URL}/api/system-config",
        headers=headers,
        json=config
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ 更新成功:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return True
    else:
        print(f"✗ 更新失败: {response.status_code}")
        print(response.text)
        return False


def check_extra_config_file(dev_mode, expected_enable_check):
    """检查 extra 配置文件"""
    import yaml
    from ruamel.yaml import YAML
    
    config_file = Path("config/extra.dev.yaml") if dev_mode else Path("config/extra.prod.yaml")
    print(f"\n========== 4. 检查配置文件 {config_file} ==========")
    
    try:
        yaml_handler = YAML()
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml_handler.load(f)
        
        actual_enable_check = config.get('trading_hours', {}).get('enable_check')
        print(f"配置文件中的 enable_check: {actual_enable_check}")
        print(f"期望值: {expected_enable_check}")
        
        if actual_enable_check == expected_enable_check:
            print("✓ 配置文件验证成功")
            return True
        else:
            print("✗ 配置文件验证失败")
            return False
    except Exception as e:
        print(f"✗ 读取配置文件失败: {e}")
        return False


def test_dev_mode():
    """测试开发模式"""
    print("\n" + "=" * 60)
    print("测试场景 1: 开发模式下修改交易时间检查")
    print("=" * 60)
    
    token = login()
    
    # 1. 获取原始配置
    original_config = get_system_config(token)
    if not original_config:
        print("✗ 无法获取原始配置，测试终止")
        return False
    
    # 2. 设置开发模式并禁用交易时间检查
    print("\n>>> 步骤：设置开发模式=true，交易时间检查=false")
    update_config = {
        "dev_mode": True,
        "dev_trading_hours_check": False
    }
    
    if not update_system_config(token, update_config):
        print("✗ 更新失败")
        return False
    
    # 3. 验证配置文件
    if not check_extra_config_file(dev_mode=True, expected_enable_check=False):
        print("✗ 配置文件验证失败")
        return False
    
    # 4. 重新获取配置验证
    new_config = get_system_config(token)
    if new_config and new_config.get('dev_trading_hours_check') == False:
        print("✓ API 返回值验证成功")
    else:
        print("✗ API 返回值验证失败")
        return False
    
    # 5. 启用交易时间检查
    print("\n>>> 步骤：设置交易时间检查=true")
    update_config = {
        "dev_mode": True,
        "dev_trading_hours_check": True
    }
    
    if not update_system_config(token, update_config):
        print("✗ 更新失败")
        return False
    
    # 6. 验证配置文件
    if not check_extra_config_file(dev_mode=True, expected_enable_check=True):
        print("✗ 配置文件验证失败")
        return False
    
    print("\n✅ 开发模式测试通过")
    return True


def test_prod_mode():
    """测试生产模式"""
    print("\n" + "=" * 60)
    print("测试场景 2: 生产模式下交易时间检查永远为 true")
    print("=" * 60)
    
    token = login()
    
    # 1. 切换到生产模式
    print("\n>>> 步骤：切换到生产模式")
    update_config = {
        "dev_mode": False
    }
    
    if not update_system_config(token, update_config):
        print("✗ 更新失败")
        return False
    
    # 2. 验证 API 返回值应该是 true（从 extra.prod.yaml 读取）
    config = get_system_config(token)
    if config and config.get('dev_trading_hours_check') == True:
        print("✓ 生产模式下交易时间检查为 true")
    else:
        print(f"✗ 生产模式下交易时间检查应该为 true，实际为: {config.get('dev_trading_hours_check')}")
        return False
    
    # 3. 尝试修改交易时间检查（应该不生效）
    print("\n>>> 步骤：尝试在生产模式下修改交易时间检查（应该被忽略）")
    update_config = {
        "dev_mode": False,
        "dev_trading_hours_check": False  # 尝试设置为 false
    }
    
    update_system_config(token, update_config)
    
    # 4. 验证 extra.prod.yaml 仍然是 true
    if not check_extra_config_file(dev_mode=False, expected_enable_check=True):
        print("✗ extra.prod.yaml 应该保持为 true")
        return False
    
    # 5. 验证 API 返回值仍然是 true
    config = get_system_config(token)
    if config and config.get('dev_trading_hours_check') == True:
        print("✓ 生产模式下交易时间检查仍然为 true（修改被忽略）")
    else:
        print("✗ 生产模式下交易时间检查应该保持为 true")
        return False
    
    print("\n✅ 生产模式测试通过")
    return True


def restore_dev_mode(token):
    """恢复到开发模式"""
    print("\n========== 5. 恢复到开发模式 ==========")
    update_config = {
        "dev_mode": True,
        "dev_trading_hours_check": False
    }
    
    if update_system_config(token, update_config):
        print("✓ 已恢复到开发模式")
        return True
    else:
        print("✗ 恢复失败")
        return False


def main():
    """主测试流程"""
    print("=" * 60)
    print("交易时间检查配置同步测试")
    print("=" * 60)
    
    try:
        # 测试开发模式
        if not test_dev_mode():
            print("\n✗ 开发模式测试失败")
            sys.exit(1)
        
        # 测试生产模式
        if not test_prod_mode():
            print("\n✗ 生产模式测试失败")
            sys.exit(1)
        
        # 恢复到开发模式
        token = login()
        restore_dev_mode(token)
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

