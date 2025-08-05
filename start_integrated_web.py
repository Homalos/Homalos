#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2  
@FileName   : start_integrated_web.py
@Date       : 2025/1/20
@Author     : Homalos Team
@Description: Homalos量化交易系统 - 完整系统启动入口（兼容性保持）
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from start_integrated import run_system
from colorama import Fore, Style

def main():
    """
    启动完整交易系统（含Web界面）- 兼容性入口
    """
    print(f"{Fore.YELLOW}注意: start_integrated_web.py 已迁移到 start_integrated.py")
    print(f"建议使用: python start_integrated.py --mode trading{Style.RESET_ALL}")
    print()
    
    # 设置系统参数模拟 --mode trading
    sys.argv = ["start_integrated.py", "--mode", "trading"]
    
    # 调用统一入口
    run_system()

if __name__ == "__main__":
    main()