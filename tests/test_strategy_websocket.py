#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_strategy_websocket.py
@Date       : 2025/10/16
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略WebSocket测试脚本

运行前确保:
1. 启动 Web 服务
2. 安装 websocket-client: pip install websocket-client

测试命令:
python tests/test_strategy_websocket.py
"""
import json
import time
import threading
try:
    import websocket
except ImportError:
    print("❌ 请先安装 websocket-client: pip install websocket-client")
    exit(1)

import requests

BASE_URL = "http://localhost:8000/api/strategies"
WS_URL = "ws://localhost:8000/api/strategies/ws"


def on_message(ws, message):
    """接收到消息时的回调"""
    try:
        data = json.loads(message)
        msg_type = data.get("type", "unknown")
        sid = data.get("sid", "unknown")
        payload = data.get("payload", "")
        
        # 根据类型着色输出
        color_map = {
            "log": "\033[94m",      # 蓝色
            "error": "\033[91m",    # 红色
            "status": "\033[93m",   # 黄色
            "stopped": "\033[90m",  # 灰色
        }
        color = color_map.get(msg_type, "\033[0m")
        reset = "\033[0m"
        
        timestamp = time.strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] [{sid}] {msg_type}: {payload}{reset}")
        
        # 如果有错误堆栈，也打印出来
        if data.get("trace"):
            print(f"{color}堆栈:\n{data['trace']}{reset}")
            
    except Exception as e:
        print(f"❌ 解析消息失败: {e}")
        print(f"原始消息: {message}")


def on_error(ws, error):
    """发生错误时的回调"""
    print(f"\n❌ WebSocket错误: {error}")


def on_close(ws, close_status_code, close_msg):
    """连接关闭时的回调"""
    print(f"\n🔌 WebSocket连接已关闭 (code: {close_status_code}, msg: {close_msg})")


def on_open(ws):
    """连接建立时的回调"""
    print("✅ WebSocket连接已建立，开始接收消息...\n")


def start_strategy_in_background(sid):
    """后台线程：启动策略"""
    time.sleep(3)  # 等待WebSocket连接稳定
    print(f"\n🚀 启动策略 {sid}...")
    try:
        response = requests.post(f"{BASE_URL}/{sid}/start")
        if response.status_code == 200:
            print(f"✅ 策略 {sid} 启动成功")
        else:
            print(f"❌ 策略 {sid} 启动失败: {response.text}")
    except Exception as e:
        print(f"❌ 启动策略时出错: {e}")


def main():
    """主测试流程"""
    print("🚀 开始测试策略WebSocket...")
    print(f"目标地址: {WS_URL}\n")
    
    # 检查服务是否可用
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print("❌ 服务未启动，请先启动 Web 服务!")
            return
    except:
        print("❌ 无法连接到服务，请确保 Web 服务正在运行!")
        return
    
    # 获取可用的策略
    try:
        response = requests.get(f"{BASE_URL}/")
        data = response.json()
        strategies = data.get("strategies", {})
        strategy_ids = list(strategies.keys())
        
        if not strategy_ids:
            print("⚠️  没有找到策略，请检查 strategies.json 配置")
            return
        
        test_sid = strategy_ids[0]
        print(f"📌 将使用策略 '{test_sid}' 进行测试\n")
        
    except Exception as e:
        print(f"❌ 获取策略列表失败: {e}")
        return
    
    # 启用WebSocket调试（可选）
    # websocket.enableTrace(True)
    
    # 创建WebSocket连接
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # 在后台线程启动策略（产生消息）
    threading.Thread(
        target=start_strategy_in_background,
        args=(test_sid,),
        daemon=True
    ).start()
    
    # 运行WebSocket（阻塞）
    print("💡 提示: 按 Ctrl+C 退出\n")
    print("="*60)
    
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断，关闭连接...")
        ws.close()
    
    print("\n" + "="*60)
    print("✨ 测试完成!")
    print("="*60)


if __name__ == "__main__":
    main()

