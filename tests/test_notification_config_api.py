#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通知配置API测试脚本

测试通知配置的双向同步功能
"""
import requests
import json
import sys

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


def get_notification_config(token):
    """获取通知配置"""
    print("\n========== 2. 获取通知配置 ==========")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/system-config/notification",
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


def update_notification_config(token, config):
    """更新通知配置"""
    print("\n========== 3. 更新通知配置 ==========")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 修改配置
    test_config = {
        "dingtalk": {
            "enabled": True,
            "name": "测试钉钉机器人",
            "id": "test_dingtalk_id",
            "webhookUrl": "https://test.dingtalk.com/webhook"
        },
        "wecom": {
            "enabled": True,
            "name": "测试企业微信机器人",
            "corpId": "test_corp_id",
            "agentId": 9999,
            "appSecret": "test_secret"
        },
        "email": {
            "enabled": False,
            "address": "test@example.com",
            "smtpServer": "smtp.example.com"
        }
    }
    
    print("发送配置:")
    print(json.dumps(test_config, indent=2, ensure_ascii=False))
    
    response = requests.put(
        f"{BASE_URL}/api/system-config/notification",
        headers=headers,
        json=test_config
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


def verify_notification_config(token, expected_config):
    """验证配置是否更新成功"""
    print("\n========== 4. 验证配置是否更新 ==========")
    config = get_notification_config(token)
    
    if config:
        # 比较钉钉配置
        if (config.get('dingtalk', {}).get('name') == expected_config['dingtalk']['name'] and
            config.get('dingtalk', {}).get('enabled') == expected_config['dingtalk']['enabled']):
            print("✓ 钉钉配置验证成功")
        else:
            print("✗ 钉钉配置验证失败")
        
        # 比较企业微信配置
        if (config.get('wecom', {}).get('name') == expected_config['wecom']['name'] and
            config.get('wecom', {}).get('enabled') == expected_config['wecom']['enabled']):
            print("✓ 企业微信配置验证成功")
        else:
            print("✗ 企业微信配置验证失败")
        
        # 比较邮件配置
        if (config.get('email', {}).get('address') == expected_config['email']['address'] and
            config.get('email', {}).get('enabled') == expected_config['email']['enabled']):
            print("✓ 邮件配置验证成功")
        else:
            print("✗ 邮件配置验证失败")
        
        return True
    return False


def restore_original_config(token, original_config):
    """恢复原始配置"""
    print("\n========== 5. 恢复原始配置 ==========")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/system-config/notification",
        headers=headers,
        json=original_config
    )
    
    if response.status_code == 200:
        print("✓ 原始配置已恢复")
        return True
    else:
        print(f"✗ 恢复失败: {response.status_code}")
        return False


def main():
    """主测试流程"""
    print("=" * 50)
    print("通知配置API测试")
    print("=" * 50)
    
    # 1. 登录
    token = login()
    
    # 2. 获取原始配置（用于后续恢复）
    original_config = get_notification_config(token)
    if not original_config:
        print("✗ 无法获取原始配置，测试终止")
        sys.exit(1)
    
    # 3. 更新配置
    test_config = {
        "dingtalk": {
            "enabled": True,
            "name": "测试钉钉机器人",
            "id": "test_dingtalk_id",
            "webhookUrl": "https://test.dingtalk.com/webhook"
        },
        "wecom": {
            "enabled": True,
            "name": "测试企业微信机器人",
            "corpId": "test_corp_id",
            "agentId": 9999,
            "appSecret": "test_secret"
        },
        "email": {
            "enabled": False,
            "address": "test@example.com",
            "smtpServer": "smtp.example.com"
        }
    }
    
    if not update_notification_config(token, test_config):
        print("✗ 更新配置失败，测试终止")
        sys.exit(1)
    
    # 4. 验证更新
    verify_notification_config(token, test_config)
    
    # 5. 恢复原始配置
    restore_original_config(token, original_config)
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

