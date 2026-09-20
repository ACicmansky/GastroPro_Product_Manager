"""Gateway ports (driven interfaces) for feeds, scrapers, AI, and files."""

from typing import Callable, Dict, Optional, Protocol, runtime_checkable
import pandas as pd
from src.domain.models import EnrichmentResult


@runtime_checkable
class FeedGatewayPort(Protocol):
    """Port for fetching and parsing external product feeds."""

    def fetch_and_parse(self, feed_name: str, url: str, config: dict) -> Optional[pd.DataFrame]:
        """Fetch remote feed and parse into normalized DataFrame."""
        ...


@runtime_checkable
class ScraperGatewayPort(Protocol):
    """Port for web scraping product data."""

    def scrape(
        self,
        scrape_mebella: bool = False,
        scrape_topchladenie: bool = False,
        topchladenie_csv_path: str = "",
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Execute enabled scrapers and return source-tagged DataFrames."""
        ...


@runtime_checkable
class AiEnricherPort(Protocol):
    """Port for AI-assisted product data enrichment."""

    def enrich(
        self,
        df: pd.DataFrame,
        force_reprocess: bool = False,
        progress_callback: Optional[Callable] = None,
        control=None,
        on_chunk_applied: Optional[Callable[[pd.DataFrame], None]] = None,
        only_categories: Optional[set] = None,
    ) -> EnrichmentResult:
        """Enrich products in DataFrame with AI content."""
        ...

    def resume(
        self,
        df: pd.DataFrame,
        progress_callback: Optional[Callable] = None,
        control=None,
        on_chunk_applied: Optional[Callable[[pd.DataFrame], None]] = None,
    ) -> EnrichmentResult:
        """Resume an interrupted AI enhancement run."""
        ...

    def get_resumable_run(self) -> Optional[dict]:
        """Return information about any active or resumable run."""
        ...


@runtime_checkable
class ExcelIOPort(Protocol):
    """Port for reading and writing Excel catalog spreadsheets."""

    def load_xlsx(self, file_path: str) -> pd.DataFrame:
        """Load an XLSX file into a DataFrame."""
        ...

    def write_xlsx(self, df: pd.DataFrame, file_path: str) -> None:
        """Write a DataFrame into an XLSX file."""
        ...
