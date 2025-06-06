import zmq
import zmq.asyncio
import pickle
import asyncio
from collections import defaultdict
from typing import Callable, Any, Coroutine, TypeVar, Optional, Union

from src.core.event import Event, EventType, LogEvent, TickEvent, OrderUpdateEvent, TradeUpdateEvent, AccountUpdateEvent, PositionUpdateEvent, ContractInfoEvent, SubscribeRequestEvent, OrderRequestEvent, CancelOrderRequestEvent, StrategySignalEvent, GatewayStatusEvent
from src.core.object import LogData # Assuming LogData might be used if LogEvents are passed
from src.util.logger import log, setup_logging

# 如果需要处理程序类型提示，请为特定事件类型定义 TypeVar
SpecificEvent = TypeVar('SpecificEvent', bound=Event)

class ZmqEventEngine:
    """
    一个使用 ZeroMQ 进行进程间通信的事件引擎。
    它采用发布-订阅模式。事件由一个或多个组件发布，并由其他组件订阅。
    """
    def __init__(self, pub_addr: str = "tcp://*:5555", sub_addr: str = "tcp://localhost:5555", 
                 engine_id: str = "ZmqEngine", environment_name: Optional[str] = None):
        """
        初始化 ZeroMQ 事件引擎。

        Args:
            pub_addr: PUB 套接字绑定到的地址（例如"tcp://*:5555"）。
                      组件将向该地址发布事件。
            sub_addr: SUB 套接字要连接的地址（例如"tcp://localhost:5555"）。
                      该引擎实例将订阅该地址来接收事件。
            engine_id: 此引擎实例的唯一标识符，用于记录日志。
            environment_name: 环境名称，用于区分不同环境的端口。
        """
        self.engine_id = engine_id
        self.environment_name = environment_name
        
        # 根据环境名称调整端口
        if environment_name:
            # 为不同环境使用不同的端口对
            # 基础端口: simnow=5555/5556, simnow7x24=5557/5558, tts=5559/5560, 等等
            port_mapping = {
                "simnow": (5555, 5556),
                "simnow7x24": (5557, 5558),
                "tts": (5559, 5560),
                "tts7x24": (5561, 5562),
                "real": (5563, 5564)
            }
            
            # 获取环境对应的端口对，如果未找到则使用默认端口
            main_port, md_port = port_mapping.get(environment_name.lower(), (5555, 5556))
            
            # 根据引擎ID判断是主引擎还是行情网关
            if "MainEngine" in engine_id:
                # 主引擎: PUB=main_port, SUB=md_port
                pub_addr = f"tcp://*:{main_port}"
                sub_addr = f"tcp://localhost:{md_port}"
            elif "MarketData" in engine_id:
                # 行情网关: PUB=md_port, SUB=main_port
                pub_addr = f"tcp://*:{md_port}"
                sub_addr = f"tcp://localhost:{main_port}"
        
        setup_logging(service_name=f"{self.__class__.__name__}[{self.engine_id}]")
        
        self.context = zmq.asyncio.Context.instance() # 使用异步上下文

        # 发布者套接字：用于此引擎实例发送事件
        self.publisher = self.context.socket(zmq.PUB)
        
        # 订阅套接字：用于此引擎实例接收其本地处理程序的事件
        self.subscriber = self.context.socket(zmq.SUB)
        
        self.pub_addr = pub_addr
        self.sub_addr = sub_addr

        self._handlers: defaultdict[EventType, list[Callable[[Any], Coroutine[Any, Any, None]]]] = defaultdict(list)
        self._active: bool = False
        self._sub_task: Optional[asyncio.Task] = None
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None

        # 存储此订阅者感兴趣的主题。键：主题（字节），值：处理程序数量
        self._subscribed_topics: defaultdict[bytes, int] = defaultdict(int)

        self._log(f"初始化完成，发布地址: {self.pub_addr}, 订阅地址: {self.sub_addr}")

    def _log(self, message: str, level: str = "INFO"):
        """事件引擎的内部记录器。"""
        log(f"[{self.engine_id}] {message}", level=level)

    def is_active(self) -> bool:
        """检查事件引擎当前是否处于活动状态。"""
        return self._active

    def start(self):
        """
        启动 ZeroMQ 事件引擎。
        绑定发布者套接字并连接订阅者套接字。
        启动订阅者任务以监听传入事件。
        """
        if self._active:
            self._log("引擎已启动。", "WARNING")
            return

        try:
            self.main_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._log("在调用 ZmqEventEngine.start() 的上下文中没有运行 asyncio 事件循环。", "WARNING")

        self._log(f"Starting. PUB socket on {self.pub_addr}, SUB socket to {self.sub_addr}.")
        
        try:
            self.publisher.bind(self.pub_addr)
            self._log(f"发布者绑定到 {self.pub_addr}")
            self.subscriber.connect(self.sub_addr)
            self._log(f"订阅者已连接到 {self.sub_addr}")
        except zmq.error.ZMQError as e:
            self._log(f"无法绑定/连接 ZMQ 套接字: {e}", "ERROR")
            if not self.publisher.closed:
                self.publisher.close()
            if not self.subscriber.closed:
                self.subscriber.close()
            raise

        if not self._subscribed_topics:
             self.subscriber.subscribe("")
             self._log("尚未注册任何特定事件类型，订阅所有消息。", "DEBUG")
        else:
            for topic_bytes in self._subscribed_topics:
                self.subscriber.subscribe(topic_bytes)
                self._log(f"订阅主题: {topic_bytes.decode()}", "DEBUG")

        self._active = True
        self._sub_task = asyncio.create_task(self._run_subscriber_loop())
        self._log("成功启动。")

    async def _run_subscriber_loop(self):
        """
        订阅者循环作为异步任务运行。
        """
        self._log("订阅者循环任务已启动。")
        while self._active:
            try:
                multipart_msg = await self.subscriber.recv_multipart()
                
                if len(multipart_msg) >= 2:
                    topic_bytes = multipart_msg[0]
                    self._log(f"ZMQ订阅端收到消息，主题: {topic_bytes.decode()}", "DEBUG")
                
                if len(multipart_msg) < 2:
                    self._log(f"收到格式错误的消息(parts < 2): {multipart_msg}", "WARNING")
                    continue

                _topic_bytes, pickled_event = multipart_msg[0], multipart_msg[1]
                
                try:
                    event: Event = pickle.loads(pickled_event)
                    await self._dispatch_event(event)
                except pickle.UnpicklingError:
                    self._log(f"无法解开事件数据。", "ERROR")
                except Exception as err:
                    self._log("处理接收的 ZMQ 消息数据时出错, err: {}".format(err), "ERROR")

            except asyncio.CancelledError:
                self._log("订阅者循环任务被取消。")
                break
            except zmq.error.ContextTerminated:
                self._log("ZMQ 上下文终止，订阅者循环退出。", "INFO")
                break
            except Exception as err:
                if self._active:
                    self._log("ZMQ 订阅者循环中出现意外错误, err: {}".format(err), "ERROR")
                break
        
        self._log("订阅者循环任务已完成。")

    async def _dispatch_event(self, event: Event):
        """
        将接收到的事件分派给所有已注册的对应类型的处理程序。
        """
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    asyncio.create_task(handler(event))
                except Exception as err:
                    self._log(f"处理程序创建任务时出错 {getattr(handler, '__name__', 'unknown_handler')} for event {event.type.value}.", "ERROR")

    async def put(self, event_or_type: Union[Event, EventType], data: Any = None):
        """
        将事件发布到 ZeroMQ 总线。
        """
        if not self._active:
            self._log(f"尝试在引擎未激活时放置事件。事件已被忽略。", "WARNING")
            return

        if isinstance(event_or_type, EventType):
            event_type = event_or_type
            event_class_map = {
                EventType.TICK: TickEvent,
                EventType.ORDER_UPDATE: OrderUpdateEvent,
                EventType.TRADE_UPDATE: TradeUpdateEvent,
                EventType.POSITION_UPDATE: PositionUpdateEvent,
                EventType.ACCOUNT_UPDATE: AccountUpdateEvent,
                EventType.CONTRACT_INFO: ContractInfoEvent,
                EventType.LOG: LogEvent,
                EventType.GATEWAY_STATUS: GatewayStatusEvent,
                EventType.ORDER_REQUEST: OrderRequestEvent,
                EventType.CANCEL_ORDER_REQUEST: CancelOrderRequestEvent,
                EventType.SUBSCRIBE_REQUEST: SubscribeRequestEvent,
                EventType.STRATEGY_SIGNAL: StrategySignalEvent,
            }
            event_class = event_class_map.get(event_type, Event)
            event = event_class(type=event_type, data=data) if event_class is Event else event_class(data=data)
        else:
            event = event_or_type

        if not self.main_loop:
            self._log("无法发布事件: main_loop 不可用。", "ERROR")
            return

        try:
            pickled_event = pickle.dumps(event)
            topic = event.type.value.encode('utf-8')
            await self.publisher.send_multipart([topic, pickled_event])
        except Exception as e:
            self._log(f"发布事件 {event.type.value} 时出错: {e}", "ERROR")

    def register(self, event_type: EventType, handler: Callable[[SpecificEvent], Coroutine[Any, Any, None]]):
        """
        为特定事件类型注册异步事件处理程序。
        """
        if not asyncio.iscoroutinefunction(handler):
            raise TypeError(f"Event handler {getattr(handler, '__name__', 'unknown_handler')} must be an async function (async def).")

        self._handlers[event_type].append(handler) # type: ignore
        
        topic_bytes = event_type.value.encode('utf-8')
        if self._subscribed_topics[topic_bytes] == 0 and self._active and not self.subscriber.closed:
            try:
                self.subscriber.subscribe(topic_bytes)
                self._log(f"ZMQ SUB套接字订阅了新主题: {event_type.value}")
            except zmq.error.ZMQError as e:
                self._log(f"订阅 ZMQ SUB 套接字主题时出错 {event_type.value}: {e}", "ERROR")
        self._subscribed_topics[topic_bytes] += 1
        
        self._log(f"Handler {getattr(handler, '__name__', 'unknown_handler')} registered for event type {event_type.value}")

    def unregister(self, event_type: EventType, handler: Callable[[SpecificEvent], Coroutine[Any, Any, None]]):
        """
        取消注册特定事件类型的事件处理程序。
        """
        try:
            self._handlers[event_type].remove(handler) # type: ignore
            self._log(f"Handler {getattr(handler, '__name__', 'unknown_handler')} unregistered from event type {event_type.value}")

            topic_bytes = event_type.value.encode('utf-8')
            self._subscribed_topics[topic_bytes] -= 1
            if self._subscribed_topics[topic_bytes] <= 0:
                if self._active and not self.subscriber.closed:
                    try:
                        self.subscriber.unsubscribe(topic_bytes)
                        self._log(f"ZMQ SUB套接字取消订阅主题: {event_type.value}")
                    except zmq.error.ZMQError as e:
                        self._log(f"取消订阅 ZMQ SUB 套接字主题时出错 {event_type.value}: {e}", "ERROR")
                del self._subscribed_topics[topic_bytes]
        except ValueError:
            self._log(f"Handler {getattr(handler, '__name__', 'unknown_handler')} not found in handlers for event type {event_type.value}.", "WARNING")

    async def stop(self):
        """
        停止 ZeroMQ 事件引擎。
        """
        if not self._active:
            self._log("引擎已经停止。", "WARNING")
            return

        self._log("停止 ZMQ 事件引擎...")
        self._active = False

        if self._sub_task:
            self._sub_task.cancel()
            try:
                await self._sub_task
            except asyncio.CancelledError:
                self._log("订阅者任务已成功取消。")

        if not self.publisher.closed:
            self.publisher.close(linger=500)
        if not self.subscriber.closed:
            self.subscriber.close(linger=0)

        self._log("ZMQ 事件引擎已停止。")


# Example usage
async def example_async_handler(event: Event):
    print(f"Received event {event.type.value} with data: {event.data}")

async def example_main():
    # Initialize two ZMQ event engines
    engine1 = ZmqEventEngine(pub_addr="tcp://*:5555", sub_addr="tcp://localhost:5556", engine_id="Engine1")
    engine2 = ZmqEventEngine(pub_addr="tcp://*:5556", sub_addr="tcp://localhost:5555", engine_id="Engine2")

    # Register handlers
    engine1.register(EventType.TICK, example_async_handler)
    engine2.register(EventType.TICK, example_async_handler)

    # Start engines
    engine1.start()
    engine2.start()

    # Wait for engines to start
    await asyncio.sleep(1)

    # Create and publish events
    from dataclasses import dataclass
    from typing import Any

    @dataclass
    class TickData:
        symbol: str
        exchange: Any
        name: str
        last_price: float

    @dataclass
    class OrderData:
        symbol: str
        exchange: Any
        orderid: str
        status: str

    # Create a tick event
    tick_data = TickData(symbol="BTCUSDT", exchange="BINANCE", name="Bitcoin", last_price=50000.0)
    await engine1.put(EventType.TICK, tick_data)  # Using the new overload

    # Create an order event
    order_data = OrderData(symbol="ETHUSDT", exchange="BINANCE", orderid="123456", status="FILLED")
    await engine2.put(EventType.ORDER_UPDATE, order_data)  # Using the new overload

    # Wait for events to be processed
    await asyncio.sleep(2)

    # Stop engines
    await engine1.stop()
    await engine2.stop()

if __name__ == "__main__":
    try:
        asyncio.run(example_main())
    except KeyboardInterrupt:
        print("Example interrupted by user.") 