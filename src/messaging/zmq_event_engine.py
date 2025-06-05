import zmq
import pickle
import threading
import asyncio
from collections import defaultdict
from typing import Callable, Any, Coroutine, TypeVar, Optional, Union

from src.core.event import Event, EventType, LogEvent, TickEvent, OrderUpdateEvent, TradeUpdateEvent, AccountUpdateEvent, PositionUpdateEvent, ContractInfoEvent, SubscribeRequestEvent, OrderRequestEvent, CancelOrderRequestEvent, StrategySignalEvent, GatewayStatusEvent
from src.core.object import LogData # Assuming LogData might be used if LogEvents are passed
from src.util.logger import log, setup_logging

# Define a TypeVar for specific event types if needed for handler type hinting
SpecificEvent = TypeVar('SpecificEvent', bound=Event)

class ZmqEventEngine:
    """
    An event engine that uses ZeroMQ for inter-process communication.
    It uses a PUB-SUB pattern. Events are published by one or more components
    and subscribed to by others.
    """
    def __init__(self, pub_addr: str = "tcp://*:5555", sub_addr: str = "tcp://localhost:5555", engine_id: str = "ZmqEngine"):
        """
        Initializes the ZeroMQ Event Engine.

        Args:
            pub_addr: The address for the PUB socket to bind to (e.g., "tcp://*:5555").
                      Components will publish events to this address.
            sub_addr: The address for the SUB socket to connect to (e.g., "tcp://localhost:5555").
                      This engine instance will subscribe to this address to receive events.
            engine_id: A unique identifier for this engine instance, used for logging.
        """
        self.engine_id = engine_id
        setup_logging(service_name=f"{self.__class__.__name__}[{self.engine_id}]")
        
        self.context = zmq.Context.instance() # Use a global singleton context

        # Publisher socket: for this engine instance to send out events
        self.publisher = self.context.socket(zmq.PUB)
        
        # Subscriber socket: for this engine instance to receive events for its local handlers
        self.subscriber = self.context.socket(zmq.SUB)
        
        self.pub_addr = pub_addr
        self.sub_addr = sub_addr

        self._handlers: defaultdict[EventType, list[Callable[[Any], Coroutine[Any, Any, None]]]] = defaultdict(list)
        self._active: bool = False
        self._sub_thread: Optional[threading.Thread] = None
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None

        # Store topics this subscriber is interested in. Key: topic (bytes), Value: count of handlers
        self._subscribed_topics: defaultdict[bytes, int] = defaultdict(int)

    def _log(self, message: str, level: str = "INFO", **kwargs):
        """Internal logger for the event engine."""
        log(f"[{self.__class__.__name__}][{self.engine_id}] {message}", level=level, **kwargs)

    def is_active(self) -> bool:
        """Checks if the event engine is currently active."""
        return self._active

    def start(self):
        """
        Starts the ZeroMQ event engine.
        Binds the publisher socket and connects the subscriber socket.
        Starts the subscriber thread to listen for incoming events.
        """
        if self._active:
            self._log("Engine is already active.", "WARNING")
            return

        try:
            # Attempt to get the current running loop if in an async context
            self.main_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._log("No asyncio event loop running in the context where ZmqEventEngine.start() is called. "
                      "Async handlers might not work as expected if not properly managed.", "WARNING")
            # If not in an async context, self.main_loop will be None.
            # Async handlers would need an explicit loop passed or a way to get one.

        self._log(f"Starting. PUB socket on {self.pub_addr}, SUB socket to {self.sub_addr}.")
        
        try:
            self.publisher.bind(self.pub_addr)
            self._log(f"Publisher bound to {self.pub_addr}")
            self.subscriber.connect(self.sub_addr)
            self._log(f"Subscriber connected to {self.sub_addr}")
        except zmq.error.ZMQError as e:
            self._log(f"Failed to bind/connect ZMQ sockets: {e}", "ERROR")
            # Potentially try to close any opened sockets before raising or returning
            if not self.publisher.closed:
                self.publisher.close()
            if not self.subscriber.closed:
                self.subscriber.close()
            raise # Re-raise the exception to signal failure to start

        # Subscribe to all initially registered topics
        # If _subscribed_topics is empty, this won't do anything here.
        # Topic subscriptions are managed by register/unregister.
        # For simplicity, we can subscribe to all messages initially or manage dynamically.
        # Let's start by subscribing to an empty string (all messages) if no specific topics yet.
        # A better approach is to subscribe to topics as handlers are registered.
        if not self._subscribed_topics:
             self.subscriber.subscribe("") # Subscribe to all messages if no specific handlers yet
             self._log("No specific event types registered yet, subscribing to ALL messages.", "DEBUG")
        else:
            for topic_bytes in self._subscribed_topics:
                self.subscriber.subscribe(topic_bytes)
                self._log(f"Subscribed to topic: {topic_bytes.decode()}", "DEBUG")


        self._active = True
        self._sub_thread = threading.Thread(target=self._run_subscriber_loop, name=f"{self.engine_id}-SubThread", daemon=True)
        self._sub_thread.start()
        self._log("Successfully started.")

    def _run_subscriber_loop(self):
        """
        The main loop for the subscriber thread.
        Polls the subscriber socket for incoming messages and processes them.
        """
        self._log("Subscriber thread started.")
        poller = zmq.Poller()
        poller.register(self.subscriber, zmq.POLLIN)

        while self._active:
            try:
                # Poll with a timeout to allow checking self._active periodically
                socks = dict(poller.poll(timeout=1000))  # Timeout in milliseconds
                if not self._active: break # Check again after poll

                if self.subscriber in socks and socks[self.subscriber] == zmq.POLLIN:
                    # Messages are expected to be [topic, pickled_event_data]
                    multipart_msg = self.subscriber.recv_multipart()
                    
                    if len(multipart_msg) < 2:
                        self._log(f"Received malformed message (parts < 2): {multipart_msg}", "WARNING")
                        continue

                    _topic_bytes, pickled_event = multipart_msg[0], multipart_msg[1]
                    
                    try:
                        event: Event = pickle.loads(pickled_event)
                        # Schedule the event processing on the main asyncio loop if available
                        if self.main_loop and self.main_loop.is_running():
                            asyncio.run_coroutine_threadsafe(self._dispatch_event(event), self.main_loop)
                        elif asyncio.iscoroutinefunction(self._dispatch_event):
                             # This case is tricky: if no main_loop was captured or it's not running,
                             # and _dispatch_event is async. We need a loop to run it.
                             # For now, we log a warning. Production systems need robust handling here.
                             self._log(f"Cannot dispatch async event {event.type.value}: main_loop not available or not running.", "ERROR")
                        else:
                             # If _dispatch_event were synchronous (it's not currently)
                             # self._dispatch_event(event) 
                             pass
                    except pickle.UnpicklingError:
                        self._log(f"Failed to unpickle event data.", "ERROR", exc_info=True)
                    except Exception:
                        self._log(f"Error processing received ZMQ message data.", "ERROR", exc_info=True)
            except zmq.error.ContextTerminated:
                self._log("ZMQ Context terminated, subscriber loop exiting.", "INFO")
                break
            except Exception:
                if self._active: # Only log if we are not intentionally stopping
                    self._log(f"Unexpected error in ZMQ subscriber loop.", "ERROR", exc_info=True)
                break # Exit loop on unexpected error
        
        poller.unregister(self.subscriber)
        self._log("Subscriber thread finished.")

    async def _dispatch_event(self, event: Event):
        """
        Dispatches a received event to all registered handlers for its type.
        This method is a coroutine and should be run on an asyncio event loop.
        """
        # self._log(f"Dispatching event: {event.type.value} (Data: {event.data})", "DEBUG")
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    # Create a new task for each handler to allow concurrent execution
                    asyncio.create_task(handler(event))
                except Exception:
                    self._log(f"Error creating task for handler {getattr(handler, '__name__', 'unknown_handler')} for event {event.type.value}.", "ERROR", exc_info=True)
        # else:
        #     self._log(f"No handlers registered for event type {event.type.value}.", "DEBUG")

    async def put(self, event_or_type: Union[Event, EventType], data: Any = None):
        """
        Publishes an event to the ZeroMQ bus.
        The event is pickled before sending.
        The event's type (EventType.value) is used as the ZMQ topic.

        Args:
            event_or_type: Either an Event object to publish, or an EventType to create a new event.
            data: If event_or_type is an EventType, this is the data to include in the new event.
        """
        if not self._active:
            self._log(f"Attempted to put event while engine is not active. Event ignored.", "WARNING")
            return

        # 如果传入的是EventType，则根据类型创建相应的事件对象
        if isinstance(event_or_type, EventType):
            event_type = event_or_type
            # 根据事件类型创建对应的事件对象
            if event_type == EventType.TICK:
                event = TickEvent(data=data)
            elif event_type == EventType.ORDER_UPDATE:
                event = OrderUpdateEvent(data=data)
            elif event_type == EventType.TRADE_UPDATE:
                event = TradeUpdateEvent(data=data)
            elif event_type == EventType.POSITION_UPDATE:
                event = PositionUpdateEvent(data=data)
            elif event_type == EventType.ACCOUNT_UPDATE:
                event = AccountUpdateEvent(data=data)
            elif event_type == EventType.CONTRACT_INFO:
                event = ContractInfoEvent(data=data)
            elif event_type == EventType.LOG:
                event = LogEvent(data=data)
            elif event_type == EventType.GATEWAY_STATUS:
                event = GatewayStatusEvent(data=data)
            elif event_type == EventType.ORDER_REQUEST:
                event = OrderRequestEvent(data=data)
            elif event_type == EventType.CANCEL_ORDER_REQUEST:
                event = CancelOrderRequestEvent(data=data)
            elif event_type == EventType.SUBSCRIBE_REQUEST:
                event = SubscribeRequestEvent(data=data)
            elif event_type == EventType.STRATEGY_SIGNAL:
                event = StrategySignalEvent(data=data)
            else:
                # 对于未知类型，创建一个通用Event
                event = Event(type=event_type, data=data)
        else:
            # 如果传入的已经是Event对象，直接使用
            event = event_or_type

        try:
            pickled_event = pickle.dumps(event)
            topic = event.type.value.encode('utf-8') # Use EventType name as topic
            
            self.publisher.send_multipart([topic, pickled_event])
            # self._log(f"Published event {event.type.value} on topic '{topic.decode()}'", "DEBUG")
        except pickle.PicklingError:
            self._log(f"Failed to pickle event {event.type.value} for publishing.", "ERROR", exc_info=True)
        except zmq.error.ZMQError:
            self._log(f"ZMQError publishing event {event.type.value}.", "ERROR", exc_info=True)
        except Exception:
            self._log(f"Unexpected error publishing event {event.type.value}.", "ERROR", exc_info=True)

    def register(self, event_type: EventType, handler: Callable[[SpecificEvent], Coroutine[Any, Any, None]]):
        """
        Registers an asynchronous event handler for a specific event type.
        The handler must be a coroutine function (async def).
        Also subscribes the ZMQ SUB socket to the corresponding topic if not already.
        """
        if not asyncio.iscoroutinefunction(handler):
            raise TypeError(f"Event handler {getattr(handler, '__name__', 'unknown_handler')} must be an async function (async def).")

        self._handlers[event_type].append(handler) # type: ignore
        
        topic_bytes = event_type.value.encode('utf-8')
        if self._subscribed_topics[topic_bytes] == 0 and self._active and not self.subscriber.closed:
            # If engine is active and this is the first handler for this topic, subscribe ZMQ socket
            try:
                self.subscriber.subscribe(topic_bytes)
                self._log(f"ZMQ SUB socket subscribed to new topic: {event_type.value}")
            except zmq.error.ZMQError as e:
                self._log(f"Error subscribing ZMQ SUB socket to topic {event_type.value}: {e}", "ERROR")
        self._subscribed_topics[topic_bytes] += 1
        
        self._log(f"Handler {getattr(handler, '__name__', 'unknown_handler')} registered for event type {event_type.value}")

    def unregister(self, event_type: EventType, handler: Callable[[SpecificEvent], Coroutine[Any, Any, None]]):
        """
        Unregisters an event handler for a specific event type.
        If no handlers remain for a topic, unsubscribes the ZMQ SUB socket.
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
                        self._log(f"ZMQ SUB socket unsubscribed from topic: {event_type.value}")
                    except zmq.error.ZMQError as e:
                        self._log(f"Error unsubscribing ZMQ SUB socket from topic {event_type.value}: {e}", "ERROR")
                del self._subscribed_topics[topic_bytes]
        except ValueError:
            self._log(f"Handler {getattr(handler, '__name__', 'unknown_handler')} not found in handlers for event type {event_type.value}.", "WARNING")

    async def stop(self):
        """
        Stops the ZeroMQ event engine.
        Closes the ZMQ sockets and terminates the subscriber thread.
        """
        if not self._active:
            self._log("Engine is already stopped.", "WARNING")
            return

        self._log("Stopping ZMQ Event Engine...")
        self._active = False

        # Wait for the subscriber thread to finish
        if self._sub_thread and self._sub_thread.is_alive():
            self._log("Waiting for subscriber thread to finish...")
            self._sub_thread.join(timeout=5.0)
            if self._sub_thread.is_alive():
                self._log("Subscriber thread did not finish in time.", "WARNING")

        # Close ZMQ sockets
        if not self.publisher.closed:
            self.publisher.close(linger=500)  # Allow time for pending messages to be sent
        if not self.subscriber.closed:
            self.subscriber.close(linger=0)  # No need to wait for subscriber

        self._log("ZMQ Event Engine stopped.")


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