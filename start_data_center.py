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
import types
from pathlib import Path
from typing import Optional

from src.config.config_manager import ConfigManager
from src.data_center.data_center import DataCenter
from src.function.gateway_helper import get_enabled_gateways

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.core.event_bus import EventBus

logger = get_logger("DataCenterApplication")


class DataCenterApplication:
    """数据中心应用程序"""
    
    def __init__(self,
                 gateway_config_file: str = "config/system.yaml",
                 data_center_config_file = "config/data_center_config.yaml"):
        self.gateway_config_file = gateway_config_file
        self.data_center_config_file = data_center_config_file
        self.gateway_config: Optional[ConfigManager] = None
        self.config = None
        self.event_bus = None
        self.data_center = None
        self.running = False
        
    async def initialize(self):
        """初始化数据中心应用"""
        try:
            # 加载系统配置
            self.gateway_config = ConfigManager(self.gateway_config_file)

            # 获取启用的网关
            enabled_gateways = get_enabled_gateways(self.gateway_config)

            if not enabled_gateways:
                raise ValueError("没有启用的网关配置")

            # 获取第一个启用的网关
            gateway_key = list(enabled_gateways.keys())[0]
            gateway_info = enabled_gateways[gateway_key]
            
            enabled_gateway_config = gateway_info['config']
            enabled_gateway_type = gateway_info['type']

            logger.info(f"使用网关: {gateway_key} (类型: {enabled_gateway_type})")

            config_path = project_root / "config" / "data_center_config.yaml"
            logger.info(f"加载数据中心配置文件: {config_path}")
            
            if not config_path.exists():
                raise FileNotFoundError(f"数据中心配置文件不存在: {config_path}")
            
            config_manager = ConfigManager(str(config_path))
            self.config = config_manager.get_all()
            
            if self.config is None:
                raise ValueError("数据中心配置加载失败，配置为空")
            
            logger.info(f"数据中心配置加载成功，包含段: {list(self.config.keys())}")
            
            # 添加网关连接配置到数据中心配置中
            gateway_config = {
                'user_id': enabled_gateway_config.get('user_id'),
                'password': enabled_gateway_config.get('password'),
                'broker_id': enabled_gateway_config.get('broker_id'),
                'md_address': enabled_gateway_config.get('md_address'),
                'td_address': enabled_gateway_config.get('td_address'),
                'appid': enabled_gateway_config.get('app_id'),
                'auth_code': enabled_gateway_config.get('auth_code'),
            }
            self.config['gateway'] = gateway_config

            # 创建事件总线
            self.event_bus = EventBus()
            
            # 创建数据中心（数据中心将独立管理网关连接）
            logger.info("开始创建数据中心实例...")
            try:
                self.data_center = DataCenter(self.event_bus, self.config)
                logger.info("数据中心实例创建成功")
            except Exception as dc_error:
                logger.error(f"创建数据中心实例失败: {dc_error}")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")
                raise
            
            return True
            
        except Exception as e:
            logger.error(f"数据中心应用初始化失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    async def start(self):
        """启动数据中心应用"""
        global shutdown_requested
        try:
            if not await self.initialize():
                return False
            
            # 启动数据中心（数据中心内部会自动创建和连接网关）
            self.data_center.start()
            logger.info("数据中心应用初始化成功")
            
            # 网关已在数据中心中自动连接
            self.running = True
            logger.info("数据中心应用启动成功，开始7x24小时运行...")
            
            # 主循环
            while self.running and not shutdown_requested:
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
# 全局关闭标志
shutdown_requested = False

def signal_handler(signum, frame: Optional[types.FrameType]) -> None:
    """信号处理器"""
    global shutdown_requested
    logger.info(f"接收到信号 {signum}，开始关闭数据中心...")
    shutdown_requested = True

    if not hasattr(app, 'running'):
        logger.warning("应用实例未初始化")
        sys.exit(1)

    # 设置应用停止标志
    app.running = False
    
    # 立即停止数据中心组件
    try:
        if app.data_center:
            app.data_center.stop()
        if app.event_bus:
            app.event_bus.stop()
        logger.info("数据中心组件已停止")
    except AttributeError as e:
        logger.error(f"组件未初始化: {e}")
    except Exception as e:
        logger.error(f"停止数据中心组件失败: {e}")
    
    # 强制退出
    logger.info("进程退出")
    sys.exit(0)

async def main():
    """主函数"""
    global shutdown_requested
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动数据中心应用
        await app.start()
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，开始关闭数据中心...")
        shutdown_requested = True
    except Exception as e:
        logger.error(f"数据中心运行异常: {e}")
        shutdown_requested = True
    finally:
        if not shutdown_requested:
            logger.info("正常关闭数据中心...")
            await app.shutdown()
        else:
            logger.info("收到关闭信号，快速关闭数据中心...")
            # 快速关闭，不等待异步操作
            try:
                if app.data_center:
                    app.data_center.stop()
                if app.event_bus:
                    app.event_bus.stop()
            except Exception as e:
                logger.error(f"快速关闭失败: {e}")
            logger.info("数据中心已关闭")

if __name__ == "__main__":
    # 设置事件循环策略（Windows）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 运行数据中心
    asyncio.run(main())