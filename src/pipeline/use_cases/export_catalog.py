"""Use case: Direct catalog export from database to final 138-column Excel spreadsheet."""

import logging
import time
from typing import Optional, List

from src.domain.models import PipelineResult
from src.domain.ports.events import EventSinkPort, NullEventSink
from src.domain.ports.gateways import ExcelIOPort
from src.domain.ports.repositories import ProductRepositoryPort
from src.domain.products.feed_specs import apply_feed_specs
from src.domain.transform.output_transformer import OutputTransformer

logger = logging.getLogger(__name__)


class DefaultExcelIO:
    """Default adapter for Excel reading and writing."""

    def load_xlsx(self, file_path: str):
        from src.data.excel import load_xlsx

        return load_xlsx(file_path)

    def write_xlsx(self, df, file_path: str) -> None:
        from src.data.excel import write_xlsx

        write_xlsx(df, file_path)


class ExportCatalogUseCase:
    """Exports current database catalog directly into the final e-shop Excel format."""

    def __init__(
        self,
        product_repo: ProductRepositoryPort,
        transformer: OutputTransformer,
        excel_io: Optional[ExcelIOPort] = None,
    ):
        self.repo = product_repo
        self.transformer = transformer
        self.excel_io = excel_io or DefaultExcelIO()

    def execute(
        self,
        output_path: str,
        selected_categories: Optional[List[str]] = None,
        event_sink: Optional[EventSinkPort] = None,
    ) -> PipelineResult:
        """Execute database to Excel catalog export."""
        start_time = time.time()
        result = PipelineResult()
        events = event_sink or NullEventSink()

        events.emit_progress("Načítavam produkty z databázy...")
        df = self.repo.get_all()
        if df.empty:
            events.emit_progress("Databáza je prázdna.")
            raise RuntimeError("V databáze sa nenachádzajú žiadne produkty na export.")

        if selected_categories and "defaultCategory" in df.columns:
            orig_count = len(df)
            df = df[df["defaultCategory"].isin(selected_categories)].copy()
            events.emit_progress(f"Filtrovaných {len(df)} z {orig_count} produktov podľa vybraných kategórií...")
            if df.empty:
                raise RuntimeError("Žiadne produkty v databáze nezodpovedajú vybraným kategóriám.")

        # Ensure structured feed dimensions/weight overrides are applied
        df = apply_feed_specs(df)

        events.emit_progress(f"Transformujem {len(df)} produktov do výstupného formátu...")
        output_df = self.transformer.transform(df)

        events.emit_progress(f"Zapisujem do Excel súboru: {output_path}...")
        self.excel_io.write_xlsx(output_df, output_path)

        result.output_path = output_path
        result.product_count = len(output_df)
        result.duration_seconds = time.time() - start_time
        events.emit_progress(f"Export dokončený: {result.product_count} produktov za {result.duration_seconds:.1f}s")
        return result
