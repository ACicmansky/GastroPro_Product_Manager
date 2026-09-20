"""OEM manufacturer specification adapters."""

from .base_oem import BaseOEMAdapter
from .forcold_adapter import ForcoldAdapter
from .stalgast_adapter import StalgastAdapter

__all__ = ["BaseOEMAdapter", "ForcoldAdapter", "StalgastAdapter"]
