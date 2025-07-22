#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2  
@FileName   : start_homalos.py
@Date       : 2025/7/6 22:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: Homalos量化交易系统主程序
"""
import asyncio
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType
from src.function.gateway_helper import get_enabled_gateways
from src.services.trading_engine import TradingEngine

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.event_bus import EventBus
from src.core.service_registry import ServiceRegistry
from src.services.data_service import DataService
from src.web.web_server import WebServer
from src.core.logger import get_logger

# 网关导入和可用性检测
from typing import Dict, Any

# 网关类映射
GATEWAY_CLASSES: Dict[str, Dict[str, Any]] = {}

# 尝试导入CTP网关
try:
    from src.ctp.gateway.market_data_gateway import MarketDataGateway as CtpMarketDataGateway
    from src.ctp.gateway.order_trading_gateway import OrderTradingGateway as CtpOrderTradingGateway
    CTP_AVAILABLE = True
    GATEWAY_CLASSES['ctp'] = {
        'market_data': CtpMarketDataGateway,
        'order_trading': CtpOrderTradingGateway,
        'available': True
    }
except ImportError:
    CtpMarketDataGateway = None
    CtpOrderTradingGateway = None
    CTP_AVAILABLE = False
    GATEWAY_CLASSES['ctp'] = {
        'market_data': None,
        'order_trading': None,
        'available': False
    }

# 尝试导入TTS网关
try:
    from src.tts.gateway.market_data_gateway import MarketDataGateway as TtsMarketDataGateway
    from src.tts.gateway.order_trading_gateway import OrderTradingGateway as TtsOrderTradingGateway
    TTS_AVAILABLE = True
    GATEWAY_CLASSES['tts'] = {
        'market_data': TtsMarketDataGateway,
        'order_trading': TtsOrderTradingGateway,
        'available': True
    }
except ImportError:
    TtsMarketDataGateway = None
    TtsOrderTradingGateway = None
    TTS_AVAILABLE = False
    GATEWAY_CLASSES['tts'] = {
        'market_data': None,
        'order_trading': None,
        'available': False
    }


logger = get_logger("HomalosSystem")


class HomalosSystem:
    """Homalos量化交易系统主类"""
    
    def __init__(self, config_file: str = "config/system.yaml"):
        self.config_file = config_file
        
        # 核心组件
        self.config: Optional[ConfigManager] = None
        self.event_bus: Optional[EventBus] = None
        self.service_registry: Optional[ServiceRegistry] = None
        self.trading_engine: Optional[TradingEngine] = None
        self.data_service: Optional[DataService] = None
        self.web_server: Optional[WebServer] = None
        
        # 网关组件（支持多个网关）
        self.market_gateways: Dict[str, Any] = {}
        self.trading_gateways: Dict[str, Any] = {}
        
        # 向后兼容性
        self.market_gateway: Optional[Any] = None
        self.trading_gateway: Optional[Any] = None
        
        # 系统状态
        self.is_running = False
        self.start_time = None
        
        # 信号处理
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(f"接收到退出信号 {signum}，正在关闭系统...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    @staticmethod
    def _validate_gateway_config(gateway_key: str, gateway_config: Dict[str, Any], gateway_type: str) -> bool:
        """验证网关配置的完整性"""
        # 定义不同网关类型的必需字段
        required_fields_map = {
            'ctp': ["user_id", "password", "broker_id", "md_address", "td_address"],
            'tts': ["user_id", "password", "broker_id", "md_address", "td_address"]
        }
        
        required_fields = required_fields_map.get(gateway_type, [])
        missing_fields = [field for field in required_fields if not gateway_config.get(field)]
        
        if missing_fields:
            logger.error(f"{gateway_key} 网关配置不完整，缺少字段: {missing_fields}")
            return False
        
        # 验证网络地址格式
        for addr_field in ["md_address", "td_address"]:
            if addr_field in gateway_config:
                address = gateway_config.get(addr_field, "")
                if address and not any(address.startswith(prefix) for prefix in ["tcp://", "ssl://", "socks://"]):
                    gateway_config[addr_field] = "tcp://" + address
                    logger.info(f"为 {gateway_key} 的 {addr_field} 添加 tcp:// 前缀")
        
        logger.info(f"{gateway_key} 网关配置验证通过")
        return True

    @staticmethod
    def _convert_gateway_config(gateway_config: dict, gateway_type: str) -> dict:
        """根据网关类型转换配置参数格式"""
        converted_config = gateway_config.copy()
        
        if gateway_type == 'tts':
            if 'user_id' in converted_config:
                converted_config['userid'] = converted_config.pop('user_id')
            
            if 'app_id' in converted_config:
                converted_config['appid'] = converted_config.pop('app_id')
        
        return converted_config
    
    async def initialize(self) -> bool:
        """初始化系统组件"""
        try:
            logger.info("Homalos量化交易系统启动中...")
            
            # 1. 初始化配置管理器
            logger.info("初始化配置管理器...")
            self.config = ConfigManager(self.config_file)
            
            # 2. 初始化事件总线
            logger.info("初始化事件总线...")
            event_bus_config = {
                "name": self.config.get("event_bus.name", "trading_system"),
                "interval": self.config.get("event_bus.timer_interval", 1.0)
            }
            self.event_bus = EventBus(**event_bus_config)
            
            # 3. 初始化服务注册中心
            logger.info("初始化服务注册中心...")
            self.service_registry = ServiceRegistry(self.event_bus)
            
            # 4. 初始化数据服务
            logger.info("初始化数据服务...")
            self.data_service = DataService(self.event_bus, self.config)
            await self.data_service.initialize()
            
            # 5. 初始化交易引擎核心
            logger.info("初始化交易引擎核心...")
            self.trading_engine = TradingEngine(self.event_bus, self.config)
            await self.trading_engine.initialize()
            
            # 6. 初始化交易网关（如果可用）
            await self._initialize_gateways()
            
            # 7. 初始化Web管理界面
            if self.config.get("web.enabled", True):
                logger.info("初始化Web管理界面...")
                self.web_server = WebServer(self.trading_engine, self.event_bus, self.config)
            
            logger.info("系统组件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            return False
    
    async def _initialize_gateways(self) -> None:
        """初始化交易网关（支持动态选择）"""
        try:
            # 获取启用的网关
            enabled_gateways = get_enabled_gateways(self.config)
            
            if not enabled_gateways:
                logger.warning("未发现启用的网关，系统将在无网关模式下运行")
                return
            
            # 初始化每个启用的网关
            for gateway_key, gateway_info in enabled_gateways.items():
                gateway_config = gateway_info['config']
                gateway_type = gateway_info['type']
                gateway_classes = gateway_info['classes']
                
                # 验证网关配置
                if not self._validate_gateway_config(gateway_key, gateway_config, gateway_type):
                    logger.warning(f"跳过网关 {gateway_key}，配置验证失败")
                    continue
                
                # 初始化行情网关
                if gateway_classes['market_data'] and self.event_bus:
                    logger.info(f"初始化 {gateway_key} 行情网关...")
                    market_gateway_name = f"{gateway_type.upper()}_MD_{gateway_key}"
                    market_gateway = gateway_classes['market_data'](self.event_bus, market_gateway_name)
                    self.market_gateways[gateway_key] = market_gateway
                    logger.info(f"行情网关已创建: {market_gateway.gateway_name}")
                    
                    # 设置主要网关（向后兼容）
                    if not self.market_gateway:
                        self.market_gateway = market_gateway
                
                # 初始化交易网关
                if gateway_classes['order_trading'] and self.event_bus:
                    logger.info(f"初始化 {gateway_key} 交易网关...")
                    trading_gateway_name = f"{gateway_type.upper()}_TD_{gateway_key}"
                    trading_gateway = gateway_classes['order_trading'](self.event_bus, trading_gateway_name)
                    self.trading_gateways[gateway_key] = trading_gateway
                    logger.info(f"交易网关已创建: {trading_gateway.gateway_name}")
                    
                    # 设置主要网关（向后兼容）
                    if not self.trading_gateway:
                        self.trading_gateway = trading_gateway
                
                # 连接网关
                await self._connect_gateway_with_timeout(gateway_key, gateway_config, gateway_type)
            
            if self.market_gateways or self.trading_gateways:
                logger.info(f"网关初始化完成，已启用 {len(self.market_gateways)} 个行情网关和 {len(self.trading_gateways)} 个交易网关")
            
        except Exception as e:
            logger.error(f"网关初始化失败: {e}")
            # 继续运行，不因网关初始化失败而退出
            logger.warning("系统将在无网关模式下运行")
    
    async def _connect_gateway_with_timeout(self, gateway_key: str, gateway_config: dict, gateway_type: str) -> None:
        """带超时控制的单个网关连接"""
        connection_timeout = 30  # 30秒超时
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试连接 {gateway_key} 网关 (第 {attempt + 1}/{max_retries} 次)...")
                
                # 并行连接行情和交易网关
                tasks = []
                
                # 连接行情网关
                if gateway_key in self.market_gateways:
                    market_gateway = self.market_gateways[gateway_key]
                    tasks.append(self._connect_single_market_gateway(
                        market_gateway, gateway_config, connection_timeout, gateway_type
                    ))
                
                # 连接交易网关
                if gateway_key in self.trading_gateways:
                    trading_gateway = self.trading_gateways[gateway_key]
                    tasks.append(self._connect_single_trading_gateway(
                        trading_gateway, gateway_config, connection_timeout, gateway_type
                    ))
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # 检查连接结果
                    success_count = sum(1 for result in results if not isinstance(result, Exception))
                    if success_count > 0:
                        logger.info(f"{gateway_key} 网关连接完成，成功连接 {success_count}/{len(tasks)} 个组件")
                    else:
                        logger.warning(f"{gateway_key} 网关所有组件连接失败")
                    break
                    
            except asyncio.TimeoutError:
                logger.warning(f"{gateway_key} 网关连接超时 (第 {attempt + 1} 次尝试)")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)  # 重试前等待5秒
                else:
                    logger.error(f"{gateway_key} 网关连接最终失败，已达到最大重试次数")
            except Exception as e:
                logger.error(f"{gateway_key} 网关连接异常 (第 {attempt + 1} 次尝试): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    logger.error(f"{gateway_key} 网关连接最终失败")
                    break
    
    async def _connect_single_market_gateway(self, market_gateway: Any, gateway_config: dict, timeout: int, gateway_type: str) -> None:
        """连接单个行情网关"""
        try:
            gateway_name = getattr(market_gateway, 'gateway_name', 'Unknown')
            
            # 根据网关类型转换配置参数
            converted_config = self._convert_gateway_config(gateway_config, gateway_type)
            
            connection_task = asyncio.create_task(
                asyncio.to_thread(market_gateway.connect, converted_config)
            )
            await asyncio.wait_for(connection_task, timeout=timeout)
            logger.info(f"行情网关 {gateway_name} 连接成功")
        except asyncio.TimeoutError:
            gateway_name = getattr(market_gateway, 'gateway_name', 'Unknown')
            logger.error(f"行情网关 {gateway_name} 连接超时")
            raise
        except Exception as e:
            gateway_name = getattr(market_gateway, 'gateway_name', 'Unknown')
            logger.error(f"行情网关 {gateway_name} 连接失败: {e}")
            raise
    
    async def _connect_single_trading_gateway(self, trading_gateway: Any, gateway_config: dict, timeout: int, gateway_type: str) -> None:
        """连接单个交易网关"""
        try:
            gateway_name = getattr(trading_gateway, 'gateway_name', 'Unknown')
            
            # 根据网关类型转换配置参数
            converted_config = self._convert_gateway_config(gateway_config, gateway_type)
            
            connection_task = asyncio.create_task(
                asyncio.to_thread(trading_gateway.connect, converted_config)
            )
            await asyncio.wait_for(connection_task, timeout=timeout)
            logger.info(f"交易网关 {gateway_name} 连接成功")
        except asyncio.TimeoutError:
            gateway_name = getattr(trading_gateway, 'gateway_name', 'Unknown')
            logger.error(f"交易网关 {gateway_name} 连接超时")
            raise
        except Exception as e:
            gateway_name = getattr(trading_gateway, 'gateway_name', 'Unknown')
            logger.error(f"交易网关 {gateway_name} 连接失败: {e}")
            raise
    
    async def _handle_gateway_connection_failure(self) -> None:
        """处理网关连接失败的回退策略"""
        try:
            logger.warning("实施网关连接失败回退策略...")
            
            # 清理失败的网关连接
            if self.market_gateway:
                try:
                    self.market_gateway.close()
                except Exception as e:
                    logger.debug(f"清理行情网关连接时出错: {e}")
                self.market_gateway = None
                
            if self.trading_gateway:
                try:
                    self.trading_gateway.close()
                except Exception as e:
                    logger.debug(f"清理交易网关连接时出错: {e}")
                self.trading_gateway = None
            
            # 发布网关连接失败事件
            if self.event_bus:
                self.event_bus.publish(Event(EventType.SYSTEM_GATEWAY_CONNECTION_FAILED, {
                    "timestamp": time.time(),
                    "reason": "connection_timeout_or_error"
                }))
            
            logger.info("网关连接失败处理完成，系统将在模拟模式下运行")
            
        except Exception as e:
            logger.error(f"处理网关连接失败时发生错误: {e}")
    
    async def start(self) -> None:
        """启动系统（增强错误处理）"""
        if self.is_running:
            logger.warning("系统已在运行")
            return

        try:
            # 初始化系统
            logger.info("开始系统初始化...")
            if not await self.initialize():
                logger.error("系统初始化失败，退出")
                await self._graceful_shutdown_on_failure()
                return
            
            # 启动核心组件（有依赖顺序）
            startup_steps = [
                ("启动事件总线", self._start_event_bus),
                ("启动服务注册中心", self._start_service_registry),
                ("启动交易引擎", self._start_trading_engine),
                ("启动Web服务器", self._start_web_server)
            ]
            
            for step_name, step_func in startup_steps:
                try:
                    logger.info(f"{step_name}...")
                    await step_func()
                    logger.info(f"{step_name}成功")
                except Exception as e:
                    logger.error(f"{step_name}失败: {e}")
                    if step_name in ["启动事件总线", "启动交易引擎"]:  # 关键组件失败
                        raise
                    else:  # 非关键组件失败，继续启动
                        logger.warning(f"{step_name}失败，但系统将继续启动")
            
            # 标记系统运行状态
            self.is_running = True
            self.start_time = time.time()
            
            logger.info("Homalos量化交易系统启动成功!")
            logger.info(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 显示系统信息
            self._print_system_info()
            
            # 发布系统启动成功事件
            if self.event_bus:
                self.event_bus.publish(Event(EventType.SYSTEM_STARTUP_COMPLETE, {
                    "start_time": self.start_time,
                    "components": self.get_system_status()["components"]
                }))
                
                # 主循环保持系统运行
                await self._main_loop()
                
        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            await self._graceful_shutdown_on_failure()
    
    async def _start_event_bus(self) -> None:
        """启动事件总线"""
        if self.event_bus:
            self.event_bus.start()
    
    async def _start_service_registry(self) -> None:
        """启动服务注册中心"""
        if self.service_registry:
            self.service_registry.start()
    
    async def _start_trading_engine(self) -> None:
        """启动交易引擎"""
        if self.trading_engine:
            await self.trading_engine.start()

    @staticmethod
    def _close_gateways(gateways: Dict[str, Any], gateway_type_name: str):
        """
        通用的关闭网关函数(行情网关和交易网关)
        :param gateways: 网关字典 {key: gateway}
        :param gateway_type_name: 网关类型名称（用于日志）
        """
        if not gateways:
            return

        logger.info(f"关闭 {len(gateways)} 个{gateway_type_name}...")
        for gateway_key, gateway in gateways.items():
            try:
                logger.info(f"关闭{gateway_type_name}: {gateway_key}")
                gateway.close()
            except Exception as e:
                logger.error(f"关闭{gateway_type_name} {gateway_key} 时发生错误: {e}", exc_info=True)


    async def _start_web_server(self) -> None:
        """启动Web服务器"""
        if self.web_server:
            # 在后台运行Web服务器
            self._web_task = asyncio.create_task(self._run_web_server())
    
    async def _graceful_shutdown_on_failure(self) -> None:
        """启动失败时的优雅关闭"""
        logger.info("启动失败，执行优雅关闭...")
        try:
            await self.shutdown()
        except Exception as e:
            logger.error(f"优雅关闭失败: {e}")
        finally:
            self.is_running = False
    
    async def _run_web_server(self):
        """运行Web服务器"""
        try:
            await self.web_server.start()
        except Exception as e:
            logger.error(f"Web服务器运行失败: {e}")
    
    async def _main_loop(self):
        """主循环"""
        try:
            while self.is_running:
                # 定期检查系统状态
                await asyncio.sleep(1)
                
                # 检查配置文件变更
                if self.config.reload():
                    logger.info("配置文件已重新加载")
                
                # 这里可以添加其他定期任务
                
        except KeyboardInterrupt:
            logger.info("接收到中断信号")
        except Exception as e:
            logger.error(f"主循环异常: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """关闭系统"""
        if not self.is_running:
            return
        
        logger.info("正在关闭Homalos量化交易系统...")
        
        try:
            # 停止交易引擎
            if self.trading_engine:
                logger.info("停止交易引擎...")
                await self.trading_engine.stop()
            
            # 关闭数据服务
            if self.data_service:
                logger.info("关闭数据服务...")
                await self.data_service.shutdown()

            # 关闭所有行情网关
            self._close_gateways(self.market_gateways, "行情网关")

            # 关闭所有交易网关
            self._close_gateways(self.trading_gateways, "交易网关")

            # 停止服务注册中心
            if self.service_registry:
                logger.info("停止服务注册中心...")
                self.service_registry.stop()
            
            # 停止事件总线
            if self.event_bus:
                logger.info("停止事件总线...")
                self.event_bus.stop()
            
            self.is_running = False
            
            # 计算运行时间
            if self.start_time:
                runtime = time.time() - self.start_time
                logger.info(f"系统运行时长: {runtime:.2f} 秒")
            
            logger.info("Homalos量化交易系统已安全关闭")
            
        except Exception as e:
            logger.error(f"系统关闭过程中发生错误: {e}", exc_info=True)
    
    def _print_system_info(self):
        """打印系统信息"""
        info = f"""
{'='*60}
🎯 Homalos量化交易系统 v2.0
📁 配置文件: {self.config_file}
🌐 Web界面: {'启用' if self.web_server else '禁用'}
🔌 CTP网关: {'可用' if CTP_AVAILABLE else '不可用'}
⚙️ 事件总线: {self.event_bus.name}
💾 数据库: {self.config.get('database.path', 'N/A')}
🎛️ 风控系统: {'启用' if self.config.get('risk.enabled', True) else '禁用'}
"""
        
        if self.web_server:
            host = self.config.get("web.host", "127.0.0.1")
            port = self.config.get("web.port", 8000)
            info += "Web地址: http:" + f"//{host}:{port}\n"
        
        info += "="*60
        logger.info(info)
    
    def get_system_status(self) -> dict:
        """获取系统状态"""
        return {
            "is_running": self.is_running,
            "start_time": self.start_time,
            "config_file": self.config_file,
            "web_enabled": self.web_server is not None,
            "ctp_available": CTP_AVAILABLE,
            "components": {
                "event_bus": self.event_bus is not None,
                "trading_engine": self.trading_engine is not None,
                "data_service": self.data_service is not None,
                "web_server": self.web_server is not None,
                "market_gateway": self.market_gateway is not None,
                "trading_gateway": self.trading_gateway is not None
            }
        }


async def main():
    """主函数"""
    try:
        # 创建系统实例
        system = HomalosSystem()
        
        # 启动系统
        await system.start()
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
    except Exception as e:
        logger.error(f"系统运行异常: {e}")
        sys.exit(1)


def run_system():
    """运行系统（同步入口）"""
    try:
        # 运行异步主函数
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("系统已停止")
    except Exception as e:
        logger.error(f"系统异常: {e}")
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
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    Homalos 量化交易系统 v0.0.1                               ║
║                                                              ║
║    基于 Python 的期货量化交易系统                            ║
║                                                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 运行系统
    run_system()

