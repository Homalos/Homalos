#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2  
@FileName   : start_integrated_web.py
@Date       : 2025/1/20
@Author     : Homalos Team
@Description: 启动集成事件监控的Homalos量化交易系统
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from start_homalos import HomalosSystem, logger


def main():
    """
    启动集成事件监控的Homalos量化交易系统
    """
    try:
        logger.info("启动集成事件监控的Homalos量化交易系统...")
        
        # 创建系统实例
        system = HomalosSystem()
        
        # 运行系统
        asyncio.run(system.start())
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
    except Exception as e:
        logger.error(f"系统运行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 10):
        print("需要Python 3.10或更高版本")
        sys.exit(1)
    
    # 检查配置文件
    system_config_file = "config/system.yaml"
    if not Path(system_config_file).exists():
        print(f"配置文件不存在: {system_config_file}")
        print("请复制config/system.yaml.example为config/system.yaml并进行配置")
        sys.exit(1)
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║ ██╗  ██╗ ██████╗ ███╗   ███╗ █████╗ ██╗      ██████╗ ███████╗ ║
║ ██║  ██║██╔═══██╗████╗ ████║██╔══██╗██║     ██╔═══██╗██╔════╝ ║
║ ███████║██║   ██║██╔████╔██║███████║██║     ██║   ██║███████╗ ║
║ ██╔══██║██║   ██║██║╚██╔╝██║██╔══██║██║     ██║   ██║╚════██║ ║
║ ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║  ██║███████╗╚██████╔╝███████║ ║
║ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝ ║
║                  Homalos 量化交易系统 v0.0.1                  ║
║                                                               ║
║              基于 Python 的期货量化交易系统                   ║
║                    集成事件监控仪表板                         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # 运行系统
    main()