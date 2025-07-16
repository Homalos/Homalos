#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : start_data_center
@Date       : 2025/1/20
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据中心独立启动脚本
"""

import asyncio
import signal
import sys
from pathlib import Path

from src.config.config_manager import ConfigManager

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.core.event_bus import EventBus
from src.services.data_center import DataCenter

logger = get_logger("DataCenterApplication")

class DataCenterApplication:
    """数据中心应用程序"""
    
    def __init__(self):
        self.config = None
        self.event_bus = None
        self.data_center = None
        self.running = False
        
    async def initialize(self):
        """初始化数据中心应用"""
        try:
            # 加载配置
            config_path = project_root / "config" / "data_center_config.yaml"
            config_manager = ConfigManager(str(config_path))
            self.config = config_manager.get_all()
            
            # 添加网关连接配置到数据中心配置中
            gateway_config = {
                'user_id': '160219',
                'password': 'donny@103010',
                'broker_id': '9999',
                'md_address': 'tcp://182.254.243.31:40011',
                'appid': 'simnow_client_test',
                'auth_code': '0000000000000000'
            }
            self.config['gateway'] = gateway_config

            # 创建事件总线
            self.event_bus = EventBus()
            
            # 创建数据中心（数据中心将独立管理网关连接）
            self.data_center = DataCenter(self.event_bus, self.config)
            
            # 启动数据中心（数据中心内部会自动创建和连接网关）
            self.data_center.start()

            logger.info("数据中心应用初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"数据中心应用初始化失败: {e}")
            return False
    
    async def start(self):
        """启动数据中心应用"""
        try:
            if not await self.initialize():
                return False
            
            # 数据中心已在initialize中启动，无需重复启动
            
            # 网关已在数据中心中自动连接
            
            self.running = True
            logger.info("数据中心应用启动成功，开始7x24小时运行...")
            
            # 主循环
            while self.running:
                await asyncio.sleep(1)
                
                # 检查组件状态
                if not self.data_center.is_connected:
                    logger.warning("数据中心连接断开，等待自动重连...")
                    
        except Exception as e:
            logger.error(f"数据中心应用运行失败: {e}")
            return False
    
    async def shutdown(self):
        """关闭数据中心应用"""
        try:
            self.running = False
                
            if self.data_center:
                self.data_center.stop()
                
            if self.event_bus:
                self.event_bus.stop()
                
            logger.info("数据中心应用已关闭")
            
        except Exception as e:
            logger.error(f"数据中心应用关闭失败: {e}")

# 全局应用实例
app = DataCenterApplication()

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"接收到信号 {signum}，开始关闭数据中心...")
    asyncio.create_task(app.shutdown())

async def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，开始关闭数据中心...")
    except Exception as e:
        logger.error(f"数据中心运行异常: {e}")
    finally:
        await app.shutdown()

if __name__ == "__main__":
    # 设置事件循环策略（Windows）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 运行数据中心
    asyncio.run(main())