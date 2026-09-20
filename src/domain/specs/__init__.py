"""Specification validation, auditing, and patching domain package."""

from .auditor import CatalogAuditor
from .patcher import SpecPatcher

__all__ = ["CatalogAuditor", "SpecPatcher"]
