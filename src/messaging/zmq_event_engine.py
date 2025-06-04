import zmq
import pickle
import threading
import asyncio
from collections import defaultdict
from typing import Callable, Any, Coroutine, TypeVar, Optional

from src.core.event import Event, EventType
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

    async def put(self, event: Event):
        """
        Publishes an event to the ZeroMQ bus.
        The event is pickled before sending.
        The event's type (EventType.value) is used as the ZMQ topic.

        Args:
            event: The Event object to publish.
        """
        if not self._active:
            self._log(f"Attempted to put event {event.type.value} while engine is not active. Event ignored.", "WARNING")
            return

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
                del self._subscribed_topics[topic_bytes] # Clean up if count is zero or less

        except ValueError:
            self._log(f"Attempt to unregister handler {getattr(handler, '__name__', 'unknown_handler')} failed: not found for event type {event_type.value}.", "WARNING")

    async def stop(self):
        """
        Stops the ZeroMQ event engine.
        Closes ZMQ sockets and stops the subscriber thread.
        The ZMQ context itself is typically terminated when the process exits or if managed globally.
        """
        if not self._active:
            self._log("Engine is not active or already stopping.", "WARNING")
            return
        
        self._log("Stopping...")
        self._active = False # Signal subscriber thread to stop

        # Wait for subscriber thread to finish
        if self._sub_thread and self._sub_thread.is_alive():
            self._log("Waiting for subscriber thread to terminate...")
            self._sub_thread.join(timeout=5.0) # Wait for 5 seconds
            if self._sub_thread.is_alive():
                self._log("Subscriber thread did not terminate in time.", "WARNING")
        
        # Close sockets
        # Check if sockets exist and are not already closed
        if hasattr(self, 'publisher') and self.publisher and not self.publisher.closed:
            self._log("Closing publisher socket.")
            self.publisher.close()
        if hasattr(self, 'subscriber') and self.subscriber and not self.subscriber.closed:
            self._log("Closing subscriber socket.")
            self.subscriber.close()
        
        # Note: ZMQ context termination is usually handled globally (e.g., context.term())
        # if zmq.Context.instance() was used. If a local context was created, term it here.
        # Since we used .instance(), we don't terminate it here as it's shared.
        
        self.main_loop = None # Clear the loop reference
        self._log("Successfully stopped.")

# Example Usage (for testing purposes, typically this would be part of a larger application)
async def example_async_handler(event: Event):
    log(f"[{threading.get_ident()}-{asyncio.current_task().get_name()}] Example Async Handler received event: {event.type} - {event.data}", "DEBUG")
    await asyncio.sleep(0.1) # Simulate some async work

async def example_main():
    pub_addr = "tcp://127.0.0.1:5555" # Use 127.0.0.1 for pub if sub is on same machine connecting to localhost
    # For PUB, tcp://*:5555 binds to all interfaces.
    # For SUB, tcp://localhost:5555 connects to localhost. Or tcp://<publisher_ip>:5555
    
    engine1 = ZmqEventEngine(pub_addr="tcp://*:5556", sub_addr="tcp://localhost:5555", engine_id="Engine1_Subscriber")
    engine2 = ZmqEventEngine(pub_addr="tcp://*:5555", sub_addr="tcp://localhost:5556", engine_id="Engine2_PublisherAndSubscriber")

    engine1.register(EventType.TICK, example_async_handler)
    engine1.register(EventType.LOG, example_async_handler)
    
    engine2.register(EventType.ORDER_UPDATE, example_async_handler)

    engine1.start()
    engine2.start()

    # Give engines time to start and connect
    await asyncio.sleep(1) 

    # Engine2 publishes a TICK event, Engine1 should receive it
    tick_data = TickData(symbol="AAPL", exchange=None, name="Apple Inc.", last_price=150.0) # Fill with dummy data
    tick_event = Event(type=EventType.TICK, data=tick_data)
    log("Engine2 publishing TickEvent...")
    await engine2.put(tick_event) # TickEvent is published on Engine2's PUB (5555)

    # Engine1 publishes an ORDER_UPDATE event, Engine2 should receive it
    order_data = OrderData(symbol="MSFT", exchange=None, orderid="123", status="FILLED") # Dummy
    order_event = Event(type=EventType.ORDER_UPDATE, data=order_data)
    log("Engine1 publishing OrderUpdateEvent...")
    await engine1.put(order_event) # OrderUpdateEvent is published on Engine1's PUB (5556)
    
    # Engine2 publishes a Log event, Engine1 should receive it
    log_data_obj = LogData(msg="A log message from Engine2", level="INFO", gateway_name="TestGateway")
    log_event_obj = Event(type=EventType.LOG, data=log_data_obj) # Use generic Event for now if LogEvent not defined in this scope
    log("Engine2 publishing LogEvent...")
    await engine2.put(log_event_obj)


    await asyncio.sleep(2) # Allow time for events to be processed

    log("Stopping engines...")
    await engine1.stop()
    await engine2.stop()
    log("Engines stopped.")

    # Terminate the global ZMQ context if no other part of the application needs it.
    # This is important for clean shutdown, especially in scripts.
    # zmq.Context.instance().term()
    # log("Global ZMQ context terminated.")


if __name__ == "__main__":
    # This example requires src.core.event.Event, EventType, and dummy data objects like TickData, OrderData, LogData
    # Ensure these are accessible or provide minimal stubs for testing.
    # For example:
    from dataclasses import dataclass
    if "TickData" not in globals():
        @dataclass
        class TickData:
            symbol: str
            exchange: Any
            name: str
            last_price: float
    if "OrderData" not in globals():
        @dataclass
        class OrderData:
            symbol: str
            exchange: Any
            orderid: str
            status: str
    # if "LogData" not in globals(): @dataclass class LogData: msg: str; level: str; gateway_name: str; # Defined in core.object

    # Need to define EventType members used if not fully imported
    # from enum import Enum
    # class EventType(Enum):
    #     TICK = "eTick"
    #     ORDER_UPDATE = "eOrderUpdate"
    #     LOG = "eLog"
    # class Event:
    #     def __init__(self, type, data=None): self.type = type; self.data = data

    try:
        asyncio.run(example_main())
    except KeyboardInterrupt:
        log("Example run interrupted by user.", "INFO")
    finally:
        # Ensure ZMQ context is terminated on script exit
        # This prevents hanging if sockets/context weren't cleaned up properly by stop() or errors.
        # It's a bit of a heavy hammer but useful for scripts.
        # In a larger app, context termination should be more carefully managed.
        # If multiple ZmqEventEngine instances share the context via .instance(),
        # term() should be called only once when the application is sure ZMQ is no longer needed.
        zmq_ctx = zmq.Context.instance()
        if not zmq_ctx.closed:
             log("Terminating global ZMQ context on script exit.", "INFO")
             zmq_ctx.term() 