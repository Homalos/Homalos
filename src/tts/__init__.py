from importlib import metadata

from .gateway import MarketDataGateway, OrderTradingGateway

__all__ = ["MarketDataGateway", "OrderTradingGateway"]

try:
    __version__ = metadata.version("tts")
except metadata.PackageNotFoundError:
    __version__ = "dev"
