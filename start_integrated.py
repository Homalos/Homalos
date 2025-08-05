#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2  
@FileName   : start_integrated.py
@Date       : 2025/8/5
@Author     : Homalos Team
@Description: Homalos量化交易系统统一入口脚本 - 支持多种运行模式
"""

import argparse
import asyncio
import sys
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any

from colorama import Fore, Style, init

# 初始化colorama
init(autoreset=True)

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import get_logger

logger = get_logger("HomalosLauncher")


class HomalosLauncher:
    """Homalos系统启动器"""
    
    def __init__(self):
        self.system = None
        self.start_time = None
        self.shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(f"接收到退出信号 {signum}，正在关闭系统...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def print_banner(self, mode: str = "完整系统"):
        """打印系统横幅"""
        print(Fore.CYAN + f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║ ██╗  ██╗ ██████╗ ███╗   ███╗ █████╗ ██╗      ██████╗ ███████╗ ║
║ ██║  ██║██╔═══██╗████╗ ████║██╔══██╗██║     ██╔═══██╗██╔════╝ ║
║ ███████║██║   ██║██╔████╔██║███████║██║     ██║   ██║███████╗ ║
║ ██╔══██║██║   ██║██║╚██╔╝██║██╔══██║██║     ██║   ██║╚════██║ ║
║ ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║  ██║███████╗╚██████╔╝███████║ ║
║ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝ ║
║                                                               ║
║               Homalos 期货量化交易系统 v2.0.0                 ║
║                                                               ║
║               基于 Python 的期货量化交易系统                  ║
║                                                               ║
║               运行模式: {mode:<20}         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
        """ + Style.RESET_ALL)
    
    @staticmethod
    def validate_python_version():
        """验证Python版本"""
        if sys.version_info < (3, 10):
            logger.error("需要Python 3.10或更高版本")
            print(f"{Fore.RED}❌ 需要Python 3.10或更高版本，当前版本: {sys.version}")
            sys.exit(1)
        logger.info(f"Python版本检查通过: {sys.version}")
    
    @staticmethod
    def validate_config_files():
        """验证配置文件"""
        config_files = {
            "config/system.yaml": "config/system.yaml.example",
            "config/brokers.json": "config/brokers.json.example"
        }
        
        missing_configs = []
        for config_file, example_file in config_files.items():
            if not Path(config_file).exists():
                missing_configs.append((config_file, example_file))
        
        if missing_configs:
            logger.error("配置文件缺失")
            print(f"{Fore.RED}❌ 以下配置文件缺失:")
            for config_file, example_file in missing_configs:
                print(f"   {config_file} (请复制 {example_file})")
            sys.exit(1)
        
        logger.info("配置文件检查通过")
    
    async def start_trading_system(self, config_file: str = "config/system.yaml", 
                                   web_enabled: bool = True):
        """启动完整交易系统"""
        try:
            # 直接使用 start_homalos.py 中的 HomalosSystem
            from start_homalos import HomalosSystem
            
            mode = "完整交易系统 (含Web界面)" if web_enabled else "完整交易系统 (无Web界面)"
            logger.info(f"启动{mode}...")
            self.print_banner(mode)
            
            system = HomalosSystem(config_file)
            self.system = system
            self.start_time = time.time()
            
            # 如果不需要Web界面，禁用Web组件
            if not web_enabled and system.config:
                system.config.set("web.enabled", False)
            
            # 启动系统
            await system.start()
            
        except Exception as e:
            logger.error(f"交易系统启动失败: {e}")
            raise
    
    async def start_web_only(self, config_file: str = "config/system.yaml"):
        """启动Web界面模式 (连接到现有系统)"""
        try:
            from src.web.integrated_web_server import IntegratedWebServer
            from src.config.config_manager import ConfigManager
            from src.core.event_bus import EventBus
            from src.core.event_monitor import EventMonitor
            
            logger.info("启动Web界面模式...")
            self.print_banner("Web界面")
            
            # 创建基本组件用于Web界面
            config = ConfigManager(config_file)
            event_bus = EventBus()
            event_monitor = EventMonitor(name="WebInterface")
            
            # 创建Web服务器（不需要完整的交易引擎）
            web_server = IntegratedWebServer(
                trading_engine=None,  # Web界面可以独立运行
                event_bus=event_bus,
                config=config,
                event_monitor=event_monitor
            )
            
            self.system = web_server
            self.start_time = time.time()
            
            # 启动Web服务器
            await web_server.start()
            
            # 等待关闭信号
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Web服务器启动失败: {e}")
            raise
    
    async def shutdown(self):
        """关闭系统"""
        if not self.system:
            return
        
        logger.info("正在关闭系统...")
        try:
            if hasattr(self.system, 'shutdown'):
                await self.system.shutdown()
            elif hasattr(self.system, 'stop'):
                await self.system.stop()
            
            # 计算运行时间
            if self.start_time:
                runtime = time.time() - self.start_time
                logger.info(f"系统运行时长: {runtime:.2f} 秒")
            
            logger.info("系统已安全关闭")
            
        except Exception as e:
            logger.error(f"系统关闭过程中发生错误: {e}")
    
    async def run(self, mode: str, config_file: str = "config/system.yaml", 
                  web_enabled: bool = True):
        """运行系统"""
        try:
            # 验证环境
            self.validate_python_version()
            self.validate_config_files()
            
            # 根据模式启动对应组件
            if mode == "trading":
                await self.start_trading_system(config_file, web_enabled)
            elif mode == "web":
                await self.start_web_only(config_file)
            else:
                raise ValueError(f"不支持的运行模式: {mode}")
        
        except KeyboardInterrupt:
            logger.info("收到中断信号")
        except Exception as e:
            logger.error(f"系统运行异常: {e}")
            raise
        finally:
            await self.shutdown()


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Homalos量化交易系统统一启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行模式说明:
  trading  - 启动完整交易系统 (默认包含Web界面)
  web      - 仅启动Web界面 (连接到现有系统)

注意: 数据中心请使用独立脚本 start_data_center.py 启动

示例:
  python start_integrated.py                    # 启动完整交易系统
  python start_integrated.py --mode trading --no-web  # 启动交易系统但不启动Web界面
  python start_integrated.py --mode web         # 仅启动Web界面
  python start_integrated.py --config config/custom.yaml  # 使用自定义配置文件
        """
    )
    
    parser.add_argument(
        "--mode", "-m",
        choices=["trading", "web"],
        default="trading",
        help="运行模式 (默认: trading)"
    )
    
    parser.add_argument(
        "--config", "-c",
        default="config/system.yaml",
        help="配置文件路径 (默认: config/system.yaml)"
    )
    
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="禁用Web界面 (仅在trading模式下有效)"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Homalos v2.0.0"
    )
    
    return parser.parse_args()


async def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 创建启动器
        launcher = HomalosLauncher()
        
        # 运行系统
        await launcher.run(
            mode=args.mode,
            config_file=args.config,
            web_enabled=not args.no_web
        )
        
    except Exception as e:
        logger.error(f"系统启动失败: {e}")
        sys.exit(1)


def run_system():
    """同步入口函数"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}系统已停止")
    except Exception as e:
        print(f"{Fore.RED}系统异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_system()