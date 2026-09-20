"""UserResolutionPort and implementations for interactive pipeline decisions."""

from typing import Callable, Optional, Protocol, runtime_checkable
import pandas as pd


@runtime_checkable
class UserResolutionPort(Protocol):
    """Port for interactive user decisions during pipeline execution."""

    def resolve_category(self, original_category: str, product_name: str = "") -> str:
        """Resolve unmapped or ambiguous category to a target category."""
        ...

    def resolve_price(self, product_data: dict, prices_df: pd.DataFrame) -> Optional[str]:
        """Resolve missing product price (return None to skip)."""
        ...


class AutoSkipResolution:
    """Non-interactive resolver for headless or automated CLI execution."""

    def resolve_category(self, original_category: str, product_name: str = "") -> str:
        return original_category

    def resolve_price(self, product_data: dict, prices_df: pd.DataFrame) -> Optional[str]:
        return None


class CallbackResolution:
    """Adapts function callbacks to the UserResolutionPort."""

    def __init__(
        self,
        on_category: Optional[Callable[[str, str], str]] = None,
        on_price: Optional[Callable[[dict, pd.DataFrame], Optional[str]]] = None,
    ):
        self._on_category = on_category
        self._on_price = on_price

    def resolve_category(self, original_category: str, product_name: str = "") -> str:
        if self._on_category:
            return self._on_category(original_category, product_name)
        return original_category

    def resolve_price(self, product_data: dict, prices_df: pd.DataFrame) -> Optional[str]:
        if self._on_price:
            return self._on_price(product_data, prices_df)
        return None
