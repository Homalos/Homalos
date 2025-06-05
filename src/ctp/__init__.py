from importlib import metadata

from .gateway import CtpGateway

__all__ = ["CtpGateway"]

try:
    __version__ = metadata.version("ctp")
except metadata.PackageNotFoundError:
    __version__ = "dev"
