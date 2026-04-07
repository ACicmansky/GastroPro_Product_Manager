from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class MergeStats:
    """Statistics from the product merge operation."""
    created: int = 0
    updated: int = 0
    removed: int = 0
    kept: int = 0


@dataclass
class MergeResult:
    """Result of merging product data from multiple sources."""
    products: pd.DataFrame
    stats: MergeStats


@dataclass
class EnrichmentResult:
    """Result of AI enhancement processing."""
    products: pd.DataFrame
    processed: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class PipelineOptions:
    """Typed options for pipeline execution."""
    main_file_path: str = ""
    output_path: str = ""
    selected_categories: list = field(default_factory=list)
    enable_scraping: bool = False
    enable_ai_enhancement: bool = False
    preserve_client_edits: bool = False
    force_ai_reprocess: bool = False
    scrape_mebella: bool = False
    scrape_topchladenie: bool = False
    topchladenie_csv_path: str = ""
    enable_price_mapping: bool = False


@dataclass
class PipelineResult:
    """Result of a complete pipeline run."""
    output_path: str = ""
    merge_stats: Optional[MergeStats] = None
    enrichment_stats: Optional[EnrichmentResult] = None
    product_count: int = 0
    duration_seconds: float = 0.0
