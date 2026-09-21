from typing import List, Optional

from .base_oem import BaseOEMAdapter
from .forcold_adapter import ForcoldAdapter
from .hendi_adapter import HendiAdapter
from .liebherr_adapter import LiebherrAdapter
from .robot_coupe_adapter import RobotCoupeAdapter
from .roller_grill_adapter import RollerGrillAdapter
from .stalgast_adapter import StalgastAdapter

__all__ = [
    "BaseOEMAdapter",
    "ForcoldAdapter",
    "HendiAdapter",
    "LiebherrAdapter",
    "RobotCoupeAdapter",
    "RollerGrillAdapter",
    "StalgastAdapter",
    "get_all_oem_adapters",
    "find_oem_adapter",
]


def get_all_oem_adapters() -> List[BaseOEMAdapter]:
    """Return an instantiated list of all registered OEM specification adapters."""
    return [
        ForcoldAdapter(),
        LiebherrAdapter(),
        StalgastAdapter(),
        RobotCoupeAdapter(),
        RollerGrillAdapter(),
        HendiAdapter(),
    ]


def find_oem_adapter(code: str, name: str = "") -> Optional[BaseOEMAdapter]:
    """Find the first matching OEM adapter for a product code or name."""
    for adapter in get_all_oem_adapters():
        if adapter.can_handle(code, name):
            return adapter
    return None
