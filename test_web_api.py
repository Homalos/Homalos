#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_web_api.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: Web API测试脚本
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def print_response(response):
    """打印响应信息"""
    print(f"状态码: {response.status_code}")
    try:
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应: {response.text}")
    print("-" * 60)


def test_health():
    """测试健康检查"""
    print("\n【测试健康检查】")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response)


def test_login():
    """测试登录"""
    print("\n【测试用户登录】")
    data = {
        "username": "admin",
        "password": "admin123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", data=data)
    print_response(response)
    
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def test_get_current_user(token):
    """测试获取当前用户信息"""
    print("\n【测试获取当前用户信息】")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    print_response(response)


def test_register():
    """测试用户注册"""
    print("\n【测试用户注册】")
    data = {
        "username": "testuser",
        "password": "test123456",
        "email": "test@example.com",
        "full_name": "测试用户"
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{BASE_URL}/api/auth/register", json=data, headers=headers)
    print_response(response)


def main():
    """主函数"""
    print("=" * 60)
    print("Homalos Web API 测试")
    print("=" * 60)
    
    try:
        # 1. 健康检查
        test_health()
        
        # 2. 用户登录
        token = test_login()
        
        if token:
            # 3. 获取当前用户信息
            test_get_current_user(token)
        
        # 4. 用户注册（可选，如果用户已存在会报错）
        # test_register()
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败！请确保Web服务已启动（运行 start_web.bat）")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")


if __name__ == "__main__":
    main()
