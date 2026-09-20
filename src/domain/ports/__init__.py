"""Domain ports package for Hexagonal Architecture."""

from .repositories import ProductRepositoryPort, RunRepositoryPort
from .gateways import FeedGatewayPort, ScraperGatewayPort, AiEnricherPort, ExcelIOPort
from .events import EventSinkPort, NullEventSink, CallbackEventSink, ConsoleEventSink
from .resolution import UserResolutionPort, AutoSkipResolution, CallbackResolution

__all__ = [
    "ProductRepositoryPort",
    "RunRepositoryPort",
    "FeedGatewayPort",
    "ScraperGatewayPort",
    "AiEnricherPort",
    "ExcelIOPort",
    "EventSinkPort",
    "NullEventSink",
    "CallbackEventSink",
    "ConsoleEventSink",
    "UserResolutionPort",
    "AutoSkipResolution",
    "CallbackResolution",
]
