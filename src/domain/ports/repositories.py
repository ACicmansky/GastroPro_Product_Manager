"""Repository ports (driven interfaces) for product and run persistence."""

from typing import List, Optional, Protocol, runtime_checkable
import pandas as pd


@runtime_checkable
class ProductRepositoryPort(Protocol):
    """Port for product catalog persistence."""

    def get_all(self) -> pd.DataFrame:
        """Retrieve all products as a DataFrame."""
        ...

    def upsert(self, df: pd.DataFrame) -> None:
        """Persist or update products from the given DataFrame."""
        ...

    def backup(self) -> Optional[str]:
        """Create a backup of the current repository state."""
        ...


@runtime_checkable
class RunRepositoryPort(Protocol):
    """Port for tracking AI enhancement runs and chunks."""

    def get_resumable_run(self) -> Optional[dict]:
        """Return the latest resumable run dictionary or None."""
        ...

    def create_run(self, force_reprocess: bool, chunks: List[List[str]]) -> int:
        """Create a new enhancement run and return its ID."""
        ...

    def update_run(
        self,
        run_id: int,
        status: Optional[str] = None,
        processed_delta: int = 0,
        detail: Optional[str] = None,
    ) -> None:
        """Update run status and progress metrics."""
        ...

    def get_chunks(self, run_id: int) -> List[dict]:
        """Retrieve all chunks belonging to a run."""
        ...

    def update_chunk(
        self,
        chunk_id: int,
        status: str,
        job_name: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Update a chunk's execution status."""
        ...
