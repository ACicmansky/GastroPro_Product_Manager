"""OEM specification adapter for Stalgast products."""

import logging
import re
from typing import Any, Dict, Optional

from .base_oem import BaseOEMAdapter

logger = logging.getLogger(__name__)

_STALGAST_CODE_RE = re.compile(r"^(?:ST|S)(\d{5,6})$", re.IGNORECASE)


class StalgastAdapter(BaseOEMAdapter):
    """Adapter for official Stalgast commercial gastro equipment."""

    @property
    def manufacturer_name(self) -> str:
        return "Stalgast"

    def can_handle(self, code: str, name: str) -> bool:
        c = code.strip().upper()
        n = name.upper()
        if _STALGAST_CODE_RE.match(c):
            return True
        if "STALGAST" in n:
            return True
        return False

    def get_specs(self, code: str, name: str) -> Optional[Dict[str, Any]]:
        c = code.strip().upper()
        m = _STALGAST_CODE_RE.match(c)
        if not m:
            return None

        article_nr = m.group(1)
        # Authoritative Stalgast source URL
        source_url = f"https://stalgast.com/produkt/{article_nr}"

        # Return standardized OEM descriptor
        return {
            "model_code": article_nr,
            "source_url": source_url,
        }
