#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : data_center
@Date       : 2025/7/23 00:02
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description:
数据中心核心模块
负责独立运行的数据中心服务，提供全市场行情订阅、数据持久化、K线合成等功能
"""
import threading
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Set, Any

from src.config.constant import Exchange
from src.config.setting import get_instrument_exchange_id, get_exchange
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.logger import Logger
from src.core.object import TickData, BarData, ContractData
from src.ctp.gateway.order_trading_gateway import OrderTradingGateway
from src.ctp.gateway.market_data_gateway import MarketDataGateway
from src.data_center.data_center_bar_generator import DataCenterBarGenerator
from src.data_center.data_center_database import DataCenterDatabase
from src.function.data_mapping import EXCHANGE_MAPPING


class DataCenter:
    """
    数据中心核心类
    负责全市场行情订阅、数据持久化、K线合成、历史查询等功能
    """

    def __init__(self, event_bus: EventBus, config: dict[str, Any]):
        """
        初始化数据中心

        Args:
            config: 配置字典
            event_bus: 事件总线
        """
        self.config = config
        self.event_bus = event_bus

        # 提取配置段
        self.data_center_config = config.get('data_center', {})
        self.market_config = config.get('market', {})
        self.database_config = self.data_center_config.get('database', {})
        self.bar_config = self.data_center_config.get('bar_generation', {})

        log_config_dict = self.data_center_config.get('log', {})

        data_logger = Logger(log_config_dict)
        self.logger = data_logger.get_gateway_logger(gateway_name=__name__)

        # 运行状态
        self.is_running = False
        self.is_connected = False

        # 数据库管理器 - 传递完整配置，让DataCenterDatabase自己提取database段
        database_full_config = {
            'database': self.database_config
        }
        self.database = DataCenterDatabase(database_full_config)

        # K线合成器
        interval_strings = self.bar_config.get('intervals', ["1m", "5m", "15m", "30m", "1h"])
        intervals = self._convert_intervals_to_minutes(interval_strings)
        self.bar_generator = DataCenterBarGenerator(
            intervals=intervals,
            on_bar=self._on_bar_generated
        )

        # 网关
        self.market_gateway: Optional[MarketDataGateway] = None
        self.trading_gateway: Optional[OrderTradingGateway] = None

        # 订阅管理
        self.subscribed_symbols: Set[str] = set()
        self.all_contracts: Dict[str, ContractData] = {}

        # 全市场合约列表
        self.logger.info("开始加载市场合约列表...")
        self.market_symbols = self._load_market_symbols()
        self.logger.info("市场合约列表加载完成")

        # 统计信息
        self.stats = {
            'tick_count': 0,
            'bar_count': 0,
            'start_time': datetime.now(),
            'last_tick_time': datetime.now(),
            'subscribed_count': 0,
            'database_status': 'disconnected'
        }

        # 监控线程
        self.monitor_thread: Optional[threading.Thread] = None
        self.health_check_thread: Optional[threading.Thread] = None

        # 注册事件处理器
        self.logger.info("开始注册事件处理器...")
        self._register_event_handlers()
        self.logger.info("事件处理器注册完成")

        # 验证配置
        self.logger.info("开始验证配置...")
        self._validate_config()
        self.logger.info("配置验证完成")

        self.logger.info("数据中心初始化完成")

    def _validate_config(self):
        """验证配置完整性"""
        self.logger.debug("开始验证必需配置段...")
        required_sections = {
            'data_center': ['database', 'bar_generation']
        }

        for section, keys in required_sections.items():
            if section not in self.config:
                self.logger.warning(f"配置中缺少 {section} 段，将使用默认值")
                continue

            section_config = self.config[section]
            for key in keys:
                if key not in section_config:
                    self.logger.warning(f"配置 {section}.{key} 缺失，将使用默认值")

        self.logger.debug("开始验证数据库配置...")
        # 验证数据库配置
        db_config = self.database_config
        sqlite_config = db_config.get('sqlite') if db_config else None
        if not sqlite_config:
            self.logger.error("数据库配置缺失，请检查配置文件")
        elif 'tick_db' in sqlite_config:
            # 新的分库配置验证
            tick_db_config = sqlite_config.get('tick_db', {})
            bar_db_config = sqlite_config.get('bar_db', {})

            if not tick_db_config.get('path'):
                self.logger.warning("Tick数据库路径未配置，使用默认路径: data/tick_data.db")
            if not bar_db_config.get('path'):
                self.logger.warning("Bar数据库路径未配置，使用默认路径: data/bar_data.db")

            self.logger.info(f"使用分库配置: Tick={tick_db_config.get('path')}, Bar={bar_db_config.get('path')}")
        elif not 'bar_db' in sqlite_config:
            self.logger.error("bar_data数据库配置缺失，请检查配置文件")

        self.logger.debug("开始验证K线配置...")
        # 验证K线配置
        bar_config = self.bar_config
        if not bar_config or not bar_config.get('intervals'):
            self.logger.warning("K线间隔未配置，使用默认间隔: [1m, 5m, 15m, 30m, 1h]")
        self.logger.debug("配置验证完成")

    def _convert_intervals_to_minutes(self, interval_strings: List[str]) -> List[int]:
        """将时间间隔字符串转换为分钟数"""
        conversion_map = {
            'm': 1, 'h': 60, 'd': 1440
        }
        intervals = []
        for interval_str in interval_strings:
            if interval_str and interval_str[-1] in conversion_map:
                try:
                    number = int(interval_str[:-1])
                    unit = interval_str[-1]
                    intervals.append(number * conversion_map[unit])
                except ValueError:
                    self.logger.warning(f"无法解析时间间隔: {interval_str}")
            else:
                self.logger.warning(f"不支持的时间间隔格式: {interval_str}")

        if not intervals:
            self.logger.warning("未找到有效的时间间隔配置，使用默认值")
            intervals = [1, 5, 15, 30, 60]  # 默认分钟间隔

        self.logger.info(f"K线时间间隔配置: {intervals} 分钟")
        return intervals

    def _load_market_symbols(self) -> List[str]:
        """从instrument_exchange_id.json加载全市场合约列表"""
        try:
            # 直接从instrument_exchange_id.json获取所有合约
            instrument_exchange_json = get_instrument_exchange_id()
            
            # 如果文件不存在或为空，尝试从全局缓存获取
            if not instrument_exchange_json:
                self.logger.warning("instrument_exchange_id.json文件不存在或为空，尝试从全局缓存获取合约列表")
                from src.ctp.gateway.order_trading_gateway import symbol_contract_map
                if symbol_contract_map:
                    symbols = list(symbol_contract_map.keys())
                    self.logger.info(f"从全局缓存加载了 {len(symbols)} 个期货合约")
                    return symbols
                else:
                    self.logger.warning("全局缓存也为空，返回空合约列表")
                    return []
            
            symbols = list(instrument_exchange_json.keys())
            self.logger.info(f"从instrument_exchange_id.json加载了 {len(symbols)} 个期货合约")
            return symbols

        except Exception as e:
            self.logger.error(f"加载合约列表失败: {e}")
            # 如果加载失败，尝试从全局缓存获取
            try:
                from src.ctp.gateway.order_trading_gateway import symbol_contract_map
                if symbol_contract_map:
                    symbols = list(symbol_contract_map.keys())
                    self.logger.info(f"从全局缓存加载了 {len(symbols)} 个期货合约")
                    return symbols
            except Exception as cache_e:
                self.logger.error(f"从全局缓存获取合约列表也失败: {cache_e}")
            
            # 最后返回空列表而不是包含空字符串的列表
            return []

    def _register_event_handlers(self):
        """注册事件处理器"""
        # 数据中心查询事件
        self.event_bus.subscribe(EventType.DATA_CENTER_QUERY_TICK, self._handle_query_tick)
        self.event_bus.subscribe(EventType.DATA_CENTER_QUERY_BAR, self._handle_query_bar)

        # 网关事件
        self.event_bus.subscribe(EventType.GATEWAY_CONNECTED, self._handle_gateway_connected)
        self.event_bus.subscribe(EventType.GATEWAY_READY, self._handle_gateway_ready)
        self.event_bus.subscribe(EventType.GATEWAY_CONTRACTS_READY, self._handle_gateway_contracts_ready)
        self.event_bus.subscribe(EventType.GATEWAY_DISCONNECTED, self._handle_gateway_disconnected)
        self.event_bus.subscribe(EventType.CONTRACT_INFO, self._handle_contract_info)

        # 监听原始tick数据事件（从CTP网关发布的事件）
        self.event_bus.subscribe(EventType.MARKET_TICK_RAW, self._handle_tick_data)

        self.logger.info("数据中心事件处理器注册完成")

    def start(self):
        """启动数据中心"""
        try:
            if self.is_running:
                self.logger.warning("数据中心已在运行")
                return

            self.logger.info("启动数据中心...")

            # 启动数据库
            self.database.start()

            # 初始化网关
            self._init_gateway()

            # 启动监控线程
            self._start_monitor_threads()

            # 设置运行状态
            self.is_running = True
            self.stats['start_time'] = datetime.now()
            self.stats['database_status'] = 'connected'

            # 发布数据中心连接事件
            self.event_bus.publish(Event(EventType.DATA_CENTER_CONNECTED, {}))

            self.logger.info("数据中心启动成功")

        except Exception as e:
            self.logger.error(f"启动数据中心失败: {e}", exc_info=True)
            self.stop()
            raise

    def stop(self):
        """停止数据中心"""
        try:
            if not self.is_running:
                self.logger.info("数据中心未在运行")
                return

            self.logger.info("停止数据中心...")

            # 设置停止标志
            self.is_running = False

            # 停止网关
            if self.market_gateway:
                self.market_gateway.close()
                self.market_gateway = None

            if self.trading_gateway:
                self.trading_gateway.close()
                self.trading_gateway = None

            # 停止数据库
            self.database.stop()

            # 停止监控线程
            self._stop_monitor_threads()

            # 发布数据中心断开事件
            self.event_bus.publish(Event(EventType.DATA_CENTER_DISCONNECTED, {}))

            self.logger.info("数据中心已停止")

        except Exception as e:
            self.logger.error(f"停止数据中心失败: {e}", exc_info=True)

    def _init_gateway(self):
        """初始化网关"""
        try:
            # 从配置获取网关设置
            gateway_config = self.config.get('gateway', {})

            # 创建交易网关实例
            self.trading_gateway = OrderTradingGateway(
                event_bus=self.event_bus,
                gateway_name="DATA_CENTER_TD"
            )

            # 连接交易网关
            self.trading_gateway.connect(gateway_config)

            # 创建行情网关实例
            self.market_gateway = MarketDataGateway(
                event_bus=self.event_bus,
                gateway_name="DATA_CENTER_MD"
            )

            # 连接行情网关
            self.market_gateway.connect(gateway_config)

            self.logger.info("网关初始化成功")

        except Exception as e:
            self.logger.error(f"网关初始化失败: {e}")
            raise

    def _start_monitor_threads(self):
        """启动监控线程"""
        try:
            # 启动性能监控线程
            self.monitor_thread = threading.Thread(
                target=self._performance_monitor,
                daemon=True
            )
            self.monitor_thread.start()

            self.logger.info("监控线程启动成功")

        except Exception as e:
            self.logger.error(f"启动监控线程失败: {e}")
            raise

    def _stop_monitor_threads(self):
        """停止监控线程"""
        try:
            # 等待监控线程结束
            if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)

            self.logger.info("监控线程已停止")

        except Exception as e:
            self.logger.error(f"停止监控线程失败: {e}")

    def _performance_monitor(self):
        """性能监控线程"""
        self.logger.info("性能监控线程已启动")

        while self.is_running:
            try:
                time.sleep(300)  # 每5分钟输出一次统计信息（减少日志频率）

                # 计算运行时间
                if self.stats['start_time']:
                    uptime = datetime.now() - self.stats['start_time']
                    uptime_str = str(uptime).split('.')[0]  # 去掉微秒
                else:
                    uptime_str = "未知"

                # 输出统计信息
                self.logger.info(
                    f"数据中心运行状态 - "
                    f"运行时间: {uptime_str}, "
                    f"Tick数量: {self.stats['tick_count']}, "
                    f"K线数量: {self.stats['bar_count']}, "
                    f"订阅合约: {self.stats['subscribed_count']}, "
                    f"数据库状态: {self.stats['database_status']}"
                )

            except Exception as e:
                self.logger.error(f"性能监控异常: {e}")
                time.sleep(5)

        self.logger.info("性能监控线程已停止")

    def _handle_tick_data(self, event: Event):
        """处理tick数据"""
        try:
            from datetime import datetime
            tick_data = event.data

            # 如果是TickData对象，直接使用
            if isinstance(tick_data, TickData):
                processed_tick = tick_data
            # 如果是字典，转换为TickData对象
            elif isinstance(tick_data, dict):
                from src.core.object import TickData as TickDataClass
                from src.config.constant import Exchange

                # 转换字典为TickData对象
                processed_tick = TickDataClass(
                    symbol=tick_data.get('symbol', ''),
                    exchange=Exchange(tick_data.get('exchange', 'CZCE')),
                    datetime=datetime.fromisoformat(tick_data.get('datetime', datetime.now().isoformat())),
                    last_price=tick_data.get('last_price', 0.0),
                    volume=tick_data.get('volume', 0),
                    turnover=tick_data.get('turnover', 0.0),
                    open_interest=tick_data.get('open_interest', 0),
                    bid_price_1=tick_data.get('bid_price_1', 0.0),
                    ask_price_1=tick_data.get('ask_price_1', 0.0),
                    bid_volume_1=tick_data.get('bid_volume_1', 0),
                    ask_volume_1=tick_data.get('ask_volume_1', 0),
                    gateway_name="DATA_CENTER_MD"
                )
            else:
                self.logger.warning(f"收到未知类型的tick数据: {type(tick_data)}")
                return

            # 更新统计信息
            self.stats['tick_count'] += 1
            self.stats['last_tick_time'] = datetime.now()

            # 保存到数据库
            self.database.save_tick_data(processed_tick)

            # K线合成
            self._process_bar_generation(processed_tick)

            # 定期输出统计信息（降低频率以减少日志输出）
            if self.stats["tick_count"] % 1000 == 0:
                self.logger.info(f"数据中心统计: 已处理{self.stats['tick_count']}个tick")

        except Exception as e:
            self.logger.error(f"处理tick数据失败: {e}", exc_info=True)

    def _process_bar_generation(self, tick_data: TickData):
        """处理K线合成"""
        try:
            # 使用K线合成器生成K线
            self.bar_generator.on_tick(tick_data)

        except Exception as e:
            self.logger.error(f"K线合成处理失败: {e}", exc_info=True)

    def _on_bar_generated(self, bar: BarData):
        """K线生成回调"""
        try:
            # 更新统计信息
            self.stats['bar_count'] += 1

            # 保存到数据库
            self.database.save_bar_data(bar)

            self.logger.debug(f"生成K线: {bar.symbol} {bar.datetime}")

        except Exception as e:
            self.logger.error(f"处理K线数据失败: {e}", exc_info=True)

    def _handle_gateway_connected(self, event: Event):
        """处理网关连接事件"""
        try:
            self.is_connected = True
            self.stats['gateway_status'] = 'connected'
            connected_data = event.data
            self.logger.info(f"网关连接事件: {connected_data}")

            self.logger.info("网关已连接，等待登录完成...")

        except Exception as e:
            self.logger.error(f"处理网关连接事件失败: {e}")

    def _handle_gateway_ready(self, event: Event):
        """处理网关就绪事件（登录完成后）"""
        try:
            self.stats['gateway_status'] = 'ready'
            ready_data = event.data
            self.logger.info(f"网关就绪事件: {ready_data}")
            self.logger.info("网关已就绪（登录完成），等待合约信息处理完成")

        except Exception as e:
            self.logger.error(f"处理网关就绪事件失败: {e}")

    def _handle_gateway_contracts_ready(self, event: Event):
        """处理网关合约就绪事件（合约信息处理完成后）"""
        try:
            self.stats['gateway_status'] = 'contracts_ready'
            contracts_data = event.data
            self.logger.info(f"网关合约就绪事件: {contracts_data}")
            
            # 合约信息处理完成后才开始订阅全市场行情
            self._subscribe_market_data()
            
            self.logger.info("网关合约信息已就绪，开始订阅全市场行情")

        except Exception as e:
            self.logger.error(f"处理网关合约就绪事件失败: {e}")

    def _handle_gateway_disconnected(self, event: Event):
        """处理网关断开事件"""
        try:
            self.is_connected = False
            self.stats['gateway_status'] = 'disconnected'
            disconnected_data = event.data
            self.logger.info(f"网关断开事件: {disconnected_data}")

            self.logger.warning("网关已断开连接")

        except Exception as e:
            self.logger.error(f"处理网关断开事件失败: {e}")

    def _handle_contract_info(self, event: Event):
        """处理合约信息事件"""
        try:
            contract = event.data
            symbol = contract.symbol

            # 添加到合约列表
            self.all_contracts[symbol] = contract

            self.logger.info(f"新增合约: {symbol}")

        except Exception as e:
            self.logger.error(f"处理合约信息失败: {e}")

    def _subscribe_market_data(self):
        """订阅全市场行情数据"""
        try:
            if not self.market_gateway:
                self.logger.warning("网关未初始化，无法订阅行情")
                return

            # 预加载合约数据到全局缓存
            self._preload_contracts()

            # 如果market_symbols为空，尝试重新加载或从全局缓存获取
            if not self.market_symbols or (len(self.market_symbols) == 1 and self.market_symbols[0] == ""):
                self.logger.warning("market_symbols为空，尝试重新加载合约列表")
                self.market_symbols = self._load_market_symbols()
                
                # 如果仍然为空，尝试从全局缓存获取
                if not self.market_symbols:
                    try:
                        from src.ctp.gateway.order_trading_gateway import symbol_contract_map
                        if symbol_contract_map:
                            self.market_symbols = list(symbol_contract_map.keys())
                            self.logger.info(f"从全局缓存获取了 {len(self.market_symbols)} 个合约")
                        else:
                            self.logger.error("无法获取任何合约列表，取消订阅")
                            return
                    except Exception as e:
                        self.logger.error(f"从全局缓存获取合约失败: {e}")
                        return

            # 获取订阅配置
            subscribe_config = self.data_center_config.get('market_subscription', {})
            max_subscriptions = subscribe_config.get('max_subscriptions', 100)  # 默认最多订阅100个合约
            subscribe_all = subscribe_config.get('auto_subscribe_all', False)  # 是否订阅所有合约

            # 确定要订阅的合约列表
            symbols_to_subscribe = []

            # 2. 如果启用订阅所有合约，或者优先合约数量不足，添加其他合约
            if subscribe_all:
                # 订阅所有合约，忽略数量限制
                for symbol in self.market_symbols:
                    if symbol and symbol.strip() and symbol not in symbols_to_subscribe:  # 过滤空字符串
                        symbols_to_subscribe.append(symbol)
            elif len(symbols_to_subscribe) < max_subscriptions:
                # 在数量限制内添加其他合约
                for symbol in self.market_symbols:
                    if symbol and symbol.strip() and symbol not in symbols_to_subscribe:  # 过滤空字符串
                        symbols_to_subscribe.append(symbol)
                        if len(symbols_to_subscribe) >= max_subscriptions:
                            break

            # 3. 添加通过CONTRACT_INFO事件获取的合约
            if subscribe_all:
                # 订阅所有合约，忽略数量限制
                for symbol in self.all_contracts:
                    if symbol not in symbols_to_subscribe:
                        symbols_to_subscribe.append(symbol)
            else:
                # 在数量限制内添加合约
                for symbol in self.all_contracts:
                    if symbol not in symbols_to_subscribe and len(symbols_to_subscribe) < max_subscriptions:
                        symbols_to_subscribe.append(symbol)

            self.logger.info(
                f"准备订阅 {len(symbols_to_subscribe)} 个合约 (最大限制: {'无限制' if subscribe_all else max_subscriptions})")

            # 订阅合约的tick数据
            subscribed_count = 0
            failed_count = 0

            for symbol in symbols_to_subscribe:
                try:
                    # 创建订阅请求对象
                    from src.core.object import SubscribeRequest
                    from src.config.constant import Exchange

                    # 根据合约代码推断交易所
                    exchange = self._get_symbol_exchange(symbol)

                    subscribe_req = SubscribeRequest(
                        symbol=symbol,
                        exchange=exchange
                    )

                    self.market_gateway.subscribe(subscribe_req)
                    self.subscribed_symbols.add(symbol)
                    subscribed_count += 1

                    # 每订阅50个合约输出一次进度
                    if subscribed_count % 50 == 0:
                        self.logger.info(f"已订阅 {subscribed_count} 个合约...")

                except Exception as e:
                    self.logger.error(f"订阅合约 {symbol} 失败: {e}")
                    failed_count += 1

            self.stats['subscribed_count'] = len(self.subscribed_symbols)
            self.logger.info(
                f"合约订阅完成 - "
                f"成功: {subscribed_count}, "
                f"失败: {failed_count}, "
                f"总计: {len(self.subscribed_symbols)} 个合约"
            )

        except Exception as e:
            self.logger.error(f"订阅全市场行情失败: {e}")

    @staticmethod
    def _get_symbol_exchange(symbol: str):
        """根据合约代码推断交易所"""
        return Exchange(get_exchange(symbol))

    def _preload_contracts(self):
        """预加载合约数据到全局缓存"""
        try:
            # 导入全局合约映射
            from src.ctp.gateway.market_data_gateway import symbol_contract_map
            from src.core.object import ContractData
            from src.config.constant import Product

            self.logger.info("开始预加载合约数据...")

            # 直接从instrument_exchange_id.json获取所有合约和交易所映射
            instrument_exchange_json = get_instrument_exchange_id()

            # 统计信息
            loaded_count = 0
            skipped_count = 0
            error_count = 0

            # 遍历所有合约进行预加载
            for symbol, exchange_str in instrument_exchange_json.items():
                try:
                    # 如果合约已存在于缓存中，跳过
                    if symbol in symbol_contract_map:
                        skipped_count += 1
                        continue

                    # 获取交易所枚举
                    exchange = EXCHANGE_MAPPING.get(exchange_str)
                    if not exchange:
                        self.logger.warning(f"未知交易所: {exchange_str} (合约: {symbol})")
                        error_count += 1
                        continue

                    # 创建合约数据
                    contract = ContractData(
                        symbol=symbol,
                        exchange=exchange,
                        name=f"{symbol}合约",
                        product=Product.FUTURES,
                        size=1,
                        price_tick=0.01,
                        min_volume=1,
                        gateway_name=self.market_gateway.gateway_name if self.market_gateway else "DATA_CENTER_MD"
                    )

                    # 添加到全局缓存
                    symbol_contract_map[symbol] = contract
                    loaded_count += 1

                    # 每加载100个合约输出一次进度
                    if loaded_count % 100 == 0:
                        self.logger.info(f"已预加载 {loaded_count} 个合约...")

                except Exception as e:
                    self.logger.error(f"预加载合约 {symbol} 失败: {e}")
                    error_count += 1

            self.logger.info(
                f"合约预加载完成 - "
                f"新加载: {loaded_count}, "
                f"跳过: {skipped_count}, "
                f"错误: {error_count}, "
                f"全局缓存总数: {len(symbol_contract_map)}"
            )

        except Exception as e:
            self.logger.error(f"预加载合约数据失败: {e}")
            self.logger.error(f"错误详情: {traceback.format_exc()}")

    def _handle_query_tick(self, event: Event):
        """处理tick数据查询请求"""
        try:
            query_data = event.data
            symbol = query_data.get('symbol')
            exchange = get_exchange(symbol)
            start_time = query_data.get('start_time')
            end_time = query_data.get('end_time')
            limit = query_data.get('limit', 1000)

            # 查询数据
            tick_data = self.database.query_tick_data(
                symbol=symbol,
                exchange=exchange,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )

            # 发布查询结果
            result_event = Event(
                event_type=EventType.DATA_CENTER_TICK_RESULT,
                data={
                    'request_id': query_data.get('request_id'),
                    'tick_data': tick_data
                }
            )
            self.event_bus.publish(result_event)

        except Exception as e:
            self.logger.error(f"处理tick查询请求失败: {e}")

    def _handle_query_bar(self, event: Event):
        """处理bar数据查询请求"""
        try:
            query_data = event.data
            symbol = query_data.get('symbol')
            exchange = get_exchange(symbol)
            interval = query_data.get('interval')
            start_time = query_data.get('start_time')
            end_time = query_data.get('end_time')
            limit = query_data.get('limit', 1000)

            # 查询数据
            bar_data = self.database.query_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )

            # 发布查询结果
            result_event = Event(
                event_type=EventType.DATA_CENTER_BAR_RESULT,
                data={
                    'request_id': query_data.get('request_id'),
                    'bar_data': bar_data
                }
            )
            self.event_bus.publish(result_event)

        except Exception as e:
            self.logger.error(f"处理bar查询请求失败: {e}")

    def get_status(self) -> dict:
        """获取数据中心状态"""
        try:
            status = {
                'is_running': self.is_running,
                'is_connected': self.is_connected,
                'stats': self.stats.copy(),
                'subscribed_symbols': list(self.subscribed_symbols),
                'total_contracts': len(self.all_contracts),
                'database_status': self.database.get_status() if self.database else 'disconnected'
            }

            return status

        except Exception as e:
            self.logger.error(f"获取状态失败: {e}")
            return {'error': str(e)}

    def query_tick_data(self, symbol: str, start_time: datetime = None,
                        end_time: datetime = None, limit: int = 1000) -> List[dict]:
        """查询tick数据"""
        try:
            return self.database.query_tick_data(
                symbol=symbol,
                exchange=get_exchange(symbol),
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
        except Exception as e:
            self.logger.error(f"查询tick数据失败: {e}")
            return []

    def query_bar_data(self, symbol: str, exchange: str = 'SHFE', interval: str = '1m',
                       start_time: datetime = None, end_time: datetime = None, limit: int = 1000) -> List[dict]:
        """查询bar数据"""
        try:
            return self.database.query_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
        except Exception as e:
            self.logger.error(f"查询bar数据失败: {e}")
            return []
