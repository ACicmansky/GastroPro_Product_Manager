"""Base interface for OEM manufacturer specification adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseOEMAdapter(ABC):
    """Abstract base adapter for harvesting canonical manufacturer specifications."""

    @property
    @abstractmethod
    def manufacturer_name(self) -> str:
        """Name of the manufacturer (e.g. 'Forcold', 'Stalgast')."""
        pass

    @abstractmethod
    def can_handle(self, code: str, name: str) -> bool:
        """Return True if this adapter can process the given product code or name."""
        pass

    @abstractmethod
    def get_specs(self, code: str, name: str) -> Optional[Dict[str, Any]]:
        """Return canonical dictionary of verified specifications, or None if unknown.

        Format of returned dict:
        {
            "insulation_mm": int | None,
            "volume_l": int | None,
            "power_w": int | None,
            "voltage_v": str | None,
            "temp_range": str | None,
            "width_mm": int | None,
            "depth_mm": int | None,
            "height_mm": int | None,
            "model_code": str | None,
            "source_url": str | None,
        }
        """
        pass
