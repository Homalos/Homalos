#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_system_config_api.py
@Date       : 2025/10/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统配置 API 测试脚本
"""
import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def test_system_config_api():
    """测试系统配置 API"""
    
    print("=" * 60)
    print("系统配置 API 测试")
    print("=" * 60)
    
    # 1. 登录获取 token
    print("\n1. 登录获取 token...")
    login_url = f"{BASE_URL}/api/auth/login"
    
    # 使用表单数据格式
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        response = requests.post(
            login_url,
            data=login_data,  # 使用 data 而不是 json
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ 登录失败: {response.text}")
            return
        
        result = response.json()
        token = result.get("access_token")
        
        if not token:
            print(f"   ❌ 未获取到 token: {result}")
            return
        
        print(f"   ✅ 登录成功，token: {token[:20]}...")
        
    except Exception as e:
        print(f"   ❌ 登录异常: {e}")
        return
    
    # 2. 获取系统配置
    print("\n2. 获取系统配置...")
    get_config_url = f"{BASE_URL}/api/system-config"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(get_config_url, headers=headers)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ 获取配置失败: {response.text}")
            return
        
        config = response.json()
        print(f"   ✅ 当前配置:")
        print(f"      - dev_mode: {config.get('dev_mode')}")
        print(f"      - dev_trading_hours_check: {config.get('dev_trading_hours_check')}")
        
        original_dev_mode = config.get('dev_mode')
        
    except Exception as e:
        print(f"   ❌ 获取配置异常: {e}")
        return
    
    # 3. 更新系统配置
    print("\n3. 更新系统配置...")
    update_config_url = f"{BASE_URL}/api/system-config"
    
    # 切换 dev_mode 的值进行测试
    new_dev_mode = not original_dev_mode
    update_data = {
        "dev_mode": new_dev_mode,
        "dev_trading_hours_check": True
    }
    
    print(f"   更新数据: {update_data}")
    
    try:
        response = requests.put(
            update_config_url,
            headers={
                **headers,
                "Content-Type": "application/json"
            },
            json=update_data
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ 更新配置失败: {response.text}")
            return
        
        result = response.json()
        print(f"   ✅ 更新成功:")
        print(f"      - message: {result.get('message')}")
        print(f"      - backup: {result.get('backup')}")
        
    except Exception as e:
        print(f"   ❌ 更新配置异常: {e}")
        return
    
    # 4. 再次获取配置验证
    print("\n4. 验证配置是否已更新...")
    
    try:
        response = requests.get(get_config_url, headers=headers)
        
        if response.status_code != 200:
            print(f"   ❌ 获取配置失败: {response.text}")
            return
        
        config = response.json()
        print(f"   ✅ 更新后的配置:")
        print(f"      - dev_mode: {config.get('dev_mode')}")
        print(f"      - dev_trading_hours_check: {config.get('dev_trading_hours_check')}")
        
        # 验证是否更新成功
        if config.get('dev_mode') == new_dev_mode:
            print(f"   ✅ dev_mode 更新成功！")
        else:
            print(f"   ❌ dev_mode 未更新，期望: {new_dev_mode}, 实际: {config.get('dev_mode')}")
        
        if config.get('dev_trading_hours_check') == True:
            print(f"   ✅ dev_trading_hours_check 更新成功！")
        else:
            print(f"   ❌ dev_trading_hours_check 未更新")
        
    except Exception as e:
        print(f"   ❌ 验证配置异常: {e}")
        return
    
    # 5. 检查配置文件
    print("\n5. 检查配置文件...")
    import yaml
    from pathlib import Path
    
    config_file = Path("config/system.yaml")
    
    if not config_file.exists():
        print(f"   ❌ 配置文件不存在: {config_file}")
        return
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            file_config = yaml.safe_load(f)
        
        base_config = file_config.get('base', {})
        print(f"   ✅ 配置文件内容:")
        print(f"      - dev_mode: {base_config.get('dev_mode')}")
        print(f"      - dev_trading_hours_check: {base_config.get('dev_trading_hours_check')}")
        
        # 验证文件是否更新
        if base_config.get('dev_mode') == new_dev_mode:
            print(f"   ✅ 配置文件已同步更新！")
        else:
            print(f"   ❌ 配置文件未同步，期望: {new_dev_mode}, 实际: {base_config.get('dev_mode')}")
        
    except Exception as e:
        print(f"   ❌ 读取配置文件异常: {e}")
        return
    
    # 6. 恢复原始配置
    print("\n6. 恢复原始配置...")
    restore_data = {
        "dev_mode": original_dev_mode,
        "dev_trading_hours_check": False
    }
    
    try:
        response = requests.put(
            update_config_url,
            headers={
                **headers,
                "Content-Type": "application/json"
            },
            json=restore_data
        )
        
        if response.status_code == 200:
            print(f"   ✅ 配置已恢复到原始状态")
        else:
            print(f"   ⚠️  恢复配置失败: {response.text}")
        
    except Exception as e:
        print(f"   ❌ 恢复配置异常: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_system_config_api()

