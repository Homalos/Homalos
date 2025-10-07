#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_web_api.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 测试Web API
"""
import requests
import json


def test_register():
    """测试用户注册"""
    url = "http://localhost:8000/api/auth/register"
    data = {
        "username": "admin",
        "password": "123456",
        "email": "admin@homalos.com",
        "full_name": "系统管理员"
    }
    
    response = requests.post(url, json=data)
    print("=" * 60)
    print("测试用户注册")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print("=" * 60)
    return response.status_code == 200


def test_login(username="admin", password="123456"):
    """测试用户登录"""
    url = "http://localhost:8000/api/auth/login"
    data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(url, data=data)
    print("=" * 60)
    print("测试用户登录")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print("=" * 60)
    
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def test_get_current_user(token):
    """测试获取当前用户信息"""
    url = "http://localhost:8000/api/auth/me"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(url, headers=headers)
    print("=" * 60)
    print("测试获取当前用户信息")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print("=" * 60)
    return response.status_code == 200


def test_health_check():
    """测试健康检查"""
    url = "http://localhost:8000/health"
    response = requests.get(url)
    print("=" * 60)
    print("测试健康检查")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print("=" * 60)
    return response.status_code == 200


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("开始测试Homalos Web API")
    print("=" * 60 + "\n")
    
    # 1. 健康检查
    print("1. 健康检查...")
    if not test_health_check():
        print("❌ 健康检查失败，请确保服务已启动")
        return
    print("✅ 健康检查通过\n")
    
    # 2. 用户注册
    print("2. 测试用户注册...")
    if test_register():
        print("✅ 用户注册成功\n")
    else:
        print("⚠️ 用户可能已存在，继续测试登录...\n")
    
    # 3. 用户登录
    print("3. 测试用户登录...")
    token = test_login()
    if not token:
        print("❌ 登录失败")
        return
    print("✅ 登录成功\n")
    
    # 4. 获取用户信息
    print("4. 测试获取用户信息...")
    if test_get_current_user(token):
        print("✅ 获取用户信息成功\n")
    else:
        print("❌ 获取用户信息失败\n")
    
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n📚 API文档地址: http://localhost:8000/docs")
    print("🔧 ReDoc文档: http://localhost:8000/redoc\n")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败！请先启动Web服务：")
        print("   python start_web.py")
        print("   或")
        print("   start_web.bat\n")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}\n")

