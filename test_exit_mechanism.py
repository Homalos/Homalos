#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据中心退出机制
"""

import os
import signal
import time
import subprocess
import sys
from pathlib import Path

def test_exit_mechanism():
    """测试数据中心的退出机制"""
    print("开始测试数据中心退出机制...")
    
    # 启动数据中心进程
    print("启动数据中心进程...")
    process = subprocess.Popen(
        [sys.executable, "-m", "start_data_center"],
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    try:
        # 等待进程启动
        print("等待数据中心启动...")
        time.sleep(10)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            print("数据中心进程正在运行，PID:", process.pid)
            
            # 在Windows上使用Ctrl+C事件
            print("发送Ctrl+C信号...")
            if sys.platform == "win32":
                # Windows上使用Ctrl+C事件
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.GenerateConsoleCtrlEvent(0, process.pid)  # CTRL_C_EVENT = 0
            else:
                # Unix系统使用SIGINT
                process.send_signal(signal.SIGINT)
            
            # 等待进程退出
            print("等待进程退出...")
            try:
                # 等待最多15秒
                return_code = process.wait(timeout=15)
                print(f"进程已退出，返回码: {return_code}")
                
                if return_code == 0:
                    print("✅ 退出机制测试成功：进程正常退出")
                else:
                    print(f"⚠️ 进程退出但返回码非零: {return_code}")
                    
            except subprocess.TimeoutExpired:
                print("❌ 退出机制测试失败：进程在15秒内未退出")
                # 强制终止进程
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
                print("已强制终止进程")
                
        else:
            print(f"❌ 数据中心进程启动失败，返回码: {process.poll()}")
            
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        if process.poll() is None:
            process.terminate()
            
    finally:
        # 确保进程被清理
        if process.poll() is None:
            process.terminate()
            time.sleep(2)
            if process.poll() is None:
                process.kill()

if __name__ == "__main__":
    test_exit_mechanism()