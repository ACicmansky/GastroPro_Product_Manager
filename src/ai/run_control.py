"""Pause/cancel signaling shared between GUI/CLI callers and the batch orchestrator."""

import threading


class RunControl:
    """Thread-safe pause/cancel flags checked by BatchOrchestrator between chunks/polls."""

    def __init__(self):
        self._pause = threading.Event()
        self._cancel = threading.Event()

    def pause(self):
        self._pause.set()

    def unpause(self):
        self._pause.clear()

    def cancel(self):
        self._cancel.set()

    @property
    def is_pause_requested(self) -> bool:
        return self._pause.is_set()

    @property
    def is_cancel_requested(self) -> bool:
        return self._cancel.is_set()
