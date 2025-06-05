from importlib import metadata

from .gateway import TtsGateway

__all__ = ["TtsGateway"]

try:
    __version__ = metadata.version("tts")
except metadata.PackageNotFoundError:
    __version__ = "dev"
