"""EventSink ports and adapters (Observer pattern) for pipeline execution updates."""

import logging
from typing import Callable, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class EventSinkPort(Protocol):
    """Port for receiving pipeline progress and stage transition events."""

    def emit_progress(self, message: str) -> None:
        """Report general progress message."""
        ...

    def emit_stage(self, stage_key: str) -> None:
        """Report transition to a new pipeline stage."""
        ...

    def emit_ai_progress(self, current: int, total: int, message: str) -> None:
        """Report fine-grained AI batch processing progress."""
        ...


class NullEventSink:
    """Default no-op event sink."""

    def emit_progress(self, message: str) -> None:
        pass

    def emit_stage(self, stage_key: str) -> None:
        pass

    def emit_ai_progress(self, current: int, total: int, message: str) -> None:
        pass


class CallbackEventSink:
    """Adapts individual callbacks to the EventSinkPort."""

    def __init__(
        self,
        on_progress: Optional[Callable[[str], None]] = None,
        on_stage: Optional[Callable[[str], None]] = None,
        on_ai_progress: Optional[Callable[[int, int, str], None]] = None,
    ):
        self._on_progress = on_progress
        self._on_stage = on_stage
        self._on_ai_progress = on_ai_progress

    def emit_progress(self, message: str) -> None:
        if self._on_progress:
            self._on_progress(message)
        logger.info(message)

    def emit_stage(self, stage_key: str) -> None:
        if self._on_stage:
            self._on_stage(stage_key)

    def emit_ai_progress(self, current: int, total: int, message: str) -> None:
        if self._on_ai_progress:
            self._on_ai_progress(current, total, message)
        elif self._on_progress:
            self._on_progress(message)


class ConsoleEventSink:
    """Event sink for CLI output using logger."""

    def emit_progress(self, message: str) -> None:
        logger.info(message)

    def emit_stage(self, stage_key: str) -> None:
        logger.info("[STAGE: %s]", stage_key.upper())

    def emit_ai_progress(self, current: int, total: int, message: str) -> None:
        logger.info("AI [%d/%d]: %s", current, total, message)
