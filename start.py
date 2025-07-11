#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : main
@Date       : 2025/7/6 22:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: Homalos量化交易系统主程序 - MVP架构启动
"""
import asyncio
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Optional, Any, Type, Union

from src.config.config_manager import ConfigManager
from src.core.event import Event
from src.services.trading_engine import TradingEngine

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.event_bus import EventBus
from src.core.service_registry import ServiceRegistry
from src.services.data_service import DataService
from src.web.web_server import WebServer
from src.core.logger import get_logger

# 尝试导入CTP网关（如果可用）
try:
    from src.ctp.gateway.market_data_gateway import MarketDataGateway
    from src.ctp.gateway.order_trading_gateway import OrderTradingGateway
    CTP_AVAILABLE = True
    MarketDataGatewayType: Type[MarketDataGateway] = MarketDataGateway
    OrderTradingGatewayType: Type[OrderTradingGateway] = OrderTradingGateway
except ImportError:
    CTP_AVAILABLE = False
    MarketDataGateway = None  # type: ignore
    OrderTradingGateway = None  # type: ignore
    MarketDataGatewayType = None  # type: ignore
    OrderTradingGatewayType = None  # type: ignore

logger = get_logger("Main")


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
        
        # 网关组件
        self.market_gateway: Optional[Union[MarketDataGateway, Any]] = None
        self.trading_gateway: Optional[Union[OrderTradingGateway, Any]] = None
        
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
    
    async def initialize(self) -> bool:
        """初始化系统组件"""
        try:
            logger.info("🚀 Homalos量化交易系统启动中...")
            
            # 1. 初始化配置管理器
            logger.info("📋 初始化配置管理器...")
            self.config = ConfigManager(self.config_file)
            
            # 2. 初始化事件总线
            logger.info("🔄 初始化事件总线...")
            event_bus_config = {
                "name": self.config.get("event_bus.name", "trading_system"),
                "interval": self.config.get("event_bus.timer_interval", 1.0)
            }
            self.event_bus = EventBus(**event_bus_config)
            
            # 3. 初始化服务注册中心
            logger.info("📝 初始化服务注册中心...")
            self.service_registry = ServiceRegistry(self.event_bus)
            
            # 4. 初始化数据服务
            logger.info("💾 初始化数据服务...")
            self.data_service = DataService(self.event_bus, self.config)
            await self.data_service.initialize()
            
            # 5. 初始化交易引擎核心
            logger.info("⚙️ 初始化交易引擎核心...")
            self.trading_engine = TradingEngine(self.event_bus, self.config)
            await self.trading_engine.initialize()
            
            # 6. 初始化交易网关（如果可用）
            await self._initialize_gateways()
            
            # 7. 初始化Web管理界面
            if self.config.get("web.enabled", True):
                logger.info("🌐 初始化Web管理界面...")
                self.web_server = WebServer(self.trading_engine, self.event_bus, self.config)
            
            logger.info("✅ 系统组件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 系统初始化失败: {e}")
            return False
    
    async def _initialize_gateways(self) -> None:
        """初始化交易网关"""
        try:
            if not CTP_AVAILABLE:
                logger.warning("⚠️ CTP网关不可用，跳过网关初始化")
                return
            
            # CTP网关配置验证
            if self.config:
                ctp_config = self.config.get("gateway.ctp", {})
                
                # 详细配置验证
                required_fields = ["user_id", "password", "broker_id", "md_address", "td_address"]
                missing_fields = [field for field in required_fields if not ctp_config.get(field)]
                
                if missing_fields:
                    logger.error(f"❌ CTP网关配置不完整，缺少字段: {missing_fields}")
                    logger.warning("⚠️ 系统将在无网关模式下运行")
                    return
                
                # 验证网络地址格式
                for addr_field in ["md_address", "td_address"]:
                    address = ctp_config.get(addr_field, "")
                    if not address or not any(address.startswith(prefix) for prefix in ["tcp://", "ssl://", "socks://"]):
                        if not address.startswith("tcp://"):
                            ctp_config[addr_field] = "tcp://" + address
                
                logger.info("✅ CTP网关配置验证通过")
                
                # 初始化行情网关
                logger.info("📊 初始化CTP行情网关...")
                if self.event_bus and MarketDataGateway:
                    self.market_gateway = MarketDataGateway(self.event_bus, "CTP_MD")
                    logger.info(f"行情网关已创建: {self.market_gateway.name}")
                
                # 初始化交易网关
                logger.info("💰 初始化CTP交易网关...")
                if self.event_bus and OrderTradingGateway:
                    self.trading_gateway = OrderTradingGateway(self.event_bus, "CTP_TD")
                    logger.info(f"交易网关已创建: {self.trading_gateway.name}")
            
                # 连接网关（带超时控制）
                await self._connect_gateways_with_timeout(ctp_config)
            
        except Exception as e:
            logger.error(f"❌ 网关初始化失败: {e}")
            # 继续运行，不因网关初始化失败而退出
            logger.warning("⚠️ 系统将在无网关模式下运行")
    
    async def _connect_gateways_with_timeout(self, ctp_config: dict) -> None:
        """带超时控制的网关连接"""
        connection_timeout = 30  # 30秒连接超时
        max_retries = 3
        
        try:
            # 连接行情网关
            if self.market_gateway:
                logger.info("🔗 连接行情网关...")
                
                for attempt in range(max_retries):
                    try:
                        # 使用超时控制连接
                        connection_task = asyncio.create_task(
                            self._connect_market_gateway(ctp_config)
                        )
                        await asyncio.wait_for(connection_task, timeout=connection_timeout)
                        
                        logger.info("✅ 行情网关连接成功")
                        break
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ 行情网关连接超时 (尝试 {attempt + 1}/{max_retries})")
                        if attempt == max_retries - 1:
                            logger.error("❌ 行情网关连接失败，已达最大重试次数")
                    except Exception as e:
                        logger.warning(f"⚠️ 行情网关连接异常: {e} (尝试 {attempt + 1}/{max_retries})")
                        if attempt == max_retries - 1:
                            logger.error("❌ 行情网关连接失败")
                    
                    # 重试前等待
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
            
            # 连接交易网关  
            if self.trading_gateway:
                logger.info("🔗 连接交易网关...")
                
                for attempt in range(max_retries):
                    try:
                        # 使用超时控制连接
                        connection_task = asyncio.create_task(
                            self._connect_trading_gateway(ctp_config)
                        )
                        await asyncio.wait_for(connection_task, timeout=connection_timeout)
                        
                        logger.info("✅ 交易网关连接成功")
                        break
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ 交易网关连接超时 (尝试 {attempt + 1}/{max_retries})")
                        if attempt == max_retries - 1:
                            logger.error("❌ 交易网关连接失败，已达最大重试次数")
                    except Exception as e:
                        logger.warning(f"⚠️ 交易网关连接异常: {e} (尝试 {attempt + 1}/{max_retries})")
                        if attempt == max_retries - 1:
                            logger.error("❌ 交易网关连接失败")
                    
                    # 重试前等待
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
            
            logger.info("✅ 网关连接流程完成")
            
        except Exception as e:
            logger.error(f"❌ 网关连接过程中发生严重错误: {e}")
            # 实施回退策略
            await self._handle_gateway_connection_failure()
    
    async def _connect_market_gateway(self, ctp_config: dict) -> None:
        """连接行情网关"""
        if self.market_gateway:
            self.market_gateway.connect(ctp_config)
            # 等待连接建立（可以根据实际API调整）
            await asyncio.sleep(3)
    
    async def _connect_trading_gateway(self, ctp_config: dict) -> None:
        """连接交易网关"""
        if self.trading_gateway:
            self.trading_gateway.connect(ctp_config)
            # 等待连接建立（可以根据实际API调整）
            await asyncio.sleep(3)
    
    async def _handle_gateway_connection_failure(self) -> None:
        """处理网关连接失败的回退策略"""
        try:
            logger.warning("🔄 实施网关连接失败回退策略...")
            
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
                self.event_bus.publish(Event("system.gateway_connection_failed", {
                    "timestamp": time.time(),
                    "reason": "connection_timeout_or_error"
                }))
            
            logger.info("📝 网关连接失败处理完成，系统将在模拟模式下运行")
            
        except Exception as e:
            logger.error(f"❌ 处理网关连接失败时发生错误: {e}")
    
    async def start(self) -> None:
        """启动系统（增强错误处理）"""
        if self.is_running:
            logger.warning("系统已在运行")
            return
        
        startup_tasks = []
        
        try:
            # 初始化系统
            logger.info("📋 开始系统初始化...")
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
                    logger.info(f"🚀 {step_name}...")
                    await step_func()
                    logger.info(f"✅ {step_name}成功")
                except Exception as e:
                    logger.error(f"❌ {step_name}失败: {e}")
                    if step_name in ["启动事件总线", "启动交易引擎"]:  # 关键组件失败
                        raise
                    else:  # 非关键组件失败，继续启动
                        logger.warning(f"⚠️ {step_name}失败，但系统将继续启动")
            
            # 标记系统运行状态
            self.is_running = True
            self.start_time = time.time()
            
            logger.info("🎉 Homalos量化交易系统启动成功!")
            logger.info(f"⏰ 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 显示系统信息
            self._print_system_info()
            
            # 发布系统启动成功事件
            if self.event_bus:
                self.event_bus.publish(Event("system.startup_complete", {
                    "start_time": self.start_time,
                    "components": self.get_system_status()["components"]
                }))
            
            # 主循环保持系统运行
            await self._main_loop()
                
        except Exception as e:
            logger.error(f"❌ 系统启动失败: {e}")
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
    
    async def _start_web_server(self) -> None:
        """启动Web服务器"""
        if self.web_server:
            # 在后台运行Web服务器
            self._web_task = asyncio.create_task(self._run_web_server())
    
    async def _graceful_shutdown_on_failure(self) -> None:
        """启动失败时的优雅关闭"""
        logger.info("🛑 启动失败，执行优雅关闭...")
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
        
        logger.info("🛑 正在关闭Homalos量化交易系统...")
        
        try:
            # 停止交易引擎
            if self.trading_engine:
                logger.info("🛑 停止交易引擎...")
                await self.trading_engine.stop()
            
            # 关闭数据服务
            if self.data_service:
                logger.info("🛑 关闭数据服务...")
                await self.data_service.shutdown()
            
            # 断开网关连接
            if self.market_gateway:
                logger.info("🛑 断开行情网关...")
                # market_gateway.disconnect()  # 根据实际API调用
            
            if self.trading_gateway:
                logger.info("🛑 断开交易网关...")
                # trading_gateway.disconnect()  # 根据实际API调用
            
            # 停止服务注册中心
            if self.service_registry:
                logger.info("🛑 停止服务注册中心...")
                self.service_registry.stop()
            
            # 停止事件总线
            if self.event_bus:
                logger.info("🛑 停止事件总线...")
                self.event_bus.stop()
            
            self.is_running = False
            
            # 计算运行时间
            if self.start_time:
                runtime = time.time() - self.start_time
                logger.info(f"⏱️ 系统运行时长: {runtime:.2f} 秒")
            
            logger.info("✅ Homalos量化交易系统已安全关闭")
            
        except Exception as e:
            logger.error(f"❌ 系统关闭过程中发生错误: {e}")
    
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
            host = self.config.get("web.host", "0.0.0.0")
            port = self.config.get("web.port", 8000)
            info += f"🌐 Web地址: http://{host}:{port}\n"
        
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
        print("❌ 需要Python 3.10或更高版本")
        sys.exit(1)
    
    # 检查配置文件
    system_config_file = "config/system.yaml"
    if not Path(system_config_file).exists():
        print(f"❌ 配置文件不存在: {system_config_file}")
        print("请复制config/system.yaml.example为config/system.yaml并进行配置")
        sys.exit(1)
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    🚀 Homalos 量化交易系统 v2.0                              ║
║                                                              ║
║    基于Python的期货量化交易系统                              ║
║    MVP架构 - 模块化单体部署                                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 运行系统
    run_system()

